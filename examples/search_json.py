"""Search eBay and print normalized listings as JSON.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here   # Windows: set SCRAPEUNBLOCKER_KEY=...
    python examples/search_json.py "mechanical keyboard"

Get a key at https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
"""

from __future__ import annotations

import json
import sys

from ebay_scraper import EbayScraper


def main() -> None:
    # Listing titles may contain emoji / non-Latin text; keep Windows consoles happy.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    keyword = sys.argv[1] if len(sys.argv) > 1 else "mechanical keyboard"
    scraper = EbayScraper()  # reads SCRAPEUNBLOCKER_KEY from the environment
    result = scraper.search(keyword, marketplace="ebay.com", page_size=60)

    print(f"# {result.total_results} total results for {result.keyword!r}")
    print(json.dumps(result.to_dict()["listings"][:10], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
