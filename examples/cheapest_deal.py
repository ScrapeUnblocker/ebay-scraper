"""Find the cheapest listing for a keyword by parsing prices across pages.

This shows off the library's price normalization: eBay often returns a raw price
string (e.g. "US $29.99") instead of a parsed number, and the scraper turns that
into a comparable float + currency for you.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/cheapest_deal.py "raspberry pi 5"
"""

from __future__ import annotations

import sys

from ebay_scraper import EbayScraper


def main() -> None:
    # Listing titles may contain emoji / non-Latin text; keep Windows consoles happy.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    keyword = sys.argv[1] if len(sys.argv) > 1 else "raspberry pi 5"

    scraper = EbayScraper()
    listings = scraper.search_pages(keyword, marketplace="ebay.com", max_pages=2, condition="new")

    priced = [item for item in listings if item.price is not None]
    if not priced:
        print("No priced listings found.")
        return

    cheapest = min(priced, key=lambda item: item.price)
    print(f"Cheapest '{keyword}':")
    print(f"  {cheapest.price:.2f} {cheapest.currency or ''}  {cheapest.title}")
    print(f"  seller: {cheapest.seller.username}  ({cheapest.seller.feedback_percent}%)")
    print(f"  {cheapest.url}")


if __name__ == "__main__":
    main()
