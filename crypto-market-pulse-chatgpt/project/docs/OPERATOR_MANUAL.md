# Crypto Market Pulse — operational manual

**Purpose:** Developer/operator reference for reliable local streaming, profiling and cloud opt-in. Not an automated trading system. This manual supplements the step-by-step `RUN_AND_DEBUG_GUIDE.md` and practical `workbooks/`.

## A. Data path and contracts

`Bybit publicTrade.{symbol}` (public WebSocket) → `normalize_trade` → stdout/Kafka/PubSub producer → stream/sink → query-level dedup by `event_id` → 1-minute OHLCV/VWAP and latest → Streamlit or Databricks AI/BI.

Canonical envelope: `schema_version`, `event_id`, `source`, `category`, `symbol`, `trade_id`, `event_time_ms`, `received_at_ms`, `side`, decimal *string* `price`, decimal *string* `quantity`. Exchange `event_time_ms` is event time; `received_at_ms` is receive time. An `event_id` uniquely identifies a trade, not a message or minute. No private API credentials are required.

### Aggregate semantics

- `window_start_ms = floor(event_time_ms / 60_000) * 60_000`; tumbling minute, UTC.
- Open/close order by `(event_time_ms, event_id)`, **not** arrival order. High/low of price.
- Volume = sum(quantity); notional = sum(price × quantity); VWAP = notional / volume; count of taker buy-side trades.
- Duplicate event IDs: keep record with smallest `received_at_ms` (tie-break by documented deterministic ordering); raw may contain duplicates by design.
- Price/quantity precision: JSON strings preserved until DECIMAL/BIGNUMERIC conversion; avoid floats for business logic.
- Current SQL views can revise past minute results when a late trade arrives. They are not immutable closed-window outputs. Near-real-time visibility is governed by consumer latency, view query time and dashboard refresh.

## B. Service choice and safety policy

Precedence **existing OS application in PATH, `~/.apps/`, `~/.app/` → existing authorized Docker/Colima container → new isolated container → install**. List versions and ports, verify compatibility and ownership, choose project-specific topic (`market.trades.v1`), consumer group and schema. Read-only `scripts/discover_local_runtime.py` never starts a service. Never manage shared services without permission, never run `docker compose down -v` or broad `docker system prune`, never paste tokens into commits.

If using `compose.yml`, containers and ports are project-scoped examples, **not** an assertion that those ports are free. Any needed override must avoid clobbering existing containers or port mappings.

## C. Lifecycle: start, monitor, pause, resume

1. Inventory and verify chosen endpoints with a **read-only** query/topic listing.
2. Initialize project-owned table/views (`scripts/clickhouse_setup.py`), only after checking `CMP_CLICKHOUSE_URL`.
3. Start a **bounded** fixture producer; validate Kafka topic count and sample key/value.
4. Start a bounded consumer; check offset commit after sink write.
5. Query raw count, dedup count, `trades_1m`, `trades_latest`; compare to reference output from `scripts/preview_marts.py`.
6. Start dashboard; note it queries every refresh, with 5-second cache, not WebSocket push.
7. For continuous live mode, run `scripts/produce.py --sink kafka` only after controlled bounded tests; coordinate consumer operation and monitoring. Stop with SIGINT and capture logs; restarting may cause at-least-once re-delivery.

### Recommended observability fields

| Layer | Metrics | How to interpret |
| --- | --- | --- |
| WebSocket | connected, reconnects, messages/s, events/s, parse rejects, last-event time | Gaps before broker are not fixed by Kafka replay |
| Kafka | publish failures, pending requests, partition offsets, consumer lag, group rebalances | Consumer lag is broker-side offset backlog, not end-to-end delay |
| ClickHouse | raw inserts, parse exceptions, query latency, unique IDs, duplicate ratio | `raw_count - dedup_count` indicates repeated ingestion, not necessarily faulty user data |
| Spark | batchId, input rows/s, processed rows/s, state rows, watermark, checkpoint | Query progress and sink correctness are separate checks |
| Beam | event-time, watermark, allowed lateness, window pane counts | Simulated TestStream behavior differs from live Dataflow scheduling |
| Dashboard | refresh time, latest visible event time | View staleness = display timestamp − latest event timestamp |

**Latency definitions:** `source_to_ingest_ms = received_at_ms - event_time_ms`; can be negative because of clock skew and exchange clocks. `broker_to_sink_ms` and `sink_to_visible_ms` need separately instrumented timestamps; don't infer them from the fixture.

## D. Failure and recovery runbook

**Producer disconnect:** record disconnect UTC and last event ID/time; retry with bounded backoff. Bybit live public WS does not guarantee historical replay of all missed trades. If continuity matters, add a backfill source and explicit reconciliation, and distinguish this from consumer recovery.

**Consumer crash after ClickHouse insert but before Kafka commit:** replay may increase raw row count. Check `trades_dedup` and aggregate invariants. Do **not** promise physical exactly-once. Avoid offset resets on shared consumer groups.

**Malformed message:** the local consumer currently raises rather than committing the offset; it has no persistent dead-letter queue. Diagnose the poison event using a project-owned topic, then implement quarantine/DLQ as a tracked improvement. Do not skip silently.

**Late/out-of-order:** SQL query-level marts update when late rows land. Beam and Spark stateful dedup depend on watermark/retention; beyond threshold, messages may not be reflected. Document actual behavior under the engine used.

**Backpressure:** first measure producer throughput vs sink throughput and Kafka consumer lag. Artificially throttle a project-owned consumer, not shared infrastructure. Stop under bounded resource pressure and verify catch-up within retention.

**Schema change:** treat new optional fields as forward-compatible only after schema test; incompatible format should fail safely, increment reject metric and leave an inspection trail.

## E. Local-versus-cloud truth table

| Feature | Offline | ClickHouse local | Spark local | GCP local | Cloud |
| --- | --- | --- | --- | --- | --- |
| Contract/replay | Implemented/tests | Same fixtures | Same fixtures | Same fixtures | Must validate |
| Raw transport | None | Kafka/Redpanda | JSON file | Emulator Pub/Sub | Managed ingest |
| Streaming runtime | None | Consumer + CH SQL views | Spark Structured Streaming | Beam DirectRunner/TestStream | Lakeflow, Dataflow, ClickPipes |
| Restart recovery | Unit-scale only | Needs E2E experiment | Checkpointed file stream | Emulator ack | Not checked |
| BigQuery subscription | N/A | N/A | N/A | **Not emulated** | Requires cloud test |
| Dashboard | No infra needed preview | Streamlit | SQL results | Streamlit on BigQuery (cloud) | AI/BI / Streamlit |

### Deployment and cost safeguards

- Local code cannot automatically deploy to GCP, ClickHouse Cloud or Databricks. Validate target-specific SQL and IaC manually. `terraform plan` or `databricks bundle validate` first; `apply/deploy` only when access and spend are explicitly approved.
- Cloud profiles are **design/integration drafts**, not production-verified.
- Check ClickPipes supported Kafka endpoint/auth, DFE quotas, Unity Catalog permissions, BigQuery location/service identity, and permissions/billing before deployment.
- No real account/orders, secrets, Gmail, SMS, or personal financial events in public fixtures.

## F. Test gates and release readiness

**Gate 0:** parser/contract/fixture tests green, SQL target filenames mapped, safe inventory script passes, deterministic preview matches fixture; 100% offline.

**Gate 1:** evidence of a project-owned Redpanda+ClickHouse local E2E; dedup/late/offset restart; dashboard shows fresh rows. Without logs mark NOT RUN.

**Gate 2:** real Spark `readStream` checkpoint+restart and Beam DirectRunner TestStream tests; optionally Pub/Sub emulator. These are separate from a continuously running Kafka/Beam production stream.

**Gate 3:** cloud opt-in IAM, source ingestion, query/dashboard, measured throughput/latency/cost/alerts. Requires explicit validation and must never inherit Gate 0's green status.

Use `docs/workbooks/05_fault_injection_and_evidence.md` as a run record; do not claim a gate passed without a command output and timestamp.

## G. Files and entry points

| Task | Entry point |
| --- | --- |
| Inventory | `scripts/discover_local_runtime.py` |
| Schema + parser | `src/market_pulse/domain.py`, `src/market_pulse/bybit_ws.py` |
| Fixture producer / live WS | `scripts/produce.py` |
| ClickHouse DDL, Kafka consumer | `scripts/clickhouse_setup.py`, `scripts/clickhouse_consumer.py` |
| Reference OHLCV | `scripts/preview_marts.py` |
| Spark local | `scripts/local_spark_debug.py`, `sql/spark/ohlcv.sql` |
| Beam windows | `src/market_pulse/beam_pipeline.py`, `tests/test_beam_optional.py` |
| Pub/Sub Emulator | `scripts/gcp_emulator_smoke.py` |
| DBX SQL + AI/BI | `sql/databricks/`, `databricks.yml`, `dashboards/market_pulse.lvdash.json` |
| GCP cloud draft | `infra/gcp/main.tf`, `sql/bigquery/` |
| Specification | `docs/SPEC.md`; handoff: `docs/CLAUDE_CODE_PROMPT.md` |

See the workbook directory for step-by-step experiments and evaluation questions.
