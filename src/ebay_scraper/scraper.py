"""Core eBay scraping logic built on the ScrapeUnblocker Python SDK.

The heavy lifting (proxying, unblocking, parsing eBay's HTML into JSON) happens on
ScrapeUnblocker's side via the ``ebay_search`` plugin. This module is a thin, typed
wrapper that adds:

* a stable, documented output shape (see :mod:`ebay_scraper.models`);
* price/currency parsing for the many listings where the API returns a raw price
  string (e.g. ``"US $29.99"``) instead of a parsed number;
* transient-error retries with exponential backoff.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from .models import Listing, SearchResult, Seller

try:  # The SDK is a hard runtime dependency, but keep imports resilient for tooling.
    import scrapeunblocker as _su
except ImportError:  # pragma: no cover - only hit when the dep is missing
    _su = None


#: Well-known regional eBay marketplaces accepted by the plugin. Any valid eBay
#: domain works; this list is for discovery/validation and CLI help.
MARKETPLACES = (
    "ebay.com",
    "ebay.co.uk",
    "ebay.de",
    "ebay.com.au",
    "ebay.ca",
    "ebay.fr",
    "ebay.it",
    "ebay.es",
    "ebay.at",
    "ebay.be",
    "ebay.ch",
    "ebay.ie",
    "ebay.nl",
    "ebay.pl",
    "ebay.com.hk",
    "ebay.com.my",
    "ebay.ph",
    "ebay.com.sg",
    "ebay.vn",
)

#: Sort options supported by the plugin.
SORT_OPTIONS = (
    "best_match",
    "newly_listed",
    "ending_soon",
    "price_asc",
    "price_desc",
)

#: Listing-type filters supported by the plugin.
LISTING_TYPES = ("all", "buy_it_now", "auction")

#: Condition filters supported by the plugin.
CONDITIONS = ("new", "open_box", "refurbished", "used", "for_parts")


def _retryable_errors() -> tuple[type[Exception], ...]:
    """Return the SDK exception classes worth retrying, if the SDK is importable."""
    if _su is None:
        return ()
    names = (
        "RateLimitError",
        "ScrapeTimeoutError",
        "BrowserTimeoutError",
        "UpstreamOutageError",
        "ServerError",
        "BlockedError",
        "ConnectionError",
    )
    return tuple(getattr(_su, name) for name in names if hasattr(_su, name))


# Symbols that unambiguously map to a currency code.
_SYMBOL_TO_CODE = {
    "£": "GBP",
    "€": "EUR",
    "¥": "JPY",
    "₩": "KRW",
    "₹": "INR",
    "R$": "BRL",
    "$": "USD",  # bare "$" defaults to USD; qualified forms handled below
}

# Country prefixes eBay puts in front of "$" (e.g. "AU $12.00").
_DOLLAR_PREFIX_TO_CODE = {
    "US": "USD",
    "AU": "AUD",
    "C": "CAD",
    "CA": "CAD",
    "NZ": "NZD",
    "HK": "HKD",
    "SGD": "SGD",
    "SG": "SGD",
}

_CODE_RE = re.compile(r"(?<![A-Za-z])([A-Z]{3})(?![A-Za-z])")
_NUMBER_RE = re.compile(r"[0-9][0-9.,\s]*[0-9]|[0-9]")


def _parse_number(text: str) -> float | None:
    """Parse a localized numeric string into a float.

    Handles both ``1,234.56`` (US) and ``1.234,56`` (EU) styles, plus plain
    ``1234`` and thousands-only forms. Returns ``None`` if no number is found.
    """
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    raw = re.sub(r"\s", "", match.group(0))
    has_dot = "." in raw
    has_comma = "," in raw
    if has_dot and has_comma:
        # The rightmost separator is the decimal separator.
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif has_comma:
        # A single comma with exactly two trailing digits is a decimal comma;
        # otherwise it is a thousands separator.
        if re.fullmatch(r"\d{1,3}(,\d{3})+", raw):
            raw = raw.replace(",", "")
        elif re.fullmatch(r"\d+,\d{1,2}", raw):
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    # dot-only or digit-only strings are already valid floats
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_currency(text: str) -> str | None:
    """Extract an ISO-ish currency code from a raw price string."""
    # An explicit 3-letter code wins (e.g. "KRW105,964.42", "EUR 15,00").
    code = _CODE_RE.search(text)
    if code:
        return code.group(1)
    # Qualified dollar, e.g. "AU $12.00" / "US $9.99".
    dollar = re.search(r"([A-Za-z]{1,3})\s*\$", text)
    if dollar:
        prefix = dollar.group(1).upper()
        if prefix in _DOLLAR_PREFIX_TO_CODE:
            return _DOLLAR_PREFIX_TO_CODE[prefix]
    for symbol, mapped in _SYMBOL_TO_CODE.items():
        if symbol in text:
            return mapped
    return None


def parse_price(
    price: Any = None,
    currency: Any = None,
    price_raw: Any = None,
) -> tuple[float | None, str | None]:
    """Best-effort (amount, currency) from the plugin's price fields.

    Prefers the already-parsed ``price``/``currency`` when present, otherwise falls
    back to parsing ``price_raw`` (e.g. ``"US $29.99"`` -> ``(29.99, "USD")``).
    """
    amount: float | None = None
    if isinstance(price, (int, float)):
        amount = float(price)
    code = currency if isinstance(currency, str) and currency else None

    if (amount is None or code is None) and isinstance(price_raw, str) and price_raw.strip():
        if amount is None:
            amount = _parse_number(price_raw)
        if code is None:
            code = _parse_currency(price_raw)
    return amount, code


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^\d]", "", value)
        return int(digits) if digits else None
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return _parse_number(value)
    return None


def normalize_seller(raw: Any) -> Seller:
    """Flatten the nested seller object into a :class:`Seller`."""
    if not isinstance(raw, dict):
        return Seller(username=raw if isinstance(raw, str) else None)
    return Seller(
        username=raw.get("username"),
        feedback_percent=_to_float(raw.get("feedbackPercent")),
        feedback_score=_to_int(raw.get("feedbackScore")),
    )


def normalize_listing(raw: dict[str, Any]) -> Listing:
    """Convert one raw plugin listing dict into a typed :class:`Listing`."""
    price, currency = parse_price(raw.get("price"), raw.get("currency"), raw.get("priceRaw"))
    shipping = raw.get("shippingCost")
    if shipping is None:
        shipping = raw.get("shippingRaw")
    return Listing(
        position=_to_int(raw.get("position")),
        listing_id=raw.get("listingId"),
        title=raw.get("title"),
        url=raw.get("url"),
        image=raw.get("image"),
        condition=raw.get("condition"),
        condition_code=raw.get("conditionCode"),
        price=price,
        currency=currency,
        price_raw=raw.get("priceRaw"),
        shipping_cost=_to_float(shipping),
        free_shipping=raw.get("freeShipping"),
        sold=_to_int(raw.get("sold")),
        watchers=_to_int(raw.get("watchers")),
        bids=_to_int(raw.get("bids")),
        buy_it_now=raw.get("buyItNow"),
        best_offer=raw.get("bestOffer"),
        seller=normalize_seller(raw.get("seller")),
    )


def normalize_response(raw: dict[str, Any]) -> SearchResult:
    """Convert a full raw plugin response into a :class:`SearchResult`."""
    raw = raw or {}
    listings = [normalize_listing(item) for item in (raw.get("results") or [])]
    return SearchResult(
        keyword=raw.get("keyword"),
        marketplace=raw.get("marketplace"),
        page=_to_int(raw.get("page")),
        page_size=_to_int(raw.get("pageSize")),
        total_results=_to_int(raw.get("totalResults")),
        search_url=raw.get("searchUrl"),
        exact_matches=raw.get("exactMatches"),
        results_collected=_to_int(raw.get("resultsCollected")),
        listings=listings,
    )


class EbayScraper:
    """A small, typed client for scraping eBay search listings.

    Parameters
    ----------
    api_key:
        Your ScrapeUnblocker API key. If omitted, the SDK reads it from the
        ``SCRAPEUNBLOCKER_KEY`` environment variable.
    timeout, max_retries:
        Passed through to the underlying SDK client.
    retries:
        How many times to retry a request on transient errors (rate limit,
        timeout, upstream outage, ...). This is on top of the SDK's own retries.
    backoff:
        Base seconds for exponential backoff between retries.
    client:
        Inject a pre-built client (mainly for testing). If given, ``api_key`` and
        ``timeout``/``max_retries`` are ignored.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 180.0,
        max_retries: int = 2,
        retries: int = 2,
        backoff: float = 1.5,
        client: Any = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            if _su is None:  # pragma: no cover - only when dep missing
                raise RuntimeError(
                    "The 'scrapeunblocker' package is required. Install it with "
                    "`pip install scrapeunblocker`."
                )
            kwargs: dict[str, Any] = {"timeout": timeout, "max_retries": max_retries}
            if api_key:
                kwargs["api_key"] = api_key
            self._client = _su.Client(**kwargs)
        self.retries = retries
        self.backoff = backoff
        self._sleep = sleep

    def search(
        self,
        keyword: str,
        *,
        marketplace: str = "ebay.com",
        page: int = 1,
        page_size: int = 60,
        condition: str | None = None,
        sort: str = "best_match",
        listing_type: str = "all",
        min_price: float | None = None,
        max_price: float | None = None,
        free_shipping: bool = False,
        seller: str | None = None,
        category: str | None = None,
        proxy_country: str | None = None,
    ) -> SearchResult:
        """Search one page of an eBay marketplace and return normalized listings."""
        if not keyword or not keyword.strip():
            raise ValueError("keyword must be a non-empty string")

        raw = self._call_with_retry(
            keyword=keyword,
            marketplace=marketplace,
            page=page,
            page_size=page_size,
            condition=condition,
            sort=sort,
            listing_type=listing_type,
            min_price=min_price,
            max_price=max_price,
            free_shipping=free_shipping,
            seller=seller,
            category=category,
            proxy_country=proxy_country,
        )
        return normalize_response(raw)

    def search_pages(
        self,
        keyword: str,
        *,
        max_pages: int = 1,
        start_page: int = 1,
        **kwargs: Any,
    ) -> list[Listing]:
        """Collect listings across several pages into a single flat list.

        Stops early once a page returns no listings.
        """
        collected: list[Listing] = []
        for page in range(start_page, start_page + max(1, max_pages)):
            result = self.search(keyword, page=page, **kwargs)
            if not result.listings:
                break
            collected.extend(result.listings)
        return collected

    def _call_with_retry(self, **params: Any) -> dict[str, Any]:
        retryable = _retryable_errors()
        attempt = 0
        while True:
            try:
                return self._client.ebay_search(**_strip_none(params))
            except retryable as exc:  # type: ignore[misc]
                if attempt >= self.retries:
                    raise
                delay = self.backoff * (2**attempt)
                attempt += 1
                _log_retry(exc, attempt, delay)
                self._sleep(delay)


def _strip_none(params: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is None/falsey-default so the SDK uses its defaults."""
    keyword = params.get("keyword")
    cleaned = {
        k: v for k, v in params.items() if k != "keyword" and v is not None and v is not False
    }
    return {"keyword": keyword, **cleaned}


def _log_retry(exc: Exception, attempt: int, delay: float) -> None:  # pragma: no cover
    import logging

    logging.getLogger("ebay_scraper").warning(
        "transient error (%s); retry %d in %.1fs", type(exc).__name__, attempt, delay
    )
