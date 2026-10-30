# Workbook 2 — Redpanda/Kafka → ClickHouse local E2E

**Goal:** prove a real Kafka transport, at-least-once sink semantics, SQL dedup and dashboard. Requires an existing *authorized* Kafka broker and ClickHouse instance, or a newly approved isolated project container.

### Preparation / safety

Run Workbook 0 first. In an existing shared broker **do not** reuse or reset someone else's topic/consumer group. For a dedicated project compose environment only:

```bash
# Last resort if inventory found no compatible installation/container:
docker compose -f infra/clickhouse/compose.yml up -d
export CLICKHOUSE_PASSWORD=local_only_change_me
docker exec cmp-redpanda rpk topic create market.trades.v1 --brokers localhost:9092
```

Adapt `CMP_KAFKA_BOOTSTRAP`, `CMP_CLICKHOUSE_URL`, `CMP_CLICKHOUSE_DATABASE`, and `CMP_KAFKA_GROUP` to chosen own resources. Avoid port collisions; use existing binaries before creating duplicates.

### Exercise A — baseline ingest

```bash
python -m pip install -r requirements-clickhouse.txt
python scripts/clickhouse_setup.py
python scripts/produce.py --sink kafka --profile clickhouse --fixture tests/fixtures/trades.jsonl
python scripts/clickhouse_consumer.py --max-messages 8
```

Read-only ClickHouse SQL (through your chosen CLI/UI):

```sql
SELECT count() AS raw_events, uniqExact(event_id) AS unique_events FROM market_pulse.trades_raw;
SELECT symbol, window_start, trade_count, open_price, high_price, low_price,
       close_price, volume, vwap
FROM market_pulse.trades_1m ORDER BY symbol, window_start;
```

Expect 8 physical events and 7 unique IDs **in an initially empty dedicated database**. If reusing existing data, do not expect these absolute totals: isolate a fresh project namespace or calculate a before/after delta. OHLCV must match Workbook 1 for the test window.

### Exercise B — duplicate replay / idempotent user-facing mart

Republish the same fixture, then consume the newly published 8 Kafka messages using the same consumer group. Raw count increases; `uniqExact(event_id)` and the `trades_1m` aggregates remain unchanged. This shows **query-level dedup**, not physical exactly-once. Be careful: `--max-messages 8` on a consumer with no new traffic waits forever until interrupted.

### Exercise C — crash/restart reasoning

1. Locate the commit boundary inside `src/market_pulse/clickhouse_sink.py`.
2. Explain what happens if the ClickHouse insert succeeds but process exits before Kafka offset commit.
3. In an isolated copy/environment, inject a controlled failure at that boundary and restart consumer. Inspect raw vs dedup counts. Do not perform this fault injection against shared services.
4. Check lag using your installed Kafka CLI (e.g. `rpk group describe <project-group>`). Record messages produced, consumed, and offsets at start/end.

### Exercise D — dashboard

```bash
python -m pip install -r requirements-dashboard.txt
CMP_PROFILE=clickhouse streamlit run dashboards/app.py
```

Confirm latest price, OHLCV and volume appear. Dashboard TTL is 5 seconds and UI refresh may require manual interaction. Do not claim a per-trade push interface.

**Pass:** recorded before/after counts, stable mart under replay, visible dashboard, Kafka offsets and non-destructive restart note. **Not yet proven:** ClickPipes cloud behavior, performance under sustained load.
