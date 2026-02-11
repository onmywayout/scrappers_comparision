#!/usr/bin/env python3
"""
Analyzes same-domain links on B2B SaaS company homepages - optimized for 589 companies.
"""

import asyncio
import csv
import json
from typing import Dict, List, Set
from urllib.parse import urlparse, urljoin, urlunparse
import statistics

import aiohttp
from bs4 import BeautifulSoup


class HomepageLinkAnalyzer:
    def __init__(self, csv_path: str, output_path: str, max_concurrent: int = 15, timeout: int = 20, max_retries: int = 3):
        self.csv_path = csv_path
        self.output_path = output_path
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        self.results = []
        self.completed_count = 0

        # Browser-like headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def read_domains(self) -> List[str]:
        """Read domains from CSV file."""
        domains = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                domain = row.get('domain', '').strip()
                if domain:
                    domains.append(domain)
        return domains

    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            ''
        ))
        return normalized

    def is_same_domain(self, base_url: str, link_url: str) -> bool:
        """Check if a link URL is from the same domain as the base URL."""
        base_parsed = urlparse(base_url)
        link_parsed = urlparse(link_url)

        base_hostname = base_parsed.hostname or ''
        link_hostname = link_parsed.hostname or ''

        base_hostname = base_hostname.replace('www.', '').lower()
        link_hostname = link_hostname.replace('www.', '').lower()

        return base_hostname == link_hostname

    def is_valid_link(self, href: str, current_page_path: str = '') -> bool:
        """Check if href is a valid link."""
        if not href:
            return False

        href = href.strip()

        if href.startswith(('mailto:', 'tel:', 'javascript:', 'data:', 'void(', '#')):
            return False

        if '#' in href and current_page_path:
            if href.startswith('#'):
                return False
            path_before_anchor = href.split('#')[0]
            if not path_before_anchor or path_before_anchor == current_page_path:
                return False

        return True

    def detect_js_heavy_page(self, html: str, link_count: int) -> bool:
        """Detect if a page appears to be JS-heavy."""
        if link_count < 5:
            soup = BeautifulSoup(html, 'html.parser')

            js_indicators = [
                'id="root"',
                'id="app"',
                'data-reactroot',
                'data-react-root',
                'ng-app',
                'v-cloak',
                '__NEXT_DATA__',
                '__nuxt'
            ]

            html_lower = html.lower()
            for indicator in js_indicators:
                if indicator.lower() in html_lower:
                    return True

            noscript_tags = soup.find_all('noscript')
            for tag in noscript_tags:
                text = tag.get_text().lower()
                if any(word in text for word in ['enable', 'javascript', 'required', 'need']):
                    return True

        return False

    async def fetch_with_retry(self, session: aiohttp.ClientSession, url: str) -> tuple:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                ssl_context = None if attempt < 2 else False

                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        return html, str(response.url), response.status, None
                    else:
                        error_msg = f"HTTP {response.status}"
                        if response.status in [403, 429]:
                            await asyncio.sleep(3)
                        continue

            except asyncio.TimeoutError:
                continue
            except aiohttp.ClientSSLError:
                continue
            except aiohttp.ClientError:
                continue
            except Exception:
                continue

        return None, None, 0, "Failed to fetch"

    async def fetch_and_analyze(self, session: aiohttp.ClientSession, domain: str) -> Dict:
        """Fetch homepage and analyze links for a single domain."""
        urls_to_try = [f'https://{domain}', f'http://{domain}']

        for url in urls_to_try:
            html, final_url, status, error = await self.fetch_with_retry(session, url)

            if html and final_url:
                try:
                    soup = BeautifulSoup(html, 'html.parser')
                    current_page_parsed = urlparse(final_url)
                    current_page_path = current_page_parsed.path

                    all_links = soup.find_all('a', href=True)

                    all_links_set = set()
                    same_domain_links_set = set()
                    same_domain_links_list = []
                    all_links_list = []

                    for link in all_links:
                        href = link.get('href', '').strip()

                        if not self.is_valid_link(href, current_page_path):
                            continue

                        absolute_url = urljoin(final_url, href)
                        normalized_url = self.normalize_url(absolute_url)

                        if normalized_url not in all_links_set:
                            all_links_set.add(normalized_url)
                            all_links_list.append(normalized_url)

                        if self.is_same_domain(final_url, absolute_url):
                            if normalized_url not in same_domain_links_set:
                                same_domain_links_set.add(normalized_url)
                                same_domain_links_list.append(normalized_url)

                    total_links_count = len(all_links_list)
                    same_domain_count = len(same_domain_links_list)

                    notes = ''
                    if self.detect_js_heavy_page(html, same_domain_count):
                        notes = 'Possible JS-heavy page, may not be fully rendered'

                    return {
                        'domain': domain,
                        'total_links': total_links_count,
                        'same_domain_links': same_domain_count,
                        'all_links_array': json.dumps(all_links_list),
                        'same_domain_links_array': json.dumps(same_domain_links_list),
                        'status': 'success',
                        'notes': notes
                    }

                except Exception:
                    continue

        return {
            'domain': domain,
            'total_links': 0,
            'same_domain_links': 0,
            'all_links_array': json.dumps([]),
            'same_domain_links_array': json.dumps([]),
            'status': 'error',
            'notes': 'Failed to fetch or connection timeout'
        }

    async def process_domains(self, domains: List[str]):
        """Process all domains with concurrent limit."""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, force_close=True)

        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def bounded_fetch(domain: str):
                async with semaphore:
                    result = await self.fetch_and_analyze(session, domain)
                    self.results.append(result)
                    self.completed_count += 1

                    # Progress indicator every 50 domains
                    if self.completed_count % 50 == 0:
                        successful = sum(1 for r in self.results if r['status'] == 'success')
                        print(f"Progress: {self.completed_count}/{len(domains)} completed ({successful} successful)")

                    return result

            tasks = [bounded_fetch(domain) for domain in domains]
            await asyncio.gather(*tasks)

    def save_results(self):
        """Save results to CSV."""
        with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['domain', 'total_links', 'same_domain_links', 'status', 'notes', 'same_domain_links_array', 'all_links_array']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

        print(f"\n✓ Results saved to: {self.output_path}")

    def print_statistics(self):
        """Print summary statistics."""
        successful = [r for r in self.results if r['status'] == 'success']

        if not successful:
            print("\nNo successful fetches to analyze.")
            return

        same_domain_counts = [r['same_domain_links'] for r in successful]

        print("\n" + "="*60)
        print("SUMMARY STATISTICS")
        print("="*60)
        print(f"Total domains analyzed: {len(self.results)}")
        print(f"Successful fetches: {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        print(f"Failed/timeout: {len(self.results) - len(successful)}")
        print()
        print(f"Same-domain links per homepage:")
        print(f"  Min:    {min(same_domain_counts)}")
        print(f"  Max:    {max(same_domain_counts)}")
        print(f"  Mean:   {statistics.mean(same_domain_counts):.2f}")
        print(f"  Median: {statistics.median(same_domain_counts):.2f}")

        sorted_counts = sorted(same_domain_counts)
        n = len(sorted_counts)
        p25_idx = n // 4
        p75_idx = 3 * n // 4
        print(f"  P25:    {sorted_counts[p25_idx]}")
        print(f"  P75:    {sorted_counts[p75_idx]}")

        print("\nDistribution (histogram):")
        bins = [0, 10, 20, 30, 50, 75, 100, 150, 200, float('inf')]
        bin_labels = ['0-9', '10-19', '20-29', '30-49', '50-74', '75-99', '100-149', '150-199', '200+']

        histogram = {label: 0 for label in bin_labels}

        for count in same_domain_counts:
            for i in range(len(bins) - 1):
                if bins[i] <= count < bins[i+1]:
                    histogram[bin_labels[i]] += 1
                    break

        max_bar_length = 50
        max_count = max(histogram.values()) if histogram.values() else 1

        for label, count in histogram.items():
            bar_length = int((count / max_count) * max_bar_length) if max_count > 0 else 0
            bar = '█' * bar_length
            percentage = (count / len(successful) * 100) if successful else 0
            print(f"  {label:>10} | {bar} {count} ({percentage:.1f}%)")

        print("="*60)

        js_heavy = [r for r in successful if 'JS-heavy' in r.get('notes', '')]
        if js_heavy:
            print(f"\n⚠ {len(js_heavy)} pages appear to be JS-heavy and may not be fully rendered")

    def run(self):
        """Main execution method."""
        print("Starting homepage link analysis for 589 companies...")
        print(f"Reading domains from: {self.csv_path}")

        domains = self.read_domains()
        print(f"Found {len(domains)} domains to analyze")
        print(f"Settings: max {self.max_concurrent} concurrent, {self.timeout}s timeout, {self.max_retries} retries\n")

        asyncio.run(self.process_domains(domains))
        self.save_results()
        self.print_statistics()


if __name__ == '__main__':
    analyzer = HomepageLinkAnalyzer(
        csv_path='/Users/nicolas/Documents/GitHub/scrap_test/589_creatio_companies.csv',
        output_path='/Users/nicolas/Documents/GitHub/scrap_test/589_companies_results.csv',
        max_concurrent=15,
        timeout=20,
        max_retries=3
    )
    analyzer.run()
