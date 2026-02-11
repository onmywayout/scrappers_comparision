# B2B SaaS Homepage Link Analysis - Final Report
## Analysis of 589 Companies

---

## Executive Summary

This report analyzes same-domain link counts on B2B SaaS company homepages to establish benchmarks for typical navigation complexity and identify patterns in site structure.

**Key Findings:**
- **Success Rate:** 95.2% (561/589 companies successfully scraped)
- **Valid Data:** 523 companies (93.2% of successful scrapes had 1+ links)
- **Scraping Issues:** 38 companies (6.8%) returned 0 links - likely JS-heavy or rendering issues
- **Typical Homepage:** 16 same-domain links (median), 21 links (mean)
- **Common Range:** 61.6% of sites have 10-19 links or fewer

---

## Methodology

### Scraping Technology
- **HTTP Client:** aiohttp (async, 15 concurrent requests)
- **Parser:** BeautifulSoup4
- **Compression:** Brotli support enabled
- **Timeout:** 20 seconds per request
- **Retries:** 3 attempts per domain
- **SSL Handling:** Fallback to SSL-disabled mode for problematic certificates

### Link Classification
**Included:**
- All `<a href>` tags with valid URLs
- Same-domain links (normalized hostname comparison)
- Both relative and absolute URLs

**Excluded:**
- `mailto:`, `tel:`, `javascript:`, `data:` protocols
- Anchor-only links (`#section`)
- Same-page navigation (`/page#section`)
- Duplicate URLs (normalized to remove fragments/trailing slashes)

---

## Data Quality Assessment

### Overall Success Metrics
| Metric | Count | Percentage |
|--------|-------|------------|
| Total Domains Analyzed | 589 | 100.0% |
| Successful HTTP Fetches | 561 | 95.2% |
| Failed/Timeout | 28 | 4.8% |
| Valid Scraping (1+ links) | 523 | 88.8% |
| **Scraping Issues (0 links)** | **38** | **6.8%** ⚠️ |

### 0-Link Sites Analysis
**Total:** 38 companies (6.8% of successful fetches)

**Likely Causes:**
- **JS-Heavy Sites:** 21 companies (55.3% of 0-link sites)
  - React, Angular, Vue, Next.js frameworks detected
  - Require browser rendering (Playwright/Selenium)
- **Minimal Landing Pages:** Some sites truly have no navigation
- **Bot Protection:** Cloudflare/similar blocking scrapers

**Examples of 0-Link Sites:**
```
anagramsecurity.com [JS-heavy]
anodet.com [JS-heavy]
cognext.ai [JS-heavy]
deltabravo.ai [JS-heavy]
chiirp.com [JS-heavy]
avala.ai
beyondmath.com
breachwaycapital.com
```

**Recommendation:** Exclude these 38 sites from analysis or use browser automation for re-scraping.

---

## Statistical Analysis (Valid Sites Only)

### Based on 523 Sites with 1+ Links

| Statistic | Value | Interpretation |
|-----------|-------|----------------|
| **Mean** | 21.3 links | Average complexity |
| **Median** | 16 links | Typical site |
| **Mode** | 10 links | Most common |
| **Std Dev** | 19.78 | High variability |
| **Min** | 1 link | Minimal navigation |
| **Max** | 187 links | Extensive navigation |

### Percentiles
| Percentile | Links | Meaning |
|------------|-------|---------|
| P10 | 5 | 10% of sites have ≤5 links |
| P25 | 9 | 25% have ≤9 links |
| **P50** | **16** | **Median site** |
| P75 | 27 | 75% have ≤27 links |
| P90 | 42 | 90% have ≤42 links |

### Total Links (Including External)
- **Mean:** 29.1 links total
- **Median:** 22 links total
- **Same-Domain Ratio:** 71.3% (most links stay on-site)

---

## Distribution Analysis

### Link Count Categories (Excluding 0-Link Sites)

| Category | Count | % of Valid Sites | Cumulative % | Interpretation |
|----------|-------|------------------|--------------|----------------|
| **1-9 links** | 134 | 25.6% | 25.6% | **Minimal** - Simple landing pages |
| **10-19 links** | 188 | 35.9% | 61.6% | **Medium** - Typical SaaS homepage |
| **20-29 links** | 86 | 16.4% | 78.0% | **Good** - Comprehensive navigation |
| **30-49 links** | 74 | 14.1% | 92.2% | **Complex** - Multiple product lines |
| **50-74 links** | 28 | 5.4% | 97.5% | **High** - Enterprise sites |
| **75-99 links** | 10 | 1.9% | 99.4% | **Very High** - Mega menus |
| **100+ links** | 3 | 0.6% | 100.0% | **Extreme** - Massive navigation |

### Visual Distribution

```
     0 links | ██████████ (38 sites, 6.8%) ⚠️  SCRAPING ISSUES
     1-9     | ███████████████████████████████████ (134 sites, 25.6%)
    10-19    | ██████████████████████████████████████████████████ (188 sites, 35.9%) ← MOST COMMON
    20-29    | ██████████████████████ (86 sites, 16.4%)
    30-49    | ███████████████████ (74 sites, 14.1%)
    50-74    | ███████ (28 sites, 5.4%)
    75-99    | ██ (10 sites, 1.9%)
   100+      | █ (3 sites, 0.6%)
```

### Key Insights

**✅ What's Typical:**
- **61.6%** of B2B SaaS sites have 10-19 links or fewer
- **78%** have fewer than 30 links
- Median site has **16 same-domain links**

**⚠️ What's Unusual:**
- Sites with **50+ links** (7.8%) - enterprise/complex sites
- Sites with **1-5 links** (12.8%) - minimal landing pages or early-stage startups
- Sites with **100+ links** (0.6%) - extremely complex navigation

---

## Top Performers

### Top 10 Companies by Same-Domain Links

| Rank | Company | Links | Category |
|------|---------|-------|----------|
| 1 | **playroll.com** | 187 | Global payroll platform |
| 2 | **amenify.com** | 133 | Property management |
| 3 | **secondshop.ca** | 131 | E-commerce platform |
| 4 | **akitra.com** | 97 | AI platform |
| 5 | **synchrony.com** | 97 | Financial services |
| 6 | **maestra.ai** | 95 | Video editing AI |
| 7 | **strsoh.org** | 88 | Healthcare |
| 8 | **lemonlight.com** | 85 | Video production |
| 9 | **nowsignage.com** | 84 | Digital signage |
| 10 | **meetingsbooker.com** | 82 | Meeting management |

**Pattern:** Enterprise platforms with multiple products, extensive documentation, and resource centers.

### Bottom 10 Companies (Excluding 0-Link Sites)

| Rank | Company | Links | Notes |
|------|---------|-------|-------|
| 1 | conkarta.com | 1 | JS-heavy |
| 2 | helloannie.com | 1 | - |
| 3 | tuhk.com | 1 | - |
| 4 | 257.co | 2 | - |
| 5 | 49ing.ai | 2 | - |
| 6 | amplify.xyz | 2 | JS-heavy |
| 7 | amherstintelligentsecurity.com | 2 | - |
| 8 | born.com | 2 | - |
| 9 | bravi.app | 2 | - |
| 10 | boopwithme.com | 2 | - |

**Pattern:** Minimal landing pages, early-stage startups, or single-product focus.

---

## Detailed Breakdown

### Sites by Navigation Complexity

#### Minimal (1-5 links): 67 sites (12.8%)
- Single product/service focus
- Simple "Get Started" or "Contact" navigation
- Often early-stage startups

#### Low (6-10 links): 95 sites (18.2%)
- Basic navigation (Home, About, Pricing, Contact)
- Limited product offerings
- Typical for bootstrapped SaaS

#### Medium (11-20 links): 168 sites (32.1%) ← **MOST COMMON**
- Standard B2B SaaS navigation
- Product pages, Resources, Blog, Docs
- 1-3 main product lines

#### Good (21-50 links): 152 sites (29.1%)
- Comprehensive site structure
- Multiple product lines
- Extensive resources/documentation
- Well-established companies

#### High (50+ links): 41 sites (7.8%)
- Enterprise-level sites
- Many products/services
- Large resource libraries
- Mega menus with subcategories

---

## JS-Heavy Page Detection

### Summary
- **Total JS-Heavy Pages:** 25 (4.5% of successful fetches)
- **JS-Heavy with 0 links:** 21 (55.3% of 0-link sites)
- **JS-Heavy with 1+ links:** 4 (0.8% of valid sites)

### Framework Detection
Common indicators found:
- React (`data-reactroot`, `id="root"`)
- Next.js (`__NEXT_DATA__`)
- Angular (`ng-app`)
- Vue (`v-cloak`)
- Nuxt (`__nuxt`)

### Impact
**High Correlation:** 55% of 0-link sites are JS-heavy, suggesting client-side rendering prevents proper scraping.

**Recommendation:** Use Playwright or Selenium for these 21 sites to enable JavaScript execution.

---

## Comparative Analysis: Test Subset vs Full Dataset

### Your Original 21-Company Test Subset

| Metric | Test Subset (21) | Full Dataset (523) | Difference |
|--------|------------------|-------------------|------------|
| Mean | 63.3 links | 21.3 links | **+197%** ⬆️ |
| Median | 51 links | 16 links | **+219%** ⬆️ |
| 0-19 links | 0% | 61.6% | **Missing majority** ❌ |
| 50+ links | 52% | 7.8% | **7x overrepresentation** ❌ |

**Verdict:** NOT REPRESENTATIVE
- Heavily biased toward large, established companies (HubSpot, Cloudflare, Twilio, MongoDB)
- Missing the "long tail" of typical B2B SaaS sites
- Represents top 10-15% by complexity, not median company

---

## Representative Sample

### How to Get Representative Sample

**Method:** Stratified Random Sampling

**For n=10 companies:**

| Stratum | Population % | Sample Size |
|---------|-------------|-------------|
| 1-9 links | 25.6% | 3 companies |
| 10-19 links | 35.9% | 4 companies |
| 20-29 links | 16.4% | 2 companies |
| 30-49 links | 14.1% | 1 company |
| 50+ links | 7.8% | 1 company |

**Representative 10-Company Sample:**

| # | Company | Links | Category |
|---|---------|-------|----------|
| 1 | aktos.ai | 7 | 1-9 links |
| 2 | neuronfactory.ai | 8 | 1-9 links |
| 3 | dealercontrolledsolutions.com | 9 | 1-9 links |
| 4 | caribou.care | 11 | 10-19 links |
| 5 | breezy.io | 14 | 10-19 links |
| 6 | getpalm.com | 15 | 10-19 links |
| 7 | flywl.com | 19 | 10-19 links |
| 8 | suppapp.com | 20 | 20-29 links |
| 9 | bipsync.com | 29 | 20-29 links |
| 10 | propper.ai | 32 | 30-49 links |

*(Bonus: amenify.com with 133 links represents the 50+ category)*

---

## Key Insights & Recommendations

### Primary Findings

1. **Typical B2B SaaS Homepage:** 10-20 same-domain links
2. **Most Common:** 10-19 link range (35.9% of sites)
3. **Same-Domain Ratio:** 71% of all links stay on-site
4. **High Variability:** Standard deviation of 19.78 suggests wide range of approaches

### Industry Benchmarks

**If you have...**

- **1-9 links:** You're in the minimal category (25.6% of sites)
  - Common for: Early-stage startups, single-product focus, simple landing pages

- **10-19 links:** You're typical (35.9% of sites) ✅
  - Common for: Standard B2B SaaS, 1-2 products, growing companies

- **20-29 links:** You're above average (16.4% of sites)
  - Common for: Multi-product companies, comprehensive documentation

- **30-49 links:** You're in the complex category (14.1% of sites)
  - Common for: Enterprise software, multiple product lines

- **50+ links:** You're in the high-complexity tier (7.8% of sites)
  - Common for: Large enterprises, extensive product portfolios

### Actionable Recommendations

**For Analysis:**
1. ✅ Use the 523 sites with 1+ links as your baseline
2. ⚠️ Exclude or separately analyze the 38 sites with 0 links
3. 🔄 Re-scrape the 21 JS-heavy sites with Playwright/Selenium if needed
4. 📊 Use median (16 links) rather than mean (21 links) for typical site

**For Benchmarking:**
1. Compare your site to the **10-19 link range** (typical)
2. If under 10 links: Consider adding product pages, resources, blog
3. If over 50 links: Audit for navigation complexity, consider simplification

**For Sampling:**
1. Use stratified random sampling, not convenience sampling
2. Include sites from all link count ranges
3. Avoid cherry-picking well-known brands
4. Minimum sample size: 30 for statistical validity

---

## Technical Appendix

### Scraping Success Factors

**Why 95% Success Rate?**
- Brotli compression support (critical - fixed 60% initial failures)
- Browser-like headers
- SSL fallback handling
- Retry logic (3 attempts)
- Async concurrent requests (15 simultaneous)

**Remaining 5% Failures:**
- Bot protection (Cloudflare, etc.)
- SSL certificate issues
- Connection timeouts
- Domain resolution failures

### Data Files

**Main Results:** `589_companies_results.csv`
- All 589 companies with scraping results
- Columns: domain, total_links, same_domain_links, status, notes, same_domain_links_array, all_links_array

**Representative Sample:** `representative_sample_10_valid.csv`
- 10-company stratified sample
- Excludes 0-link sites
- Proportionally represents all link count ranges

**Test Subset:** `test_subset_21_results.csv`
- Your original 21 well-known companies
- Biased toward enterprise (not representative)

---

## Conclusion

The analysis of 589 B2B SaaS companies reveals that **the typical homepage has 10-20 same-domain links**, with significant variability based on company size, product complexity, and business model.

**Key Takeaway:** Most B2B SaaS sites (61.6%) have fewer than 20 links, contrary to the perception that successful SaaS companies need extensive navigation. Simplicity is common, even among successful companies.

**For Representative Testing:** Use stratified sampling with emphasis on the 10-19 link range (35.9% of population), not just well-known brands.

**Data Quality Note:** 6.8% of sites returned 0 links (likely scraping issues); exclude from analysis or re-scrape with browser automation.

---

## Report Metadata

- **Date Generated:** 2026-02-10
- **Dataset Size:** 589 companies (561 successful, 523 valid)
- **Analysis Period:** Single scraping pass
- **Tools Used:** Python, aiohttp, BeautifulSoup4, Brotli
- **Statistical Methods:** Descriptive statistics, stratified sampling
- **Confidence Level:** High (n=523 for valid data)

---

*End of Report*
