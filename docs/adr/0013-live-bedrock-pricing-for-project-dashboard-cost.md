# ADR 0013: Live AWS Price List Pricing for Project Dashboard Token Cost

## Status

Accepted

## Date

2026-09-17

## Context

The Project Dashboard (ADR 0010) tracks per-lane token usage via `harness/agentcore_invocation_metrics.py::InvocationMetricsTracker`/`TokenUsage`, feeding the dashboard's live cost tiles. Real per-turn token *counts* are already parsed correctly from AgentCore's own response (`agents/runner.py::parse_harness_stream`'s `usage` block, recorded through `harness/live_session.py::_record_usage`) — but the dollar figure was `real_tokens × PRICE_PER_1K_INPUT_USD/PRICE_PER_1K_OUTPUT_USD`, two module constants ($0.003/$0.015) the file's own docstring already called "a placeholder estimate... not a billing source of truth," applied uniformly regardless of which model actually ran. The user asked whether token cost was implemented, and — once shown that the counts were real but the price was fake — asked for the price to come from a real AWS/AgentCore API instead.

**AWS Cost Explorer was the first candidate and was rejected.** It reports actual billed dollars, but only at account/service granularity (e.g. "Amazon Bedrock this month"), with hours of reporting lag, and has no concept of "this dashboard session" or "this lane" to scope to — the wrong shape for a live, per-session tile no matter how real the underlying number is.

**GitHub Copilot fallback lanes and DEMO mode have no real invocation to price at all.** Copilot's token count is already a char-count heuristic (`harness/live_session.py::_run_github_copilot`, explicitly commented "GitHub Copilot CLI has no usage API"); DEMO's tokens are a fixed synthetic constant per work-product transition. Multiplying either by any price — real or fake — produces a number that looks precise but reflects nothing real.

## Decision

**Fetch real, current $/1K-token pricing per Bedrock model from the AWS Price List API**, and apply it to the token counts already being parsed correctly, instead of a hardcoded constant. New module `harness/bedrock_pricing.py::get_bedrock_model_pricing(model_id)` builds a `pricing` boto3 client — pinned to `region_name="us-east-1"` always, since the Price List API is only published there and in `ap-south-1` regardless of where Bedrock/AgentCore itself runs, deliberately bypassing `harness/connection_tester.py::build_boto3_client()`'s region-override logic for this one call while still honoring its configured credentials/profile via `build_session(load_settings())`. Pricing is cached in memory per `model_id` per process (pricing rarely changes, no external cache needed).

The AWS Price List API's exact filterable/returned attribute schema for `ServiceCode="AmazonBedrock"` is not something this module hardcodes with confidence — Bedrock's Price List entries generally use human-readable model names rather than the inference-profile id strings this app configures (`bedrock_model_id`, e.g. `us.anthropic.claude-opus-4-6-v1`). `bedrock_pricing.py` matches by scanning each returned product's `attributes` for fragments derived from the model id (stripping the region/vendor prefix and version suffix) rather than a single exact filter, and parses the rate via the AWS Price List API's generic, service-agnostic shape (`terms.OnDemand.<sku>.priceDimensions.<rateCode>.pricePerUnit.USD`, normalized against the dimension's `unit`). This is a best-effort matcher pending a real, credentialed verification pass against live AWS data — this session's sandbox had no AWS credentials to run that pass, so the matching logic is exercised only against hand-built fake `pricing` client responses in `tests/test_bedrock_pricing.py`. **Deliberately conservative**: zero matches, more than one distinct candidate rate for the same direction (input/output), or any client error all return `None` — never a guess, never a silent fallback to the old constants (which are deleted entirely from `agentcore_invocation_metrics.py`, along with `TokenUsage.estimated_cost_usd`, so nothing can keep using them).

**"N/A beats a wrong number," extended to a third state.** ADR 0003 established that REAL mode fails soft to a structured unavailable state rather than crashing; ADR 0012 (unrelated) later chose the same for `list_live_agents()`'s harness listing over falling back to stale cached ARNs. This ADR applies the identical philosophy to cost specifically: `InvocationMetricsTracker.start_lane(lane_key, source, model_id="")` only attempts a pricing fetch when `source == "AGENTCORE"` and a `model_id` is supplied (threaded through from `harness/project_dashboard.py::ProjectLane._run_live`'s already-resolved `agent_config["bedrock_model_id"]`); `DEMO` and `GITHUB_COPILOT` lanes never attempt one. `lane_snapshot()`/`project_snapshot()` now report `cost_available: bool` alongside `token_cost_usd: Optional[float]`, which is `None` — not `0` — whenever cost isn't available: a lane that ran real turns never actually costs literally $0.00, so `0` would misrepresent it; `null` forces any consumer that forgets to check `cost_available` to fail loudly (`.toFixed` throws on `null`) rather than silently render a confidently-wrong `"$0.00"`. `project_snapshot()`'s aggregate `cost_available` is `True` only if every lane with any recorded usage is itself available — a mixed AgentCore + DEMO run must not quietly omit the DEMO lane's unknown spend and present a clean total.

The frontend (`apps/web/src/components/ProjectDashboard.tsx`) renders a new `formatCost(cost, available)` helper at its three existing cost display sites (header stat tile, per-lane footer, "Estimated Cost" insights tile), showing `"N/A"` wherever `cost_available` is `false` instead of the previous unconditional `$X.XX`.

## Consequences

### Positive
- AgentCore-backed lanes now show a cost that reflects the actual model that ran and AWS's actual current list price, self-correcting whenever AWS reprices without a code deploy.
- No AgentCore/AWS call site regressed — pricing lookups are additive and fail soft; a lookup failure degrades to "unavailable," never to a wrong number or a crash.
- Deleting the hardcoded constants removes a way for any future code to silently reuse a stale, unlabeled estimate.

### Negative / non-goals
- Still a list-price estimate, not the actual bill: provisioned throughput, enterprise discount agreements, and any Bedrock-specific caching discounts are not reflected. AWS Cost Explorer remains the source of record for real spend.
- The exact Price List attribute-matching logic in `bedrock_pricing.py` is best-effort, verified only against hand-built fake responses — this sandbox had no AWS credentials to empirically confirm the real schema. Whoever has AWS access should run the one-off `get_products(ServiceCode="AmazonBedrock", MaxResults=5)` probe described in that module's docstring and adjust the matcher if real attribute names differ from what's assumed.
- One extra live AWS call per lane-start in REAL mode for AgentCore lanes (mitigated by per-process caching — one fetch per distinct `model_id` for the life of the process).
- GitHub Copilot fallback lanes and DEMO lanes lose their previous (already-fake) dollar figure entirely, now always showing "N/A" for cost — a deliberate trade of "always shows a number" for "never shows a wrong one."

## Alternatives Considered

- **AWS Cost Explorer** — rejected: account/service-level granularity with hours of lag, cannot be scoped to a single dashboard lane or session.
- **Per-model hardcoded price table** (more granular than the old blended constant, but still static) — rejected: still goes silently stale the instant AWS changes list pricing, with no signal to anyone that it happened.
- **Extending Copilot's char-count heuristic into a dollar estimate too** — rejected per the user's explicit choice: there's no real invocation behind that number, so no cost figure should be shown for it, ever.
