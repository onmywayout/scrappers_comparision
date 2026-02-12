from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Re-export feature schema from models (single source of truth)
from src.models import (
    AugmentedCompany,
    FeatureType,
    FEATURES,
    FEATURE_TYPES,
    SKIP_FIELDS,
    GT_FIELD_MAP,
    GT_INVERTED_BOOLEANS,
)


class CrawlerType(str, Enum):
    FIRECRAWL = "firecrawl"
    CRAWL4AI = "crawl4ai"
    JINA = "jina"
    SCRAPINGBEE = "scrapingbee"
    SCRAPERAPI = "scraperapi"
    CUSTOM_HTML = "custom_html"


class LLMType(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    HAIKU = "haiku"


@dataclass
class CrawlResult:
    domain: str
    crawler: CrawlerType
    raw_content: str
    page_contents: Dict[str, str]  # {"homepage": "...", "pricing": "..."}
    crawled_at: datetime
    homepage_internal_links: int = 0
    homepage_total_links: int = 0
    homepage_external_links: int = 0
    homepage_internal_links_crawled: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ParsedContent:
    domain: str
    crawler: CrawlerType
    markdown: str  # Combined cleaned content
    page_sections: Dict[str, str]  # Per-page cleaned content
    char_count: int = 0


@dataclass
class ExtractedFeatures:
    domain: str
    crawler: CrawlerType
    llm: LLMType
    extracted_at: datetime
    features: Dict[str, Any]  # {feature_name: normalized_value}
    raw_llm_response: str = ""
    error: Optional[str] = None


@dataclass
class FeatureScore:
    feature_name: str
    extracted_value: Any
    ground_truth_value: Any
    score: float  # 0.0 to 1.0
    match_type: str  # "exact", "partial", "missing", "no_ground_truth"


@dataclass
class PresenceScore:
    feature_name: str
    extracted_present: bool
    ground_truth_present: bool
    score: float  # 0.0 or 1.0
    match_type: str  # "exact", "mismatch"


@dataclass
class EvaluationResult:
    domain: str
    crawler: CrawlerType
    llm: LLMType
    overall_accuracy: float
    features_found: int
    features_correct: int
    overall_presence_accuracy: float = 0.0
    features_present_correct: int = 0
    homepage_internal_links: int = 0
    homepage_total_links: int = 0
    homepage_external_links: int = 0
    homepage_internal_links_crawled: int = 0
    feature_scores: List[FeatureScore] = field(default_factory=list)
    presence_scores: List[PresenceScore] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    timestamp: datetime
    total_domains: int
    total_combinations: int
    results: List[EvaluationResult]
    summary_by_crawler: Dict[str, float]
    summary_by_llm: Dict[str, float]
    summary_by_combo: Dict[str, float]
    summary_by_crawler_presence: Dict[str, float] = field(default_factory=dict)
    summary_by_llm_presence: Dict[str, float] = field(default_factory=dict)
    summary_by_combo_presence: Dict[str, float] = field(default_factory=dict)
