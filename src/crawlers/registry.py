from src.types import CrawlerType
from src.crawlers.base import BaseCrawler
from src.config import Config


def get_crawler(crawler_type: CrawlerType, config: Config) -> BaseCrawler:
    if crawler_type == CrawlerType.FIRECRAWL:
        from src.crawlers.firecrawl_crawler import FirecrawlCrawler
        return FirecrawlCrawler(
            api_key=config.firecrawl_api_key,
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    elif crawler_type == CrawlerType.CRAWL4AI:
        from src.crawlers.crawl4ai_crawler import Crawl4AICrawler
        return Crawl4AICrawler(
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    elif crawler_type == CrawlerType.JINA:
        from src.crawlers.jina_crawler import JinaReaderCrawler
        return JinaReaderCrawler(
            api_key=config.jina_api_key,
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    elif crawler_type == CrawlerType.SCRAPINGBEE:
        from src.crawlers.scrapingbee_crawler import ScrapingBeeCrawler
        return ScrapingBeeCrawler(
            api_key=config.scrapingbee_api_key,
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    elif crawler_type == CrawlerType.SCRAPERAPI:
        from src.crawlers.scraperapi_crawler import ScraperAPICrawler
        return ScraperAPICrawler(
            api_key=config.scraperapi_api_key,
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    elif crawler_type == CrawlerType.CUSTOM_HTML:
        from src.crawlers.custom_html_crawler import CustomHTMLCrawler
        return CustomHTMLCrawler(
            timeout=config.crawler_timeout,
            max_retries=config.max_retries,
            min_delay=config.min_delay_between_requests,
        )
    else:
        raise ValueError(f"Unknown crawler type: {crawler_type}")
