"""Command-line interface for ebay-scraper.

Examples::

    ebay-scraper search "mechanical keyboard" --marketplace ebay.de --pages 2
    ebay-scraper search "airpods pro" --condition new --sort price_asc --format csv -o out.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections.abc import Sequence
from typing import Any

from . import __version__
from .models import Listing
from .scraper import (
    CONDITIONS,
    LISTING_TYPES,
    MARKETPLACES,
    SORT_OPTIONS,
    EbayScraper,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ebay-scraper",
        description="Scrape eBay listings via ScrapeUnblocker.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search an eBay marketplace.")
    search.add_argument("keyword", help="Search phrase or part number.")
    search.add_argument(
        "-m",
        "--marketplace",
        default="ebay.com",
        help="Regional eBay site (e.g. ebay.com, ebay.co.uk, ebay.de). "
        f"Known: {', '.join(MARKETPLACES)}",
    )
    search.add_argument("--pages", type=int, default=1, help="Number of pages to fetch.")
    search.add_argument("--start-page", type=int, default=1, help="First page number.")
    search.add_argument(
        "--page-size",
        type=int,
        default=60,
        choices=(60, 120, 240),
        help="Listings per page.",
    )
    search.add_argument("--condition", choices=CONDITIONS, help="Item condition filter.")
    search.add_argument(
        "--sort", choices=SORT_OPTIONS, default="best_match", help="Result ordering."
    )
    search.add_argument(
        "--listing-type", choices=LISTING_TYPES, default="all", help="Listing type."
    )
    search.add_argument("--min-price", type=float, help="Minimum price.")
    search.add_argument("--max-price", type=float, help="Maximum price.")
    search.add_argument("--free-shipping", action="store_true", help="Only free-shipping listings.")
    search.add_argument("--seller", help="Restrict to a seller username.")
    search.add_argument("--category", help="eBay category id (e.g. 131090).")
    search.add_argument("--country", help="Exit-IP country (ISO-2, e.g. US, DE).")
    search.add_argument(
        "-f",
        "--format",
        choices=("json", "csv", "table"),
        default="json",
        help="Output format.",
    )
    search.add_argument("-o", "--output", help="Write output to a file instead of stdout.")
    search.add_argument(
        "--api-key",
        help="ScrapeUnblocker API key (defaults to SCRAPEUNBLOCKER_KEY env var).",
    )
    return parser


def _render_json(listings: list[Listing]) -> str:
    return json.dumps([listing.to_dict() for listing in listings], indent=2, ensure_ascii=False)


def _render_csv(listings: list[Listing]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(Listing.CSV_FIELDS))
    writer.writeheader()
    for listing in listings:
        writer.writerow(listing.to_row())
    return buffer.getvalue()


def _render_table(listings: list[Listing]) -> str:
    rows = []
    for listing in listings:
        price = ""
        if listing.price is not None:
            price = f"{listing.price:.2f} {listing.currency or ''}".strip()
        elif listing.price_raw:
            price = listing.price_raw
        title = (listing.title or "")[:60]
        rows.append(f"{price:>16}  {(listing.condition or '-'):<12}  {title}")
    header = f"{'PRICE':>16}  {'CONDITION':<12}  TITLE"
    return "\n".join([header, "-" * len(header), *rows])


def _render(listings: list[Listing], fmt: str) -> str:
    if fmt == "csv":
        return _render_csv(listings)
    if fmt == "table":
        return _render_table(listings)
    return _render_json(listings)


def _run_search(args: argparse.Namespace) -> int:
    scraper = EbayScraper(api_key=args.api_key)
    common: dict[str, Any] = dict(
        marketplace=args.marketplace,
        page_size=args.page_size,
        condition=args.condition,
        sort=args.sort,
        listing_type=args.listing_type,
        min_price=args.min_price,
        max_price=args.max_price,
        free_shipping=args.free_shipping,
        seller=args.seller,
        category=args.category,
        proxy_country=args.country,
    )
    listings = scraper.search_pages(
        args.keyword,
        max_pages=args.pages,
        start_page=args.start_page,
        **common,
    )
    output = _render(listings, args.format)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as handle:
            handle.write(output)
        print(f"Wrote {len(listings)} listing(s) to {args.output}", file=sys.stderr)
    else:
        print(output)
    return 0


def _force_utf8_stdout() -> None:
    """Emit UTF-8 to stdout even on consoles that default to a legacy codepage.

    Listing titles routinely contain emoji and non-Latin characters; on a Windows
    cp1252 console a bare ``print`` would otherwise raise ``UnicodeEncodeError``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - stream not reconfigurable
                pass


def main(argv: Sequence[str] | None = None) -> int:
    _force_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "search":
        try:
            return _run_search(args)
        except ValueError as exc:
            parser.error(str(exc))
    parser.error("unknown command")
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
