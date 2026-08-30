"""Offline tests for EbayScraper — the SDK client is fully mocked (no API credit)."""

from __future__ import annotations

import pytest
import scrapeunblocker as su

from ebay_scraper import EbayScraper


class FakeClient:
    """Records calls and replays a queued sequence of results/exceptions."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def ebay_search(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _page(titles, **extra):
    return {
        "keyword": "kb",
        "marketplace": "ebay.com",
        "results": [{"title": t, "priceRaw": "$1.00"} for t in titles],
        **extra,
    }


def test_search_normalizes_and_strips_none_params():
    client = FakeClient([_page(["A", "B"])])
    scraper = EbayScraper(client=client)
    result = scraper.search("kb", marketplace="ebay.de", condition=None)
    assert [listing.title for listing in result] == ["A", "B"]
    # keyword always sent; None-valued optionals dropped so SDK defaults apply
    sent = client.calls[0]
    assert sent["keyword"] == "kb"
    assert sent["marketplace"] == "ebay.de"
    assert "condition" not in sent
    assert "free_shipping" not in sent  # False is dropped too


def test_search_rejects_empty_keyword():
    scraper = EbayScraper(client=FakeClient([]))
    with pytest.raises(ValueError):
        scraper.search("   ")


def test_retry_on_transient_error_then_succeeds():
    # Note: SDK API errors require a status_code kwarg; a bare message raises TypeError.
    responses = [
        su.RateLimitError("slow down", status_code=429),
        su.ScrapeTimeoutError("timed out"),  # base ctor: no status_code kwarg
        _page(["OK"]),
    ]
    client = FakeClient(responses)
    slept = []
    scraper = EbayScraper(client=client, retries=2, backoff=0.1, sleep=slept.append)
    result = scraper.search("kb")
    assert [listing.title for listing in result] == ["OK"]
    assert len(client.calls) == 3
    assert len(slept) == 2  # backed off twice


def test_retry_gives_up_after_limit():
    responses = [
        su.UpstreamOutageError("upstream down", status_code=502),
        su.UpstreamOutageError("upstream down", status_code=502),
    ]
    client = FakeClient(responses)
    scraper = EbayScraper(client=client, retries=1, backoff=0.01, sleep=lambda _s: None)
    with pytest.raises(su.UpstreamOutageError):
        scraper.search("kb")
    assert len(client.calls) == 2  # initial + 1 retry


def test_non_transient_error_is_not_retried():
    client = FakeClient([su.InvalidRequestError("bad param", status_code=400)])
    scraper = EbayScraper(client=client, retries=3, sleep=lambda _s: None)
    with pytest.raises(su.InvalidRequestError):
        scraper.search("kb")
    assert len(client.calls) == 1


def test_search_pages_collects_and_stops_on_empty():
    client = FakeClient([_page(["A", "B"]), _page(["C"]), _page([])])
    scraper = EbayScraper(client=client)
    listings = scraper.search_pages("kb", max_pages=5)
    assert [listing.title for listing in listings] == ["A", "B", "C"]
    assert len(client.calls) == 3  # stopped once an empty page came back
