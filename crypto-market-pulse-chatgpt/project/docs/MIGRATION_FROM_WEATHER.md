# Weather DFE → Crypto Market Pulse migration

The project is now a *public trade event stream*, not repeated weather HTTP polling. Keep Weather DFE as a reference inside `baseline/weather_dfe_handoff.zip`; do not overwrite an existing Git repository's current history or branches as a side effect of this archive.

| Weather DFE | Crypto Market Pulse |
| --- | --- |
| Open-Meteo periodic polling | Bybit public WebSocket messages with trade-level identity |
| temperature/humidity/wind observations | price/quantity/side/trade ID/exchange timestamp |
| daily/hourly weather marts | 1m OHLCV, VWAP, latest price and lag |
| likely repeated source snapshots | naturally frequent individual events |
| source freshness by API update time | source/ingest timestamp, event-time windows, retries, duplicates |
| weather UI | market-monitoring dashboard with visible aggregation cadence |
| weather SQL | `sql/clickhouse`, `sql/databricks`, `sql/bigquery` |
| weather notebooks | fixture replay entrypoint to Delta Bronze |

## Unchanged engineering agreements

SQL-first; split `settings.yml`/`settings.py`/`utils.py`; Python for producers/adapters; no mixed SQL/Python business logic; CI no cloud resources; reuse existing OS apps/containers before new ones; Python tests; Spark/Beam/ClickHouse local debug; three profiles; dashboards-as-code; Conventional Commits and draft PR on verified write access only.

## What is NOT migrated automatically

- Weather tables and notebooks, or an existing remote's default branch. Historical data remains in baseline.
- Direct DFE ingestion from WebSocket: use a separate producer and cloud-supported Bronze sink.
- Google Dataflow streaming executor and ClickHouse Cloud ClickPipes production config: both require account-specific decisions/validation.
- A real order-book stream: future phase with snapshot/delta sequence restoration, a separate schema and testing.
