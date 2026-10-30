# Product Brief: CMP-gcp — local dev & debug loop

Status: draft · 2026-10-30 · BMAD v6.12.4 (`bmad-product-brief` shape, hand-filled)
Scope: **local only** (Pub/Sub emulator + Beam DirectRunner + goccy BigQuery emulator). Cloud deploy lives in [`../deploy/`](../deploy/README.md) (separate agent, Agent OS).

## Executive Summary
The GCP lane of Crypto Market Pulse turns Bybit public trades into 1-minute OHLCV bars two ways: a SQL path (Pub/Sub → BigQuery subscription → views) and a Beam path (event-time windows, dedup, late data). A ChatGPT handoff ([`crypto-market-pulse-chatgpt/project/`](../../crypto-market-pulse-chatgpt/project/README.md)) sketched both, but none of it was ever run.

This effort builds a laptop loop that proves both paths on the same fixture, with no cloud account, no credentials and no spend. Cloud work ([GCP-C*](../../docs/plans/gcp/tasks.md#cloud)) can then reuse code and SQL that already pass.

## The Problem
- The reference code has never run: it has defaults everywhere, hardcoded scalars, and DISCARDING late panes that would overwrite a bar with only its late trades ([plan §Context](../../docs/plans/gcp/01-local-dev-debug.md#context)).
- The Pub/Sub emulator never delivers BigQuery subscriptions, and a finite replay never closes the last streaming window. Both make a local run silently empty.
- Debugging streaming semantics against real GCP is slow and costs money.

## The Solution
One `just`-driven loop under `CMP-gcp/`: discover and reuse local runtimes → emulators → SQL templates → subscription shim → Beam pipeline → fixture assertion on both paths → fault injection. The same SQL and the same domain code later run in the cloud.

## What Makes This Different
- One SQL dialect (GoogleSQL) for emulator and cloud; no forked SQL ([ADR-0001](adr/0001-bigquery-emulator-goccy.md)).
- Deterministic `TestStream` tests pin windowing, lateness and dedup ([ADR-0003](adr/0003-dedup-and-late-data.md)).
- The conventions of the working sibling lane [`CMP-dbx-fe/`](../../CMP-dbx-fe/README.md): strict config, no env defaults, the fixture oracle.

## Who This Serves
The repo owner (data engineer, course homework) and the AI agents implementing `GCP-L*` stories. Success for them: `just test && just it` is green on a clean laptop in minutes.

## Success Criteria
- FX on both paths: BTCUSDT 10:00 → `trade_count=4, volume=0.45, open 70000, high 70010, low 69990, close 69990`. A rerun leaves both bars unchanged.
- TestStream cases 1–6 green; fault matrix F1/F2/F3/F5/F7/F10 PASS with evidence.
- `find_hardcoded_scalars.py` is clean; zero `os.getenv(..., default)`.

## Scope
In: [GCP-L01…L13](../../docs/plans/gcp/tasks.md#local). Out: everything in `GCP-C*`, Dataflow, Terraform, Looker Studio, and backlog items L14/L15.

## Vision
The local loop becomes the regression gate for the cloud lane (CI, [GCP-L13](../../docs/plans/gcp/tasks.md#gcp-l13)): every cloud change must first pass the same fixture locally.
