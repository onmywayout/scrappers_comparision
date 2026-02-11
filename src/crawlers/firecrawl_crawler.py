import aiohttp
from src.crawlers.base import BaseCrawler
from src.types import CrawlerType


class FirecrawlCrawler(BaseCrawler):
    crawler_type = CrawlerType.FIRECRAWL

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.api_url = "https://api.firecrawl.dev/v1/scrape"

    async def crawl_url(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "excludeTags": ["img"],
                    "removeBase64Images": True,
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Firecrawl HTTP {resp.status}: {text[:200]}")
                data = await resp.json()
                return data.get("data", {}).get("markdown", "")
