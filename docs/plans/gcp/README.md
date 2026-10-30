# GCP lane: Pub/Sub + Beam + BigQuery (`./CMP-gcp/`)

Bybit V5 `publicTrade` → `normalize_trade` (`event_id = bybit:{category}:{symbol}:{trade_id}`) → Pub/Sub, which feeds two paths:
- **SQL path:** BigQuery subscription → raw table → dedup/1m/latest views → Looker Studio
- **Beam path:** event-time 1m windows, dedup by event_id, allowed lateness → `trades_1m_beam`

Both paths must reproduce the fixture: BTCUSDT 10:00 → `trade_count=4, volume=0.45, open 70000, high 70010, close 69990`.

Sibling of the Databricks lane (`CMP-dbx-fe/`), with the same conventions: uv/py3.12, justfile, compose on localhost only, strict `config/config.yaml` + `.env` files, an idempotent rerun check. Reference implementation (never run): `crypto-market-pulse-chatgpt/project/`.

| Doc | Scope |
|---|---|
| [01-local-dev-debug.md](01-local-dev-debug.md) | Pub/Sub emulator, goccy BigQuery emulator, subscription shim, Beam DirectRunner + TestStream, fault injection, debug, CI |
| [02-cloud-deploy-test.md](02-cloud-deploy-test.md) | Free tier/trial facts, Terraform fixes, auth (ADC/WIF), cloud fixture smoke, hosted producer, dashboard, optional Dataflow, teardown |
| [tasks.md](tasks.md) | `GCP-L01…L15`, `GCP-C01…C17` with dependencies and acceptance criteria |

## Status (2026-10-30)
| Area | Tasks | Status |
|---|---|---|
| Local scaffold + core | L01–L03 | planned |
| Emulators + SQL + shim | L04–L06 | planned |
| Beam + TestStream | L07–L08, L12 | planned |
| E2E + faults + live | L09–L11 | planned |
| CI (hermetic) | L13 | planned |
| Cloud core ingest + verification | C01–C05 | planned (gated: user billing + apply approval) |
| Hosted producer + dashboard | C06–C08 | planned (gated: Bybit reachability probe) |
| CI smoke / Dataflow / teardown | C09–C11 | planned (Dataflow optional, time-boxed) |
| Backlog alternatives | L14–L15, C12–C17 | backlog |
