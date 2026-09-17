"""Live AWS Price List API lookups for Amazon Bedrock on-demand token pricing.

Fetches the real, current $/1K-token input+output rate for a given Bedrock
model id from the `pricing` boto3 client (AWS Price List API), so
harness/agentcore_invocation_metrics.py can multiply real per-turn token
counts (already parsed correctly from AgentCore's own response — see that
module's docstring) by a real, current rate instead of a hardcoded
constant. AWS Cost Explorer was considered instead and rejected: it reports
actual billed dollars, but only at account/service granularity with hours
of lag, and can never be scoped to a single dashboard lane.

The AWS Price List API is published in only us-east-1/ap-south-1
regardless of where the priced service itself runs, so the `pricing`
client here always pins region_name="us-east-1" — deliberately bypassing
harness/connection_tester.py's build_boto3_client() region-override logic
for this one call, since honoring a saved Connection Tester region (e.g.
ap-southeast-2) would point this client at a region the Price List API
doesn't support. Credentials/profile are still honored via
build_session(load_settings()).

The AWS Price List API's exact filterable/returned attributes for
ServiceCode="AmazonBedrock" are not something this module hardcodes with
confidence: Bedrock's Price List entries generally use human-readable
model names (e.g. "Claude 3.5 Sonnet") rather than the inference-profile
id strings this app uses (e.g. "us.anthropic.claude-opus-4-6-v1"), so
matching is done by scanning each returned product's attributes for a
plausible model-name fragment rather than a single exact TERM_MATCH
filter. This is a best-effort matcher pending a real, credentialed
verification pass (see docs/adr/0013 for the empirical-discovery step) —
it is deliberately conservative: any ambiguity (zero or multiple distinct
matching rates for the same direction) returns None rather than guessing,
so a caller that can't get a confident number shows "cost unavailable,"
never a wrong one.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional

_PRICING_REGION = "us-east-1"
_SERVICE_CODE = "AmazonBedrock"

_cache_lock = Lock()
_cache: Dict[str, Optional["BedrockModelPricing"]] = {}


@dataclass
class BedrockModelPricing:
    model_id: str
    input_price_per_1k_usd: float
    output_price_per_1k_usd: float


def get_bedrock_model_pricing(model_id: str) -> Optional[BedrockModelPricing]:
    """Cached (in-memory, per-process — pricing rarely changes) lookup of
    real on-demand Bedrock pricing for `model_id`. None means pricing
    could not be confidently matched (API unreachable, no matching
    product, or an ambiguous match) — callers must treat that as "cost
    unavailable" and never fall back to a guessed/hardcoded rate."""
    with _cache_lock:
        if model_id in _cache:
            return _cache[model_id]

    result = _fetch_bedrock_model_pricing(model_id)

    with _cache_lock:
        _cache[model_id] = result
    return result


def _fetch_bedrock_model_pricing(model_id: str) -> Optional[BedrockModelPricing]:
    if not model_id:
        return None

    try:
        from harness.connection_tester import build_session, load_settings

        client = build_session(load_settings()).client("pricing", region_name=_PRICING_REGION)
    except Exception:  # noqa: BLE001 - report, never crash the caller
        return None

    try:
        input_rates: List[float] = []
        output_rates: List[float] = []
        paginator = client.get_paginator("get_products")
        for page in paginator.paginate(ServiceCode=_SERVICE_CODE):
            for price_list_entry in page.get("PriceList", []):
                product = json.loads(price_list_entry) if isinstance(price_list_entry, str) else price_list_entry
                attributes = product.get("product", {}).get("attributes", {}) or {}
                if not _product_matches_model(attributes, model_id):
                    continue

                direction = _rate_direction(attributes)
                if direction is None:
                    continue

                rate = _extract_on_demand_rate_per_1k(product)
                if rate is None:
                    continue

                if direction == "input":
                    input_rates.append(rate)
                elif direction == "output":
                    output_rates.append(rate)
    except Exception:  # noqa: BLE001 - report, never crash the caller
        return None

    # Any ambiguity (nothing found, or more than one distinct candidate
    # rate for the same direction) is treated as "not confidently priced" -
    # never pick arbitrarily between them.
    if len(set(input_rates)) != 1 or len(set(output_rates)) != 1:
        return None

    return BedrockModelPricing(
        model_id=model_id,
        input_price_per_1k_usd=input_rates[0],
        output_price_per_1k_usd=output_rates[0],
    )


def _model_search_fragments(model_id: str) -> List[str]:
    """Reduce an inference-profile-style model id (e.g.
    "us.anthropic.claude-opus-4-6-v1") to the fragments most likely to
    appear in a Price List product's human-readable model name (e.g.
    "Claude", "Opus"), stripping the region prefix, vendor, and trailing
    version suffix."""
    tail = model_id.split(".")[-1] if "." in model_id else model_id
    tail = re.sub(r"-v\d+$", "", tail)
    parts = [p for p in tail.split("-") if p and not p.isdigit()]
    return [p.lower() for p in parts if len(p) > 2]


def _product_matches_model(attributes: Dict[str, Any], model_id: str) -> bool:
    fragments = _model_search_fragments(model_id)
    if not fragments:
        return False
    haystack = " ".join(str(v) for v in attributes.values()).lower()
    return all(fragment in haystack for fragment in fragments)


def _rate_direction(attributes: Dict[str, Any]) -> Optional[str]:
    haystack = " ".join(str(v) for v in attributes.values()).lower()
    is_input = "input" in haystack
    is_output = "output" in haystack
    if is_input and not is_output:
        return "input"
    if is_output and not is_input:
        return "output"
    return None


def _rate_per_1k_from_unit(price_per_unit_usd: float, unit: str) -> Optional[float]:
    """Normalize a Price List rate to $/1K tokens given its `unit` string.
    Bedrock's on-demand token pricing is published per 1K tokens, but this
    stays defensive rather than assuming: an unrecognized unit returns
    None (not confidently priceable) instead of silently mis-scaling."""
    normalized = unit.lower().replace(" ", "")
    if "1ktoken" in normalized or "1000token" in normalized:
        return price_per_unit_usd
    if normalized in ("tokens", "token"):
        return price_per_unit_usd * 1000
    return None


def _extract_on_demand_rate_per_1k(product: Dict[str, Any]) -> Optional[float]:
    """Generic AWS Price List API shape (true for every ServiceCode, not
    Bedrock-specific): terms.OnDemand.<sku>.priceDimensions.<rateCode> each
    carry a pricePerUnit.USD string and a `unit` description."""
    on_demand = product.get("terms", {}).get("OnDemand", {})
    rates: List[float] = []
    for sku_term in on_demand.values():
        for dimension in sku_term.get("priceDimensions", {}).values():
            price_str = dimension.get("pricePerUnit", {}).get("USD")
            unit = dimension.get("unit", "")
            if not price_str or not unit:
                continue
            try:
                price = float(price_str)
            except ValueError:
                continue
            rate = _rate_per_1k_from_unit(price, unit)
            if rate is not None:
                rates.append(rate)

    if len(set(rates)) != 1:
        return None
    return rates[0]
