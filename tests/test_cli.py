"""Offline tests for the CLI arg parser and output rendering."""

from __future__ import annotations

import csv
import io
import json

import pytest

from ebay_scraper import cli
from ebay_scraper.models import Listing, Seller


def test_parser_defaults():
    args = cli.build_parser().parse_args(["search", "airpods"])
    assert args.command == "search"
    assert args.keyword == "airpods"
    assert args.marketplace == "ebay.com"
    assert args.pages == 1
    assert args.format == "json"


def test_parser_rejects_bad_sort():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["search", "x", "--sort", "cheapest"])


def test_parser_rejects_bad_page_size():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["search", "x", "--page-size", "50"])


def _sample():
    return [
        Listing(
            position=1,
            listing_id="1",
            title="Widget",
            price=9.99,
            currency="USD",
            price_raw="US $9.99",
            condition="New",
            condition_code="new",
            watchers=3,
            buy_it_now=True,
            url="https://ebay.com/itm/1",
            seller=Seller(username="acme", feedback_percent=99.9, feedback_score=100),
        )
    ]


def test_render_json_roundtrips():
    out = cli._render(_sample(), "json")
    data = json.loads(out)
    assert data[0]["title"] == "Widget"
    assert data[0]["seller"]["username"] == "acme"


def test_render_csv_has_flat_seller_columns():
    out = cli._render(_sample(), "csv")
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows[0]["seller_username"] == "acme"
    assert rows[0]["price"] == "9.99"
    assert "seller" not in rows[0]  # nested object flattened away


def test_render_table_includes_title_and_price():
    out = cli._render(_sample(), "table")
    assert "Widget" in out
    assert "9.99" in out


def test_run_search_writes_file(tmp_path, monkeypatch):
    class FakeScraper:
        def __init__(self, *a, **k):
            pass

        def search_pages(self, keyword, **kwargs):
            return _sample()

    monkeypatch.setattr(cli, "EbayScraper", FakeScraper)
    out_file = tmp_path / "out.json"
    rc = cli.main(["search", "widget", "-o", str(out_file)])
    assert rc == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data[0]["title"] == "Widget"
