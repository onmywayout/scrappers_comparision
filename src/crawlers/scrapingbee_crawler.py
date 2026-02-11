import aiohttp
import trafilatura

from src.crawlers.base import BaseCrawler
from src.types import CrawlerType


class ScrapingBeeCrawler(BaseCrawler):
    crawler_type = CrawlerType.SCRAPINGBEE

    def __init__(self, api_key: str, render_js: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.render_js = render_js
        self.api_url = "https://app.scrapingbee.com/api/v1"

    async def crawl_url(self, url: str) -> str:
        params = {
            "api_key": self.api_key,
            "url": url,
            "render_js": "true" if self.render_js else "false",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.api_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"ScrapingBee HTTP {resp.status}: {text[:200]}")
                html = await resp.text()
                extracted = trafilatura.extract(
                    html,
                    output_format="markdown",
                    include_images=False,
                    include_links=True,
                )
                if not extracted:
                    raise Exception("ScrapingBee returned empty content after extraction")
                return extracted
