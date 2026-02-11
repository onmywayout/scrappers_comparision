import asyncio
import aiohttp
import trafilatura

from src.crawlers.base import BaseCrawler
from src.types import CrawlerType


class CustomHTMLCrawler(BaseCrawler):
    """
    Custom crawler based on analyze_589_companies.py:
    fetch raw HTML with browser-like headers, then extract Markdown via trafilatura.
    """

    crawler_type = CrawlerType.CUSTOM_HTML

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def crawl_url(self, url: str) -> str:
        content, _ = await self.crawl_url_with_html(url)
        return content

    async def crawl_url_with_html(self, url: str) -> tuple[str, str]:
        async with aiohttp.ClientSession() as session:
            html = await self._fetch_with_retry(session, url)
            extracted = trafilatura.extract(
                html,
                output_format="markdown",
                include_images=False,        # Drop image markdown
                include_comments=False,      # Exclude user comments
                include_tables=True,         # Important for pricing tables
                include_links=True,          # Keep links for context
                deduplicate=True,            # Remove duplicate content
                favor_recall=True,           # Prefer capturing more content
                no_fallback=False,           # Use fallback extraction if needed
            )
            if not extracted:
                raise Exception("CustomHTML extraction returned empty content")
            return extracted, html

    async def _fetch_with_retry(self, session: aiohttp.ClientSession, url: str) -> str:
        for attempt in range(self.max_retries):
            try:
                ssl_context = None if attempt < 2 else False
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True,
                    ssl=ssl_context,
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    if response.status in (403, 429):
                        await asyncio.sleep(3)
            except asyncio.TimeoutError:
                continue
            except aiohttp.ClientSSLError:
                continue
            except aiohttp.ClientError:
                continue
        raise Exception("CustomHTML failed to fetch")
