import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    firecrawl_api_key: str = ""
    jina_api_key: str = ""
    scrapingbee_api_key: str = ""
    scraperapi_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    ground_truth_path: Path = Path("verified_data.jsonl")
    output_dir: Path = Path("results")

    crawler_timeout: int = 60
    max_retries: int = 3
    min_delay_between_requests: float = 1.0  # Minimum delay (seconds) between requests to same domain
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Config":
        load_dotenv(env_file)
        return cls(
            firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY", ""),
            jina_api_key=os.getenv("JINA_API_KEY", ""),
            scrapingbee_api_key=os.getenv("SCRAPINGBEE_API_KEY", ""),
            scraperapi_api_key=os.getenv("SCRAPERAPI_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            ground_truth_path=Path(os.getenv("GROUND_TRUTH_PATH", "verified_data.jsonl")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "results")),
            crawler_timeout=int(os.getenv("CRAWLER_TIMEOUT", "60")),
            max_retries=int(os.getenv("CRAWLER_MAX_RETRIES", "3")),
            min_delay_between_requests=float(os.getenv("MIN_DELAY_BETWEEN_REQUESTS", "1.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self, crawlers: list, llms: list):
        """Validate that required API keys are present for selected tools."""
        errors = []
        from src.types import CrawlerType, LLMType

        for c in crawlers:
            if c == CrawlerType.FIRECRAWL and not self.firecrawl_api_key:
                errors.append("FIRECRAWL_API_KEY required for firecrawl crawler")
            if c == CrawlerType.JINA and not self.jina_api_key:
                errors.append("JINA_API_KEY required for jina crawler")
            if c == CrawlerType.SCRAPINGBEE and not self.scrapingbee_api_key:
                errors.append("SCRAPINGBEE_API_KEY required for scrapingbee crawler")
            if c == CrawlerType.SCRAPERAPI and not self.scraperapi_api_key:
                errors.append("SCRAPERAPI_API_KEY required for scraperapi crawler")

        for l in llms:
            if l == LLMType.OPENAI and not self.openai_api_key:
                errors.append("OPENAI_API_KEY required for openai LLM")
            if l == LLMType.CLAUDE and not self.anthropic_api_key:
                errors.append("ANTHROPIC_API_KEY required for claude LLM")

        if errors:
            raise ValueError("Missing API keys:\n  " + "\n  ".join(errors))
