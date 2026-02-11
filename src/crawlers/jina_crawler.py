import aiohttp
from src.crawlers.base import BaseCrawler
from src.types import CrawlerType


class JinaReaderCrawler(BaseCrawler):
    crawler_type = CrawlerType.JINA

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key

    async def crawl_url(self, url: str) -> str:
        reader_url = f"https://r.jina.ai/{url}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/markdown",
            "X-Return-Format": "markdown",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                reader_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Jina HTTP {resp.status}: {text[:200]}")
                return await resp.text()
