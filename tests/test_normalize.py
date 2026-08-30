"""Offline tests for price/currency parsing and response normalization."""

from __future__ import annotations

import pytest

from ebay_scraper.scraper import (
    normalize_listing,
    normalize_response,
    normalize_seller,
    parse_price,
)


@pytest.mark.parametrize(
    ("raw", "expected_amount", "expected_currency"),
    [
        ("US $29.99", 29.99, "USD"),
        ("$1,234.56", 1234.56, "USD"),
        ("£9.99", 9.99, "GBP"),
        ("EUR 15,00", 15.00, "EUR"),  # European decimal comma
        ("1.234,56 EUR", 1234.56, "EUR"),  # European thousands + decimal
        ("KRW105,964.42", 105964.42, "KRW"),
        ("AU $12.00", 12.00, "AUD"),
        ("¥3,500", 3500.0, "JPY"),
    ],
)
def test_parse_price_from_raw(raw, expected_amount, expected_currency):
    amount, currency = parse_price(None, None, raw)
    assert amount == pytest.approx(expected_amount)
    assert currency == expected_currency


def test_parse_price_prefers_parsed_fields():
    amount, currency = parse_price(19.5, "USD", "US $19.50")
    assert amount == pytest.approx(19.5)
    assert currency == "USD"


def test_parse_price_fills_only_missing_pieces():
    # amount present but currency null -> pull currency from raw
    amount, currency = parse_price(19.5, None, "US $19.50")
    assert amount == pytest.approx(19.5)
    assert currency == "USD"


def test_parse_price_handles_garbage():
    assert parse_price(None, None, None) == (None, None)
    assert parse_price(None, None, "Best offer") == (None, None)


def test_normalize_seller_flattens_nested_object():
    seller = normalize_seller({"username": "acme", "feedbackPercent": 99.7, "feedbackScore": 14000})
    assert seller.username == "acme"
    assert seller.feedback_percent == pytest.approx(99.7)
    assert seller.feedback_score == 14000


def test_normalize_seller_handles_missing():
    assert normalize_seller(None).username is None
    assert normalize_seller("bob").username == "bob"


def test_normalize_listing_uses_raw_price_when_price_null():
    raw = {
        "position": 1,
        "listingId": "267543612733",
        "title": "NuPhy X BH65 Keyboard",
        "url": "https://www.ebay.com/itm/267543612733",
        "condition": "Pre-Owned",
        "conditionCode": "used",
        "price": None,
        "currency": None,
        "priceRaw": "US $29.99",
        "watchers": 36,
        "buyItNow": True,
        "seller": {"username": "anson", "feedbackPercent": 99.7, "feedbackScore": 14000},
    }
    listing = normalize_listing(raw)
    assert listing.listing_id == "267543612733"
    assert listing.price == pytest.approx(29.99)
    assert listing.currency == "USD"
    assert listing.condition_code == "used"
    assert listing.watchers == 36
    assert listing.buy_it_now is True
    assert listing.seller.username == "anson"


def test_normalize_response_shape():
    raw = {
        "keyword": "kb",
        "marketplace": "ebay.com",
        "page": 1,
        "pageSize": 60,
        "totalResults": 15000,
        "searchUrl": "https://www.ebay.com/sch/i.html?_nkw=kb",
        "exactMatches": True,
        "resultsCollected": 2,
        "results": [
            {"title": "A", "priceRaw": "$1.00"},
            {"title": "B", "priceRaw": "$2.00"},
        ],
    }
    result = normalize_response(raw)
    assert result.keyword == "kb"
    assert result.total_results == 15000
    assert len(result) == 2
    assert [listing.title for listing in result] == ["A", "B"]
    assert result.to_dict()["listings"][0]["price"] == pytest.approx(1.0)


def test_normalize_response_handles_empty():
    result = normalize_response({})
    assert len(result) == 0
    assert result.to_dict()["listings"] == []
