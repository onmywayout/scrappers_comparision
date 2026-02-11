from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Iterable
from urllib.parse import urljoin, urlparse, urldefrag
from collections import defaultdict
import asyncio
import random
import re

from src.types import CrawlResult, CrawlerType


DEFAULT_MAX_PAGES = 10


class BaseCrawler(ABC):
    crawler_type: CrawlerType

    # Class-level rate limiting state (shared across all crawler instances)
    _domain_locks = defaultdict(asyncio.Lock)
    _last_request_time = defaultdict(float)

    def __init__(self, timeout: int = 60, max_retries: int = 3, min_delay: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay = min_delay  # Minimum delay between requests to same domain

    @abstractmethod
    async def crawl_url(self, url: str) -> str:
        """Crawl a single URL, return markdown/text content."""
        ...

    async def crawl_url_with_html(self, url: str) -> tuple[str, Optional[str]]:
        """Crawl a single URL, returning (content, raw_html if available)."""
        return await self.crawl_url(url), None

    async def crawl(
        self,
        domain: str,
        pages: Optional[List[str]] = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> CrawlResult:
        """Crawl a domain: homepage first, then discover and crawl internal links."""
        import time
        from datetime import datetime

        page_contents: Dict[str, str] = {}
        errors = []
        start = time.time()
        base = self._normalize_base(domain)

        # 1) Crawl homepage first
        try:
            homepage_content, homepage_html = await self._crawl_homepage(base, errors)
            if homepage_content and homepage_content.strip():
                page_contents["homepage"] = homepage_content
        except Exception:
            homepage_content = ""
            homepage_html = None

        # 2) Discover internal/external links from homepage (prefer raw HTML if available)
        discovery_source = homepage_html or homepage_content
        discovered, external_links = self._discover_links(discovery_source, base)
        # Prefer pricing/about if they appear on the homepage
        preferred = [urljoin(base + "/", "pricing"), urljoin(base + "/", "about")]
        discovered_set = {self._canonical_url(u) for u in discovered}
        ordered = []
        for url in preferred:
            if self._canonical_url(url) in discovered_set:
                ordered.append(url)
        for url in discovered:
            if url not in ordered:
                ordered.append(url)
        discovered = ordered
        if pages:
            discovered = self._filter_by_pages(discovered, pages) or discovered
        if max_pages is not None:
            discovered = discovered[: max(0, max_pages)]

        # 3) Crawl each discovered page
        for url in discovered:
            page_name = self._page_name(url, base)
            if page_name in page_contents:
                continue
            content = await self._crawl_with_retries(page_name, url, errors)
            if content and content.strip():
                page_contents[page_name] = content

        combined = "\n\n---\n\n".join(
            f"## Page: {name}\n\n{text}" for name, text in page_contents.items()
        )

        return CrawlResult(
            domain=domain,
            crawler=self.crawler_type,
            raw_content=combined,
            page_contents=page_contents,
            crawled_at=datetime.now(),
            homepage_internal_links=len(discovered_set),
            homepage_total_links=len(discovered_set) + len(external_links),
            homepage_external_links=len(external_links),
            homepage_internal_links_crawled=len(discovered),
            error="; ".join(errors) if errors else None,
            duration_seconds=time.time() - start,
        )

    def _should_rate_limit(self) -> bool:
        """Only rate-limit local crawlers that use our IP."""
        return self.crawler_type in (CrawlerType.CRAWL4AI, CrawlerType.CUSTOM_HTML)

    def _use_raw_html_for_discovery(self) -> bool:
        """Only local crawlers provide raw HTML for link discovery."""
        return self._should_rate_limit()

    async def _crawl_homepage(self, base: str, errors: List[str]) -> tuple[str, Optional[str]]:
        if self._use_raw_html_for_discovery():
            return await self._crawl_with_retries_with_html("homepage", base, errors)
        return await self._crawl_with_retries("homepage", base, errors), None

    async def _crawl_with_retries(self, page_name: str, url: str, errors: List[str]) -> str:
        result, _ = await self._crawl_with_retries_impl(
            page_name, url, errors, use_html=False
        )
        return result

    async def _crawl_with_retries_with_html(
        self, page_name: str, url: str, errors: List[str]
    ) -> tuple[str, Optional[str]]:
        return await self._crawl_with_retries_impl(
            page_name, url, errors, use_html=True
        )

    async def _crawl_with_retries_impl(
        self, page_name: str, url: str, errors: List[str], use_html: bool
    ) -> tuple[str, Optional[str]]:
        import time

        domain = urlparse(url).netloc

        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting only for local crawlers
                if self._should_rate_limit():
                    async with self._domain_locks[domain]:
                        elapsed = time.time() - self._last_request_time[domain]
                        if elapsed < self.min_delay:
                            wait = self.min_delay - elapsed
                            wait += random.uniform(-0.2 * wait, 0.2 * wait)
                            await asyncio.sleep(max(0, wait))

                        self._last_request_time[domain] = time.time()
                        if use_html:
                            result = await self.crawl_url_with_html(url)
                        else:
                            result = (await self.crawl_url(url), None)
                else:
                    if use_html:
                        result = await self.crawl_url_with_html(url)
                    else:
                        result = (await self.crawl_url(url), None)

                return result

            except Exception as e:
                error_str = str(e)

                if attempt < self.max_retries - 1 and any(code in error_str for code in ["429", "403", "503"]):
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)
                    continue

                if attempt == self.max_retries - 1:
                    errors.append(f"{page_name} ({url}): {e}")

        return "", None

    def _normalize_base(self, domain: str) -> str:
        base = domain.rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"
        return base

    def _page_name(self, url: str, base: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if path == "/":
            return "homepage"
        path = path.rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path

    def _filter_by_pages(self, urls: List[str], pages: List[str]) -> List[str]:
        wanted = {p.strip("/").lower() for p in pages if p}
        filtered = []
        for url in urls:
            path = urlparse(url).path.strip("/").lower()
            if path in wanted:
                filtered.append(url)
        return filtered

    def _discover_links(self, content: str, base: str) -> tuple[List[str], List[str]]:
        if not content:
            return [], []
        base_parsed = urlparse(base)
        base_host = self._normalize_host(base_parsed.netloc)
        skip_path_tokens = (
            "/login", "/log-in", "/signin", "/sign-in", "/signup", "/sign-up",
            "/register", "/auth", "/authenticate", "/oauth", "/sso",
        )
        skip_exts = {
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
            ".css", ".js", ".json", ".xml", ".pdf", ".zip", ".rar",
            ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".eot",
        }

        raw_links = self._extract_links_from_content(content)
        seen = set()
        internal = []
        external = []
        for raw in raw_links:
            cleaned = raw.strip()
            if not cleaned or cleaned.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            absolute = urljoin(base, cleaned)
            absolute, _ = urldefrag(absolute)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                continue
            path_lower = parsed.path.lower()
            if any(token in path_lower for token in skip_path_tokens):
                continue
            if any(path_lower.endswith(ext) for ext in skip_exts):
                continue
            host = self._normalize_host(parsed.netloc)
            canonical = self._canonical_url(absolute)
            if canonical == self._canonical_url(base):
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            if host == base_host or host.endswith(f".{base_host}"):
                internal.append(absolute)
            else:
                external.append(absolute)
        return internal, external

    def _normalize_host(self, host: str) -> str:
        host = host.lower()
        if host.startswith("www."):
            return host[4:]
        return host

    def _canonical_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _extract_links_from_content(self, content: str) -> Iterable[str]:
        links = []
        # HTML href links
        links.extend(
            m.group(1)
            for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', content, flags=re.IGNORECASE)
        )
        # Markdown inline links [text](url)
        links.extend(
            m.group(1)
            for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", content)
        )
        # Markdown autolinks <http://...>
        links.extend(
            m.group(1)
            for m in re.finditer(r"<(https?://[^>]+)>", content)
        )
        return links
