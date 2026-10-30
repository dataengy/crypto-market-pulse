---
title: CMP-gcp local dev & debug
created: 2026-10-30
updated: 2026-10-30
---

# PRD: CMP-gcp local dev & debug

## 0. Document Purpose
This PRD is for the agents and the human implementing `GCP-L*`. It is BMAD v6.12.4 `bmad-prd` shape, adapted with the developer-product and small-scope clusters. It builds on the existing plan and does not repeat it: [01-local-dev-debug.md](../../docs/plans/gcp/01-local-dev-debug.md) holds the step detail, and [tasks.md](../../docs/plans/gcp/tasks.md) holds IDs, dependencies and acceptance. Inputs: [project-brief.md](project-brief.md), [architecture.md](architecture.md). Breakdown: [epics.md](epics.md) → [stories/](stories/).

## 1. Vision
A laptop loop that proves the GCP lane's two aggregation paths, SQL over raw and Beam over the stream, on one fixture with no cloud. It also makes streaming failures (watermark stall, late data, duplicates, poison) reproducible on demand.

## 2. Target User
### 2.1 Jobs To Be Done
- As the builder, I want both paths green locally before I spend anything on GCP.
- As a debugging agent, I want one command per failure mode, and evidence that shows expected next to actual.

### 2.2 Key User Journeys
- **UJ-1. Fresh laptop to green.** Nikolay clones the repo and runs `just discover`, which reuses the host `gcloud` emulator. `just up && just test && just it` then asserts FX on both paths in minutes.
- **UJ-2. Empty Beam output.** The raw table is full but `trades_1m_beam` is empty. The runbook's first check (heartbeat / `timestamp_attribute`) finds the stalled watermark ([runbook](runbooks/local-dev-debug.md#empty-beam)).
- **UJ-3. Prove late-data semantics.** `just fault-late` shows that a LATE pane updates the bar within lateness, and that reconciliation shows the diff beyond it.

## 3. Glossary
- **FX** — the fixture assertion: BTCUSDT 10:00 → `trade_count=4, volume=0.45, open 70000, high 70010, low 69990, close 69990`, from 8 events with 1 duplicate (7 unique).
- **SQL path** — Pub/Sub → (shim locally / BigQuery subscription in the cloud) → `trades_raw` → `trades_dedup` → `trades_1m` / `trades_latest`.
- **Beam path** — Pub/Sub → Beam → `trades_1m_beam_panes` → view `trades_1m_beam`.
- **Shim** — the local-only stand-in for BigQuery-subscription delivery ([ADR-0004](adr/0004-bq-subscription-shim.md)).
- **Heartbeat** — the message after a finite replay that pushes the watermark past every fixture window.
- **Pane** — one Beam window firing (ON_TIME or LATE, with a `pane_index`).
- **Profile** — `local` or `cloud`, chosen by `CMP_PROFILE`. This PRD covers `local` only.
- **Oracle** — `reference.py`, the pure-Python expected values.

## 4. Features

### 4.1 Runtime & configuration
#### FR-1: Read-only runtime discovery — GCP-L01
`just discover` lists host tools, containers and port listeners, then picks reuse → host → compose ([reuse policy](../../crypto-market-pulse-chatgpt/project/docs/local/LOCAL_RUNTIME_REUSE_POLICY.md)). Realizes UJ-1.
- Exits 0 with no side effects; the inventory is never committed.
#### FR-2: Strict settings — GCP-L02
All scalars come from `config/config.yaml` or `config/.env.*`; no defaults.
- A missing key raises `ValueError` naming the key and the file to fill. An unknown profile fails.

### 4.2 Ingest
#### FR-3: Producer with attributes + heartbeat — GCP-L03
`produce.py --source fixture|bybit`. Every message carries `event_id`, `event_time_ms` and `symbol` attributes, and a fixture replay ends with one heartbeat.
- `--sink stdout` prints 8 events + 1 heartbeat.
#### FR-4: Local emulators — GCP-L04
Pub/Sub emulator (reused, host, or compose) + goccy BigQuery emulator, bound to 127.0.0.1.
- `just up` ×2 creates no duplicates; `just down` leaves reused services untouched and never uses `-v`.

### 4.3 SQL path
#### FR-5: Templated GoogleSQL + compatibility probe — GCP-L05
`{{dataset}}` templates 001–005 plus the DQ view, run unchanged on the emulator and in the cloud.
- Every file either runs on the emulator or is listed as `skip_on_emulator` in `docs/emulator-gaps.md`.
#### FR-6: Subscription shim — GCP-L06
Pull → `insert_rows_json` → ack after a successful insert.
- The fixture gives 8 raw rows and 7 dedup rows.

### 4.4 Beam path
#### FR-7: Event-time pipeline — GCP-L07
Fixed windows, ACCUMULATING late panes, dedup by `event_id`, quarantine output, append-only pane sink plus latest-pane view ([ADR-0003](adr/0003-dedup-and-late-data.md)).
- `beam_run --profile local` writes FX to `trades_1m_beam` and logs the runner that actually ran ([ADR-0002](adr/0002-directrunner-not-prism.md)).
#### FR-8: TestStream suite — GCP-L08
Cases 1–6 from [plan §8](../../docs/plans/gcp/01-local-dev-debug.md#s8), checked against the Oracle.
#### FR-9: Debug tooling — GCP-L12
`debug-pubsub`, `debug-bq`, `debug-beam`; the Beam workbook notebook runs inside the test suite.

### 4.5 Verification
#### FR-10: E2E + idempotent rerun — GCP-L09
`just it` asserts FX on both paths; a second replay doubles raw and leaves both bars unchanged.
#### FR-11: Fault injection — GCP-L10
F1/F2/F3/F5/F7/F10 with evidence in `.tmp/evidence/`; PASS only when expected and actual are both shown. Realizes UJ-3.
#### FR-12: Live Bybit smoke — GCP-L11
A bounded live run into the emulators; ingest lag recorded.
#### FR-13: Hermetic CI — GCP-L13
Unit + TestStream + emulator integration on PRs, with no cloud credentials.

## 5. Cross-Cutting NFRs
- **NFR-1 No hardcoded scalars:** IDs, URLs, ports, timeouts, window and lateness values and regexes live in config ([user rule](../AGENTS.md#policy)). Gate: `find_hardcoded_scalars.py --exit-nonzero-on-find`.
- **NFR-2 No defaults, fail fast:** `os.environ["X"]`, `load_dotenv(override=False)`; no `getenv(..., d)`, `${X:-d}` or `dict.get(k, d)` for config.
- **NFR-3 Secrets:** only in `config/.env.secrets` (git-ignored; keys listed in `.env.secrets.demo`) or Bitwarden `bw`. The local profile needs **none**.
- **NFR-4 Localhost only:** binds on 127.0.0.1; project-labelled containers; no destructive teardown.
- **NFR-5 Determinism:** windowing, lateness and dedup are proven with TestStream, not by sleeping on wall-clock time.
- **NFR-6 Least code:** reuse the `CMP-dbx-fe` patterns (settings, domain, fixture); no abstraction without a second caller.

## 6. Non-Goals
- No GCP project, gcloud auth, Terraform, Dataflow, Looker Studio or cloud CI (→ `GCP-C*`, [`../deploy/`](../deploy/README.md)).
- No exactly-once claim from local tests. No durable restart semantics (DirectRunner has no checkpoint).
- No DuckDB SQL fork ([GCP-L14](../../docs/plans/gcp/tasks.md#gcp-l14)); no Prism + Pub/Sub ([GCP-L15](../../docs/plans/gcp/tasks.md#gcp-l15)).

## 7. MVP Scope
In: FR-1…FR-13. MVP cut line if time-boxed: FR-1…FR-10 (L11, L12, L13 can follow).

## 8. Success Metrics
- **SM-1** FX green on both paths, plus an idempotent rerun. Validates FR-6, FR-7, FR-10.
- **SM-2** TestStream cases 1–6 green. Validates FR-8.
- **SM-3** Fault matrix all PASS. Validates FR-11.
- **SM-C1** Wall-clock run time: do not optimize it by shortening lateness or windows in config. Counterbalances SM-1.

## 9. Open Questions
1. Does goccy support `SAFE.PARSE_JSON`, `QUALIFY`, `BIGNUMERIC` and `ARRAY_AGG … LIMIT`? → L05 probe.
2. Can `WriteToBigQuery` target the emulator? Assumed no → local DoFn sink.
3. Does the TestStream / `ReadFromPubSub` streaming path force the BundleBased DirectRunner fallback in the pinned Beam? → L07 logs the runner.
4. What exact metadata columns does a BigQuery subscription write? → GCP-C02 (cloud).

## 10. Assumptions Index
- §4.3: goccy is compatible enough for 001–005 [ASSUMPTION; gate: L05].
- §4.4: a local DoFn sink is acceptable as a stand-in for `WriteToBigQuery` [ASSUMPTION].
- §5 NFR-3: the local profile needs no secrets at all [ASSUMPTION].
