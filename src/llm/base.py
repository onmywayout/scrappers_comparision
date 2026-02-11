import json
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from src.types import ParsedContent, ExtractedFeatures, LLMType
from src.models import AugmentedCompany, FEATURES, SKIP_FIELDS


class BaseLLMExtractor(ABC):
    llm_type: LLMType

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def _call_llm(self, system_msg: str, user_msg: str) -> str:
        """Make the actual API call, return raw text response."""
        ...

    async def extract(self, parsed_content: ParsedContent) -> ExtractedFeatures:
        from datetime import datetime
        from src.llm.prompt import EXTRACTION_PROMPT

        system_msg = (
            "You are an expert data extraction AI. "
            "Extract structured company information from website content. "
            "Return ONLY valid JSON matching the AugmentedCompany schema."
        )
        user_msg = EXTRACTION_PROMPT + "\n\n" + parsed_content.markdown

        try:
            raw_response = await self._call_llm(system_msg, user_msg)
            features = self._parse_and_validate(raw_response, parsed_content.domain)
            return ExtractedFeatures(
                domain=parsed_content.domain,
                crawler=parsed_content.crawler,
                llm=self.llm_type,
                extracted_at=datetime.now(),
                features=features,
                raw_llm_response=raw_response,
            )
        except Exception as e:
            return ExtractedFeatures(
                domain=parsed_content.domain,
                crawler=parsed_content.crawler,
                llm=self.llm_type,
                extracted_at=datetime.now(),
                features={f: None for f in FEATURES},
                raw_llm_response="",
                error=str(e),
            )

    def _parse_and_validate(self, text: str, domain: str) -> Dict[str, Any]:
        """Parse LLM response, validate with Pydantic, return evaluable features only."""
        raw_dict = self._parse_json(text)

        # Ensure domain is set
        raw_dict.setdefault("domain", domain)

        # Try Pydantic validation (strict schema conformance)
        try:
            validated = AugmentedCompany.model_validate(raw_dict)
            full_dict = validated.model_dump()
        except Exception:
            # Fall back to raw dict if validation fails
            full_dict = raw_dict

        # Extract only evaluable features (skip domain + explanations)
        features = {}
        for feat_name in FEATURES:
            features[feat_name] = full_dict.get(feat_name)
        return features

    def _parse_json(self, text: str) -> dict:
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting from ```json ... ``` blocks
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        # Try finding first { ... } block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")
