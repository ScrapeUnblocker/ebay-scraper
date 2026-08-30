"""ebay-scraper — a clean, typed eBay listings scraper built on ScrapeUnblocker.

Search any regional eBay marketplace (ebay.com, ebay.co.uk, ebay.de, ...) and get
back normalized listings: title, price, condition, seller, shipping and more.

Powered by ScrapeUnblocker — https://scrapeunblocker.com

Basic usage::

    from ebay_scraper import EbayScraper

    scraper = EbayScraper()  # reads SCRAPEUNBLOCKER_KEY from the environment
    result = scraper.search("mechanical keyboard", marketplace="ebay.com")
    for listing in result.listings:
        print(listing.title, listing.price, listing.currency)
"""

from __future__ import annotations

from .models import Listing, SearchResult, Seller
from .scraper import MARKETPLACES, EbayScraper

__version__ = "0.1.0"

__all__ = [
    "EbayScraper",
    "Listing",
    "Seller",
    "SearchResult",
    "MARKETPLACES",
    "__version__",
]
