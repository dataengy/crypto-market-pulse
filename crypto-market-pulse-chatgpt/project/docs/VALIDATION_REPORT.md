# Crypto Market Pulse — Validation and readiness record

Date: 2026-10-30 (UTC+4 calendar date). All commands below were executed inside the isolated ChatGPT Linux container, **not** on the user's Mac, GitHub Actions, Databricks, or GCP.

## P0: Offline, verified

| Verification | Evidence | Result |
|---|---|---|
| Python domain/unit/contract tests | `PYTHONPATH=src pytest -q tests --ignore=tests/test_beam_optional.py` | **18 passed** |
| Reference OHLCV | `python scripts/preview_marts.py` | Four (symbol,minute) rows; 7 distinct trades from 8 fixture messages; one replay duplicate; BTCUSDT 10:00 minute volume 0.45, open 70000.0, close 69990.0 |
| JSON/YAML | Python `json.loads`, `yaml.safe_load` over all codebase JSON/YAML | Parsed successfully |
| Notebook 01 | `nbclient.NotebookClient(...).execute()` | Executed successfully (nbformat emitted missing cell-id warning, non-fatal) |
| Python syntax | `python -m compileall -q src scripts dashboards tests notebooks` | Checked in archive verification |

The fixture consists of **synthetic** market events, not real historical Bybit prices.

## Not verified in this container

- `ruff` was not installed; GitHub Actions lint/format job has not run.
- `apache_beam`, `pyspark`, Kafka Python client, and Docker were not available; no Beam DirectRunner TestStream, Spark checkpoint flow, Redpanda/ClickHouse E2E, or container integration was run.
- No cloud deployment or provider-specific SQL execution was run (ClickHouse Cloud / GCP Pub/Sub → BigQuery / Dataflow / Databricks DFE).
- No Bybit live WebSocket session or market-data freshness/latency measurements were run here.
- The Databricks dashboard JSON was generated/validated as JSON only, not imported to a workspace.
- CI configuration has not executed inside GitHub Actions and cannot be called green yet.

## GitHub publishing blocker

Repository `dataengy/crypto-market-pulse` was found through the GitHub connector and reports `push: true` in repository metadata; actual writes failed with `403 Resource not accessible by integration` for both the Contents API and Git Trees API. **Nothing was committed or pushed remotely.** This is an integration grant/permissions issue; fixing it may require GitHub App repository installation scopes (Contents: write) or re-authorizing the connector. This handoff package includes an **offline Git bundle** with stages prepared as commits, which can be pushed locally once authorized.

## Stage readiness (not production readiness)

| Phase | Readiness | What still needs runtime validation |
|---|---|---|
| Core/parser/replay/settings | P0 verified | Live websocket reconnect and source gap behaviour |
| ClickHouse local / Redpanda | Draft + offline SQL checks | Broker/consumer/ClickHouse E2E, replay, offsets, dashboard |
| Databricks / local Spark | Draft + JSON/SQL checks | Spark checkpoint restart, Lakeflow SQL, dashboard import |
| GCP / Beam | Draft + optional Beam tests defined | DirectRunner, Pub/Sub Emulator, BigQuery Subscription in cloud |
| Guides/manual/workbooks | Present and structurally checked | Execute practical exercises and collect logs |

Never infer exactly-once delivery or cloud portability from P0 tests alone.
