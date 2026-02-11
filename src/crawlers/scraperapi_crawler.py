import aiohttp

from src.crawlers.base import BaseCrawler
from src.types import CrawlerType


class ScraperAPICrawler(BaseCrawler):
    crawler_type = CrawlerType.SCRAPERAPI

    def __init__(self, api_key: str, render_js: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.render_js = render_js
        self.api_url = "https://api.scraperapi.com"

    async def crawl_url(self, url: str) -> str:
        params = {
            "api_key": self.api_key,
            "url": url,
            "output_format": "markdown",
            "render": "true" if self.render_js else "false",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.api_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"ScraperAPI HTTP {resp.status}: {text[:200]}")
                return await resp.text()
