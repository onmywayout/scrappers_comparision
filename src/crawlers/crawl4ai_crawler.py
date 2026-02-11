import logging
from src.crawlers.base import BaseCrawler
from src.types import CrawlerType

logger = logging.getLogger(__name__)


class Crawl4AICrawler(BaseCrawler):
    crawler_type = CrawlerType.CRAWL4AI

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._crawler = None

    async def _get_crawler(self):
        if self._crawler is None:
            from crawl4ai import AsyncWebCrawler
            self._crawler = AsyncWebCrawler(verbose=False)
            await self._crawler.awarmup()
        return self._crawler

    async def crawl_url(self, url: str) -> str:
        crawler = await self._get_crawler()
        result = await crawler.arun(url=url)
        if result.success:
            return result.markdown or result.cleaned_html or ""
        raise Exception(f"Crawl4AI failed: {result.error_message}")

    async def close(self):
        if self._crawler:
            await self._crawler.close()
            self._crawler = None
