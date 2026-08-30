"""Typed data models for eBay search results.

These dataclasses give the scraper a stable, documented output shape regardless of
small differences in the raw API payload (for example, ``price`` being ``null`` while
``priceRaw`` carries the value). See :func:`ebay_scraper.scraper.normalize_listing`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Seller:
    """A listing's seller."""

    username: str | None = None
    feedback_percent: float | None = None
    feedback_score: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Listing:
    """A single normalized eBay listing."""

    position: int | None = None
    listing_id: str | None = None
    title: str | None = None
    url: str | None = None
    image: str | None = None
    condition: str | None = None
    condition_code: str | None = None
    price: float | None = None
    currency: str | None = None
    price_raw: str | None = None
    shipping_cost: float | None = None
    free_shipping: bool | None = None
    sold: int | None = None
    watchers: int | None = None
    bids: int | None = None
    buy_it_now: bool | None = None
    best_offer: bool | None = None
    seller: Seller = field(default_factory=Seller)

    #: Column order used for CSV export.
    CSV_FIELDS = (
        "position",
        "listing_id",
        "title",
        "price",
        "currency",
        "price_raw",
        "condition",
        "condition_code",
        "shipping_cost",
        "free_shipping",
        "seller_username",
        "seller_feedback_percent",
        "seller_feedback_score",
        "watchers",
        "bids",
        "buy_it_now",
        "url",
        "image",
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("CSV_FIELDS", None)
        return data

    def to_row(self) -> dict[str, Any]:
        """Flat mapping suitable for a CSV row (seller fields inlined)."""
        return {
            "position": self.position,
            "listing_id": self.listing_id,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "price_raw": self.price_raw,
            "condition": self.condition,
            "condition_code": self.condition_code,
            "shipping_cost": self.shipping_cost,
            "free_shipping": self.free_shipping,
            "seller_username": self.seller.username,
            "seller_feedback_percent": self.seller.feedback_percent,
            "seller_feedback_score": self.seller.feedback_score,
            "watchers": self.watchers,
            "bids": self.bids,
            "buy_it_now": self.buy_it_now,
            "url": self.url,
            "image": self.image,
        }


@dataclass
class SearchResult:
    """The result of a single eBay search request (one page)."""

    keyword: str | None = None
    marketplace: str | None = None
    page: int | None = None
    page_size: int | None = None
    total_results: int | None = None
    search_url: str | None = None
    exact_matches: bool | None = None
    results_collected: int | None = None
    listings: list[Listing] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.listings)

    def __iter__(self):
        return iter(self.listings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "marketplace": self.marketplace,
            "page": self.page,
            "page_size": self.page_size,
            "total_results": self.total_results,
            "search_url": self.search_url,
            "exact_matches": self.exact_matches,
            "results_collected": self.results_collected,
            "listings": [listing.to_dict() for listing in self.listings],
        }
