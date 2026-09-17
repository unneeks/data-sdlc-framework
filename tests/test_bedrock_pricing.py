"""Unit tests for harness/bedrock_pricing.py's live AWS Price List API
lookup. The `pricing` boto3 client is always faked here (no moto, matching
this repo's convention) — these tests exercise the generic Price List API
parsing shape and the fail-soft matching rules, not AWS itself.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.bedrock_pricing as bedrock_pricing
import harness.connection_tester as connection_tester
from harness.bedrock_pricing import BedrockModelPricing, get_bedrock_model_pricing


def _price_list_entry(model_attr: str, usagetype: str, price_usd: str, unit: str = "1K tokens") -> str:
    import json

    return json.dumps({
        "product": {"attributes": {"model": model_attr, "usagetype": usagetype}},
        "terms": {
            "OnDemand": {
                "sku.term": {
                    "priceDimensions": {
                        "sku.term.dim": {"pricePerUnit": {"USD": price_usd}, "unit": unit},
                    }
                }
            }
        },
    })


class FakePaginator:
    def __init__(self, pages, error: Exception | None = None, call_counter: dict | None = None):
        self._pages = pages
        self._error = error
        self._call_counter = call_counter

    def paginate(self, **kwargs):
        if self._call_counter is not None:
            self._call_counter["count"] += 1
        if self._error is not None:
            raise self._error
        return iter(self._pages)


class FakePricingClient:
    def __init__(self, pages, error: Exception | None = None, call_counter: dict | None = None):
        self._pages = pages
        self._error = error
        self._call_counter = call_counter

    def get_paginator(self, operation_name):
        return FakePaginator(self._pages, error=self._error, call_counter=self._call_counter)


class FakeSession:
    def __init__(self, client, captured: dict | None = None):
        self._client = client
        self._captured = captured

    def client(self, service_name, region_name=None, **kwargs):
        if self._captured is not None:
            self._captured["service_name"] = service_name
            self._captured["region_name"] = region_name
        return self._client


def _patch_session(monkeypatch, client, captured: dict | None = None, region: str = "us-east-1"):
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings(region=region))
    monkeypatch.setattr(connection_tester, "build_session", lambda settings: FakeSession(client, captured))


def test_get_bedrock_model_pricing_parses_matching_input_and_output_rates(monkeypatch):
    pages = [{
        "PriceList": [
            _price_list_entry("Fake Model X", "Input-Tokens", "0.01"),
            _price_list_entry("Fake Model X", "Output-Tokens", "0.02"),
            _price_list_entry("Some Other Model", "Input-Tokens", "9.99"),  # must not match
        ]
    }]
    call_counter = {"count": 0}
    client = FakePricingClient(pages, call_counter=call_counter)
    _patch_session(monkeypatch, client)

    pricing = get_bedrock_model_pricing("fake-model-a")
    assert pricing == BedrockModelPricing("fake-model-a", input_price_per_1k_usd=0.01, output_price_per_1k_usd=0.02)

    # Second lookup for the same model_id must hit the cache, not the client again.
    get_bedrock_model_pricing("fake-model-a")
    assert call_counter["count"] == 1


def test_get_bedrock_model_pricing_returns_none_when_ambiguous(monkeypatch):
    pages = [{
        "PriceList": [
            _price_list_entry("Fake Model B", "Input-Tokens", "0.01"),
            _price_list_entry("Fake Model B", "Input-Tokens", "0.05"),  # a second, different input rate
            _price_list_entry("Fake Model B", "Output-Tokens", "0.02"),
        ]
    }]
    client = FakePricingClient(pages)
    _patch_session(monkeypatch, client)

    assert get_bedrock_model_pricing("fake-model-b") is None


def test_get_bedrock_model_pricing_returns_none_on_client_error(monkeypatch):
    client = FakePricingClient([], error=RuntimeError("boom"))
    _patch_session(monkeypatch, client)

    assert get_bedrock_model_pricing("fake-model-c") is None


def test_get_bedrock_model_pricing_returns_none_when_unmatched(monkeypatch):
    pages = [{"PriceList": [_price_list_entry("Totally Unrelated", "Input-Tokens", "0.01")]}]
    client = FakePricingClient(pages)
    _patch_session(monkeypatch, client)

    assert get_bedrock_model_pricing("fake-model-d") is None


def test_pricing_client_pinned_to_us_east_1_regardless_of_connection_tester_region(monkeypatch):
    pages = [{
        "PriceList": [
            _price_list_entry("Fake Model E", "Input-Tokens", "0.01"),
            _price_list_entry("Fake Model E", "Output-Tokens", "0.02"),
        ]
    }]
    captured: dict = {}
    client = FakePricingClient(pages)
    _patch_session(monkeypatch, client, captured=captured, region="ap-southeast-2")

    get_bedrock_model_pricing("fake-model-e")
    assert captured["service_name"] == "pricing"
    assert captured["region_name"] == "us-east-1"


def test_get_bedrock_model_pricing_returns_none_for_empty_model_id():
    assert get_bedrock_model_pricing("") is None
