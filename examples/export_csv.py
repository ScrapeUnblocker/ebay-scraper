"""Search several pages of an eBay marketplace and export the listings to CSV.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/export_csv.py "wireless earbuds" ebay.co.uk

Docs: https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
"""

from __future__ import annotations

import csv
import sys

from ebay_scraper import EbayScraper
from ebay_scraper.models import Listing


def main() -> None:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "wireless earbuds"
    marketplace = sys.argv[2] if len(sys.argv) > 2 else "ebay.com"

    scraper = EbayScraper()
    listings = scraper.search_pages(keyword, marketplace=marketplace, max_pages=2, sort="price_asc")

    out_path = "ebay_listings.csv"
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(Listing.CSV_FIELDS))
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing.to_row())

    print(f"Wrote {len(listings)} listing(s) from {marketplace} to {out_path}")


if __name__ == "__main__":
    main()
