import csv
from pathlib import Path
from typing import List


def load_domains_csv(path: Path) -> List[str]:
    """Load domains from CSV. Expects a 'domain' column (or first column)."""
    domains = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row.get("domain") or row.get("url") or list(row.values())[0]
            domain = domain.strip()
            if domain:
                if not domain.startswith("http"):
                    domain = f"https://{domain}"
                domains.append(domain)
    return domains
