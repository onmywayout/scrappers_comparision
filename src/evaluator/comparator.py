import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.types import (
    ExtractedFeatures, EvaluationResult, FeatureScore, PresenceScore,
)
from src.models import (
    FEATURES, FEATURE_TYPES, FeatureType,
    GT_FIELD_MAP, GT_INVERTED_BOOLEANS,
)


class GroundTruthComparator:
    def __init__(self, ground_truth_path: Path):
        self.ground_truth = self._load_jsonl(ground_truth_path)
        self._index = self._build_index()

    def get_normalized_ground_truth(self, domain: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """Return normalized GT map: feature -> {present: bool, value: any}."""
        gt = self._find_ground_truth(domain)
        if not gt:
            return None
        gt_features = gt.get("features", {})
        normalized: Dict[str, Dict[str, Any]] = {}
        for feat_name in FEATURES:
            gt_feat, used_old_name = self._get_gt_feature(gt_features, feat_name)
            gt_present = gt_feat.get("present", False) if gt_feat else False
            gt_val = (
                self._normalize_gt_value(feat_name, gt_feat, used_old_name)
                if gt_present else None
            )
            normalized[feat_name] = {"present": gt_present, "value": gt_val}
        return normalized

    def evaluate(self, extraction: ExtractedFeatures) -> EvaluationResult:
        gt = self._find_ground_truth(extraction.domain)
        if not gt:
            return EvaluationResult(
                domain=extraction.domain,
                crawler=extraction.crawler,
                llm=extraction.llm,
                overall_accuracy=0.0,
                features_found=0,
                features_correct=0,
                errors=[f"No ground truth found for {extraction.domain}"],
            )

        gt_features = gt.get("features", {})
        scores: List[FeatureScore] = []
        presence_scores: List[PresenceScore] = []
        found = 0
        correct = 0
        present_correct = 0

        for feat_name in FEATURES:
            extracted_val = extraction.features.get(feat_name)
            gt_feat, used_old_name = self._get_gt_feature(gt_features, feat_name)
            gt_present = gt_feat.get("present", False) if gt_feat else False
            gt_val = (
                self._normalize_gt_value(feat_name, gt_feat, used_old_name)
                if gt_present else None
            )

            extracted_present = self._is_present_value(extracted_val)
            if extracted_present:
                found += 1

            score, match_type = self._score_feature(feat_name, extracted_val, gt_val, gt_present)
            if score >= 0.8:
                correct += 1

            scores.append(FeatureScore(
                feature_name=feat_name,
                extracted_value=extracted_val,
                ground_truth_value=gt_val,
                score=score,
                match_type=match_type,
            ))

            presence_score, presence_match = self._score_presence(extracted_present, gt_present)
            if presence_score >= 1.0:
                present_correct += 1
            presence_scores.append(PresenceScore(
                feature_name=feat_name,
                extracted_present=extracted_present,
                ground_truth_present=gt_present,
                score=presence_score,
                match_type=presence_match,
            ))

        accuracy = correct / len(FEATURES) if FEATURES else 0.0
        presence_accuracy = present_correct / len(FEATURES) if FEATURES else 0.0

        return EvaluationResult(
            domain=extraction.domain,
            crawler=extraction.crawler,
            llm=extraction.llm,
            overall_accuracy=accuracy,
            features_found=found,
            features_correct=correct,
            overall_presence_accuracy=presence_accuracy,
            features_present_correct=present_correct,
            feature_scores=scores,
            presence_scores=presence_scores,
        )

    # ── Scoring dispatch ─────────────────────────────────────────────────

    def _score_feature(
        self, feat_name: str, extracted: Any, ground_truth: Any, gt_present: bool
    ) -> tuple:
        feat_type = FEATURE_TYPES.get(feat_name, FeatureType.TEXT)

        # Both null — correct negative
        if extracted is None and not gt_present:
            return 1.0, "both_null"

        # Extracted null but GT has value — miss
        if extracted is None and gt_present:
            return 0.0, "missing"

        # Extracted something but GT is null — false positive (partial credit)
        if extracted is not None and not gt_present:
            # Empty lists count as null for scoring
            if isinstance(extracted, list) and len(extracted) == 0:
                return 1.0, "both_null"
            if isinstance(extracted, str) and extracted.lower() in ("unknown", ""):
                return 1.0, "both_null"
            return 0.3, "false_positive"

        # Both have values — compare by type
        if feat_type == FeatureType.LITERAL_BOOL:
            return self._score_literal_bool(extracted, ground_truth, feat_name)
        elif feat_type == FeatureType.LITERAL_ENUM:
            return self._score_literal_enum(extracted, ground_truth)
        elif feat_type == FeatureType.LIST:
            return self._score_list(extracted, ground_truth)
        else:
            return self._score_text(extracted, ground_truth)

    # ── Type-specific scorers ────────────────────────────────────────────

    def _score_literal_bool(self, extracted: Any, ground_truth: Any, feat_name: str) -> tuple:
        """Score Literal['true', 'false', 'unknown'] fields."""
        ext_str = str(extracted).lower().strip()
        gt_str = str(ground_truth).lower().strip()

        # Normalize "yes"/"no" from GT
        if gt_str in ("yes", "1"):
            gt_str = "true"
        elif gt_str in ("no", "0"):
            gt_str = "false"

        if ext_str == gt_str:
            return 1.0, "exact"
        # "unknown" vs true/false → partial credit
        if ext_str == "unknown" or gt_str == "unknown":
            return 0.5, "partial"
        return 0.0, "mismatch"

    def _score_literal_enum(self, extracted: Any, ground_truth: Any) -> tuple:
        """Score Literal enum fields (e.g., product_category)."""
        ext_str = str(extracted).lower().strip()
        gt_str = str(ground_truth).lower().strip()
        if ext_str == gt_str:
            return 1.0, "exact"
        # Check if GT is contained in extracted or vice versa
        if ext_str in gt_str or gt_str in ext_str:
            return 0.6, "partial"
        return 0.0, "mismatch"

    def _score_list(self, extracted: Any, ground_truth: Any) -> tuple:
        """Score list[str] fields using Jaccard similarity on normalized items."""
        ext_items = self._normalize_list(extracted)
        gt_items = self._normalize_list(ground_truth)

        if not ext_items and not gt_items:
            return 1.0, "both_null"
        if not ext_items or not gt_items:
            return 0.2, "mismatch"

        # Jaccard similarity on lowercased items
        ext_set = set(ext_items)
        gt_set = set(gt_items)
        intersection = len(ext_set & gt_set)
        union = len(ext_set | gt_set)

        if union == 0:
            return 1.0, "both_null"

        jaccard = intersection / union
        if jaccard >= 0.8:
            return 1.0, "exact"
        if jaccard >= 0.5:
            return 0.8, "close"

        # Fallback: check word-level overlap across all items
        ext_words = set()
        for item in ext_items:
            ext_words.update(re.findall(r'\w+', item))
        gt_words = set()
        for item in gt_items:
            gt_words.update(re.findall(r'\w+', item))

        if ext_words and gt_words:
            word_overlap = len(ext_words & gt_words) / max(len(ext_words), len(gt_words))
            if word_overlap > 0.5:
                return 0.6, "partial"

        return 0.2, "mismatch"

    def _score_text(self, extracted: Any, ground_truth: Any) -> tuple:
        """Score plain text fields."""
        ext_str = str(extracted).lower().strip()
        gt_str = str(ground_truth).lower().strip()
        if ext_str == gt_str:
            return 1.0, "exact"
        if ext_str in gt_str or gt_str in ext_str:
            return 0.8, "substring"
        # Word overlap
        ext_words = set(re.findall(r'\w+', ext_str))
        gt_words = set(re.findall(r'\w+', gt_str))
        if ext_words and gt_words:
            overlap = len(ext_words & gt_words) / max(len(ext_words), len(gt_words))
            if overlap > 0.5:
                return 0.6, "partial"
        return 0.2, "mismatch"

    # ── Helpers ──────────────────────────────────────────────────────────

    def _is_present_value(self, val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, list):
            return any(str(v).strip() for v in val)
        if isinstance(val, str):
            low = val.strip().lower()
            return low not in ("", "unknown", "null", "none")
        return True

    def _score_presence(self, extracted_present: bool, gt_present: bool) -> tuple:
        if extracted_present == gt_present:
            return 1.0, "exact"
        return 0.0, "mismatch"

    def _normalize_list(self, val: Any) -> list:
        """Normalize a value into a list of lowercase strings for comparison."""
        if isinstance(val, list):
            return [str(v).lower().strip() for v in val if v]
        if isinstance(val, str):
            # Ground truth may store lists as comma-separated strings
            items = [s.strip().lower() for s in val.split(",")]
            return [i for i in items if i]
        return []

    def _normalize_gt_value(self, feat_name: str, gt_feat: dict, used_old_name: bool) -> Any:
        """Extract the ground truth value in a form comparable to the new model's output."""
        if not gt_feat or not gt_feat.get("present"):
            return None
        val = gt_feat.get("value", "")
        feat_type = FEATURE_TYPES.get(feat_name, FeatureType.TEXT)

        if feat_type == FeatureType.LITERAL_BOOL:
            # Convert GT boolean to string "true"/"false"
            low = str(val).lower().strip()
            if low.startswith("yes") or low.startswith("true") or low == "1":
                gt_bool = "true"
            elif low.startswith("no") or low.startswith("false") or low == "0":
                gt_bool = "false"
            else:
                # If present=true for a boolean feature, default to "true"
                gt_bool = "true"

            # Handle inverted fields only when GT uses old names
            if used_old_name and feat_name in GT_INVERTED_BOOLEANS:
                gt_bool = "false" if gt_bool == "true" else "true"

            return gt_bool

        if feat_type == FeatureType.LITERAL_ENUM:
            return str(val).lower().strip()

        if feat_type == FeatureType.LIST:
            # GT may be a comma-separated string or already a list
            if isinstance(val, list):
                return val
            return val  # will be normalized during scoring

        # TEXT — return as-is
        return val

    def _get_gt_feature(self, gt_features: dict, new_feat_name: str) -> tuple[Optional[dict], bool]:
        """Look up feature from ground truth using old field names via GT_FIELD_MAP."""
        # Reverse lookup: find old name(s) that map to this new name
        old_names = [old for old, new in GT_FIELD_MAP.items() if new == new_feat_name]

        for old_name in old_names:
            # Try exact match
            if old_name in gt_features:
                return gt_features[old_name], True
            # Try underscore/space variants
            alt = old_name.replace("_", " ")
            if alt in gt_features:
                return gt_features[alt], True
            alt2 = old_name.replace(" ", "_")
            if alt2 in gt_features:
                return gt_features[alt2], True

        # Also try the new name directly (in case GT is already updated)
        if new_feat_name in gt_features:
            return gt_features[new_feat_name], False

        return None, False

    def _find_ground_truth(self, domain: str) -> Optional[dict]:
        norm = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        return self._index.get(norm)

    def _build_index(self) -> Dict[str, dict]:
        idx = {}
        for entry in self.ground_truth:
            url = entry.get("url", "")
            norm = url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
            idx[norm] = entry
        return idx

    def _load_jsonl(self, path: Path) -> list:
        with open(path, "r") as f:
            content = f.read()
        # Handle multi-line JSON entries
        entries_raw = re.split(r'(?=\{"company")', content)
        entries = []
        for raw in entries_raw:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return entries
