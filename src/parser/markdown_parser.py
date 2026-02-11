import re
from src.types import CrawlResult, ParsedContent


MAX_CHARS_PER_PAGE = 25000
MAX_TOTAL_CHARS = 200000


class MarkdownParser:
    """Clean and prepare crawled content for LLM consumption."""

    def parse(self, crawl_result: CrawlResult) -> ParsedContent:
        cleaned_pages = {}
        for page_name, raw in crawl_result.page_contents.items():
            cleaned = self._clean_markdown(raw)
            if len(cleaned) > MAX_CHARS_PER_PAGE:
                cleaned = cleaned[:MAX_CHARS_PER_PAGE] + "\n\n[...truncated]"
            cleaned_pages[page_name] = cleaned

        combined = "\n\n---\n\n".join(
            f"# PAGE: {name.upper()}\n\n{text}"
            for name, text in cleaned_pages.items()
            if text.strip()
        )

        if len(combined) > MAX_TOTAL_CHARS:
            combined = combined[:MAX_TOTAL_CHARS] + "\n\n[...truncated]"

        return ParsedContent(
            domain=crawl_result.domain,
            crawler=crawl_result.crawler,
            markdown=combined,
            page_sections=cleaned_pages,
            char_count=len(combined),
        )

    def _clean_markdown(self, text: str) -> str:
        if not text:
            return ""
        # Remove excessive blank lines
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        # Drop linked images and inline images
        text = re.sub(r"\[\s*!\[[^\]]*\]\([^)]+\)\s*\]\([^)]+\)", "", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
        # Remove image markdown that's just decorative
        text = re.sub(r"!\[(?:icon|logo|arrow|decoration).*?\]\(.*?\)", "", text, flags=re.IGNORECASE)
        # Remove very long base64 data URIs
        text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}", "[base64-image]", text)
        # Remove cookie/consent banner boilerplate
        text = re.sub(
            r"(?i)(we use cookies|cookie policy|accept all|reject all|manage preferences).*?\n",
            "",
            text,
        )
        # Strip leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Collapse multiple blank lines again
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
