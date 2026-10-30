# Crypto Market Pulse — Product & Engineering Specification

Status: implementation-ready MVP spec, with cloud providers and cross-engine E2E tests explicitly gated. Date: 2026-10-30.

## Goal / Why

Build a public, read-only **market microstructure monitoring** product and streaming system design portfolio that answers:

1. What is happening in BTCUSDT/ETHUSDT right now? Show price, 1m OHLCV, VWAP, trade count, taker-buy share and anomalies/volume spikes (next iteration).
2. How current and trustworthy is the view? Show source/ingestion timestamp, lag, duplicate count, late-event count, consumer lag and data quality state.
3. How do alternative execution engines handle event-time windows, repeated events, backpressure, checkpoint/replay and query serving?

Explicitly out of scope: authenticated trading, order submission, leverage, forecasts, investment advice, private account data and automated resource expenditure.

## Sources

- Bybit V5 public WS linear endpoint `wss://stream.bybit.com/v5/public/linear`.
- Subscribe `publicTrade.BTCUSDT` and `publicTrade.ETHUSDT`.
- Every WS frame can contain **multiple trades**. Map each `data[]` entry into an immutable canonical record.
- Handle `ping/pong`, reconnect, jitter/backoff, downstream timeout, schema failure quarantine and source gaps as distinct concerns. Public streams do not guarantee backfill of trades missed before Kafka.
- Include synthetic deterministic fixture; no API keys needed.

### Canonical envelope

```json
{"schema_version":1,"event_id":"bybit:linear:BTCUSDT:t01","source":"bybit","category":"linear","symbol":"BTCUSDT","trade_id":"t01","event_time_ms":1793354405000,"received_at_ms":1793354422000,"side":"Buy","price":"70000.0","quantity":"0.10"}
```

Prices are examples, not actual market quotations. Reject nonfinite numbers, zero/negative prices or quantities, malformed IDs, wrong side or impossible times. `price`/`quantity` must remain decimal-precision-safe. Use stable exchange trade ID for dedup, not WS envelope ID. Version contract and validate at producer and consumer.

## Architecture profiles

| Profile | Local | Managed cloud | Semantic caveats |
| --- | --- | --- | --- |
| ClickHouse | existing Redpanda/Kafka → Python consumer → ClickHouse OSS → Streamlit | Confluent Cloud Basic on GCP → ClickPipes → ClickHouse Cloud | At-least-once ingestion; query-level dedup; serving SQL views; ClickPipes deployment *draft* |
| Databricks | Spark `readStream` JSON file feed + checkpoint, SQL batch mart | Delta Bronze → Lakeflow SQL streaming table + MVs → Databricks SQL AI/BI | DFE may restrict continuous mode; Bronze producer separate; SQL MVs refresh instead of push |
| GCP native | Beam DirectRunner TestStream + Pub/Sub Emulator | Pub/Sub → native BigQuery subscription (MVP); optional Pub/Sub → Dataflow/Beam → BigQuery (advanced) | Emulator cannot deliver to BigQuery; BQ subscription has no custom window logic |

Prefer Confluent Cloud to MSK/self-managed Kafka for simplest managed Kafka, but do **not** create paid services without explicit user approval. ClickHouse Cloud production ClickPipes path must be validated against target plan/network/auth. Keep Terraform scoped, state protected, least-privilege identities and budget alerts.

## Deliverables

1. `config/settings.yml`, per-profile YAML, typed `src/market_pulse/settings.py`, minimal shared `utils.py`; no secrets/default production credentials.
2. `domain.py` strictly validates publicTrade and canonical envelopes; `bybit_ws.py` retries safely, `publish.py` sends to stdout/Kafka/PubSub, `scripts/produce.py` does bounded fixture replay.
3. SQL-first marts separately for ClickHouse, Databricks and BigQuery, including 1m OHLCV/VWAP/latest. Do not treat dialects as identical: compare outputs on same fixture.
4. Working local ClickHouse setup and consumer with commit-after-insert; no destructive DDL. Manual opt-in Docker Compose only as last resort.
5. Spark Structured Streaming local checkpoint/replay diagnostic; Lakeflow source SQL; optional Databricks bundle with dashboard JSON. No guarantee of uninterrupted DFE runtime.
6. GCP Beam TestStream event-time window test, Pub/Sub emulator smoke and Terraform (manual only). Dataflow streaming runner is explicitly **phase 2**, not secretly claimed complete.
7. Dashboard as code: Streamlit for ClickHouse/BigQuery; Databricks AI/BI JSON with SQL source. Compare current price, OHLCV, VWAP, volume and lag; later add anomaly alerts/lag panels.
8. GitHub Actions fast unit/contract/Beam tests without credentials. Docker integration and cloud smoke are manual/optional. Conventional Commits, PR-first delivery.
9. Read-only host inventory with explicit precedence **OS installations → existing authorized containers → new isolated containers → new installation**, searching PATH, `~/.apps/`, `~/.app/`, Docker/Colima. Never restart/stop/remove unknown services or use shared DB without permission.
10. Document experimental limitations and security safeguards. No actual trading credentials.

## Streaming test matrix

| Scenario | What to verify | Expected evidence |
| --- | --- | --- |
| Multi-trade WS payload | Every `data[]` element mapped once | Parser unit test, stable event IDs |
| Duplicates/replay | Same `event_id` emitted twice | Dedup view and exact expected OHLCV |
| Out-of-order arrival | Late delivery inside configured bounds | OHLC correct by event time, not arrival time |
| Late beyond watermark | Explicit policy: discard, quarantine or correction | Error/late count and documented behavior |
| Consumer crash after sink write | Restart with same Kafka group | No double count in query-level mart |
| Consumer slower than producer | Producer lag/backpressure | Lag and failure metrics, recovery evidence |
| Broken JSON / bad price | Reject and record poison message | No offset commit until managed DLQ/quarantine |
| WebSocket disconnect | Reconnect after bounded retry | Note missing producer-side historical data |
| Schema evolution | New optional field vs breaking change | Versioned contract or fail safely |
| Cross-engine equality | Same fixture applied everywhere | OHLCV, VWAP, trade_count and ordering match |

## Acceptance criteria

**P0 offline:** all parser/settings/tests pass; fixture and result are deterministic; no credentials/cloud required; no data-destructive actions; all code and spec packed in one ZIP. Read-only inventory runs without changes.

**P1 local ClickHouse:** verified broker/database endpoints, create *project-owned* topic and schema, publish fixture, consume, query 1m and latest marts, show Streamlit dashboard; repeated replay does not alter financial aggregates. Capture console output or test log.

**P2 Spark/Beam:** run local Spark streaming with checkpoint and Beam DirectRunner TestStream, assert exact 1m results; demonstrate restart/late policy explicitly. Pub/Sub emulator optional; no fake BigQuery delivery.

**P3 cloud opt-in:** cloud-specific auth/networking, costs, IAM, target runtimes and CI smoke checked manually. Never claim P3 from unit tests. Provide measured ingest-to-visible latency, throughput, duplicate ratio, consumer lag and estimated cost only after measurements.

**P4 product:** add anomaly detection (volume spike vs historical median, price change over window), alerts with cooldown and explainable thresholds, health panel and user-selected watchlist. Avoid signal-to-buy/sell language. Optional streaming order book reconstruction with sequence/gap tests; not mixed into P0.

## Work units / PR plan

- PR1 shared domain, producer, replay fixtures, settings, CI and read-only inventory.
- PR2 local Redpanda/ClickHouse SQL and Streamlit E2E.
- PR3 Spark checkpoint streaming, Databricks Lakeflow SQL, dashboard-as-code.
- PR4 Beam DirectRunner, Pub/Sub emulator, BigQuery SQL, GCP Terraform review.
- PR5 opt-in Confluent/ClickPipes and Dataflow cloud smoke (manual cost approval).
- PR6 latency/DQ/observability, chaos/lag tests, alerts and comparison report.

## Operational and repository constraints

The `beloz978/weather_dfe`, `dataengy/weather_dfe` and `hnkovr` org/ownership may differ; inspect git remotes, authenticated `gh auth status`, permissions before any mutation. **No archive, fork, push, deploy, PR or account switch without checking owner and explicit approval.** Keep existing Weather DFE baseline in `baseline/weather_dfe_handoff.zip` as read-only reference. If an unrelated repo is checked out, create an isolated feature branch only after permission. Prefer not to alter default branch. Never store `.env`, API tokens, private messages, account statements, creds or real account trade data in public repo.

## Key authoritative references

- https://bybit-exchange.github.io/docs/v5/websocket/public/trade
- https://bybit-exchange.github.io/docs/v5/ws/connect
- https://docs.databricks.com/gcp/en/ldp/developer/ldp-sql-ref-create-streaming-table
- https://docs.databricks.com/gcp/en/dev-tools/bundles/resources
- https://docs.cloud.google.com/pubsub/docs/bigquery
- https://docs.cloud.google.com/pubsub/docs/emulator
- https://clickhouse.com/docs/integrations/clickpipes
- https://beam.apache.org/documentation/runners/direct/
