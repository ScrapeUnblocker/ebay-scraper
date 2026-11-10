# ebay-scraper

[![CI](https://github.com/ScrapeUnblocker/ebay-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ScrapeUnblocker/ebay-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A clean, typed **eBay listings scraper** in Python. Search any regional eBay
marketplace (`ebay.com`, `ebay.co.uk`, `ebay.de`, …) and get back normalized
listings — **title, price, condition, seller, shipping, watchers and more** — as
Python objects, JSON or CSV.

> **Powered by [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos).**
> The proxying, unblocking and HTML‑to‑JSON parsing all happen server‑side via the
> official eBay search plugin, so this library stays small and reliable.

## Features

- 🔎 Search any regional eBay marketplace by keyword.
- 🧱 **Typed output** (`SearchResult` / `Listing` / `Seller`) with `to_dict()`,
  `to_row()` and CSV export helpers.
- 💵 **Robust price parsing** — eBay frequently returns a raw price string like
  `"US $29.99"` or `"EUR 15,00"`; the scraper turns that into a comparable
  `(amount, currency)` pair, handling US and European number formats.
- 🎛️ Filters for condition, sort order, listing type, price range, free shipping,
  seller and category.
- 📄 Multi‑page collection with `search_pages(...)`.
- 🔁 Automatic retries on transient errors (rate limit, timeout, upstream outage).
- 🖥️ A `ebay-scraper` CLI with `json`, `csv` and `table` output.
- ✅ Offline unit tests (the SDK is mocked — no API credit spent in CI).

## Install

```bash
pip install .
# or, for development:
pip install -e ".[dev]"
```

Requires Python 3.11+ and a ScrapeUnblocker API key. Copy `.env.example` to `.env`
(or export the variable) and set your key — get one at
[scrapeunblocker.com](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos):

```bash
export SCRAPEUNBLOCKER_KEY=your_key_here     # Windows: set SCRAPEUNBLOCKER_KEY=...
```

## CLI usage

```bash
# JSON to stdout
ebay-scraper search "mechanical keyboard"

# German marketplace, 2 pages, new only, cheapest first, as CSV
ebay-scraper search "airpods pro" \
  --marketplace ebay.de --pages 2 --condition new --sort price_asc \
  --format csv --output airpods.csv

# Compact table
ebay-scraper search "raspberry pi 5" --min-price 40 --format table
```

Key options: `--marketplace`, `--pages`, `--page-size {60,120,240}`, `--condition`,
`--sort`, `--listing-type`, `--min-price`, `--max-price`, `--free-shipping`,
`--seller`, `--category`, `--country`, `--format {json,csv,table}`, `--output`.

## Library usage

```python
from ebay_scraper import EbayScraper

scraper = EbayScraper()  # reads SCRAPEUNBLOCKER_KEY from the environment

result = scraper.search("mechanical keyboard", marketplace="ebay.com", page_size=60)
print(result.total_results, "results")

for listing in result.listings[:5]:
    print(f"{listing.price} {listing.currency}  {listing.condition}  {listing.title}")
    print(f"  by {listing.seller.username} ({listing.seller.feedback_percent}%)")
    print(f"  {listing.url}")

# Collect across pages into one flat list
deals = scraper.search_pages(
    "wireless earbuds", marketplace="ebay.co.uk", max_pages=3, condition="new", sort="price_asc"
)
cheapest = min((d for d in deals if d.price is not None), key=lambda d: d.price)
print("Cheapest:", cheapest.price, cheapest.currency, cheapest.title)
```

### Example output

```json
[
  {
    "position": 1,
    "listing_id": "267543612733",
    "title": "NuPhy X BH65 Magnetic Switch Gaming Keyboard, Black",
    "url": "https://www.ebay.com/itm/267543612733",
    "price": 78.45,
    "currency": "USD",
    "price_raw": "US $78.45",
    "condition": "Pre-Owned",
    "condition_code": "used",
    "watchers": 36,
    "buy_it_now": true,
    "seller": { "username": "anexample", "feedback_percent": 99.7, "feedback_score": 14000 }
  }
]
```

See [`examples/`](examples/) for runnable scripts: JSON output
(`search_json.py`), CSV export (`export_csv.py`) and a cheapest‑deal finder
(`cheapest_deal.py`).

## Project layout

```
src/ebay_scraper/
  __init__.py      package exports + __version__
  models.py        Listing / Seller / SearchResult dataclasses
  scraper.py       EbayScraper + normalization / price parsing / retries
  cli.py           argparse CLI (the `ebay-scraper` command)
examples/          runnable example scripts
tests/             offline unit tests (SDK mocked)
```

## Development

```bash
make install   # editable install with dev extras
make lint      # ruff check
make format    # ruff format
make test      # pytest (offline, no API credit)
make run       # run the JSON example
```

## How it works

Under the hood this calls the ScrapeUnblocker Python SDK's `ebay_search` method,
which hits the [eBay search plugin](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos).
ScrapeUnblocker handles the unblocking and returns structured JSON; this library
normalizes it into typed objects and adds price parsing, paging and retries.

## Links

- 🌐 ScrapeUnblocker — https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
- 📚 Documentation — https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos

## License

[MIT](LICENSE) © 2026 ScrapeUnblocker
