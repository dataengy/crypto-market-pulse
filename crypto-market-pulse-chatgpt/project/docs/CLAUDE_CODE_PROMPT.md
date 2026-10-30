# Claude Code implementation handoff — Crypto Market Pulse

You are implementing the Crypto Market Pulse market-streaming demo from this ZIP. Read `README.md`, `docs/SPEC.md`, and `docs/LOCAL_RUNTIME_REUSE_POLICY.md` first. Treat `baseline/weather_dfe_handoff.zip` as a read-only legacy reference. Do not overwrite or archive unrelated work.

## Non-negotiable rules

1. Inventory `PATH`, `~/.apps/`, `~/.app/`, Docker and Colima **before installation or `docker compose up`**. Priorities: existing OS apps → compatible existing authorized containers → isolated new container → installation. Run `python3 scripts/discover_local_runtime.py --markdown`. Record versions, reachable endpoints, owner, state and risks. Read-only discovery must never print secrets.
2. Do not stop/remove/modify pre-existing containers, images, topics, databases, Docker volumes or services without owner permission. If local port is occupied, reuse with explicit checks or choose a new isolated port instead of killing processes.
3. Never create paid GCP/Databricks/Confluent/ClickHouse Cloud resources without explicit approval. Never auto-run `terraform apply` or `databricks bundle deploy` in CI.
4. Do not request/commit private Bybit keys. Source is public trade WebSocket. Do not implement trading or financial signals.
5. Use Python for external I/O, connectivity, replay and test harness; SQL in separate files for business models. Keep shared contract semantic parity, documented engine differences and `settings.py`+profile YAML.
6. Keep all offline CI green before proposing cloud testing. Never label a profile ready without actual runtime evidence.
7. Inspect `pwd`, `git remote -v`, worktree status, `gh auth status` and repository permission. Do not assume `dataengy` and `beloz978` are interchangeable. Avoid archival/fork unless user separately approves. Draft PR on feature branch only after rights and explicit authorization.

## Implementation steps

- Review existing implementation and fail-fast checks (settings, producer, Bybit payload, Decimal, event_time, `event_id`). Add fuzz/bad-message tests and no-backfill disclaimer.
- Verify replay → local Kafka → CH raw insert → SQL view OHLCV/latest. Reuse existing services. Demonstrate duplicate replay without double-counting.
- Verify local Spark Structured Streaming `availableNow` plus checkpoint. Distinguish bounded batch-like replay from continuous live source.
- Verify Beam TestStream via DirectRunner and optional Pub/Sub Emulator smoke; preserve its no-BigQuery limitation. Keep DataflowRunner as later cloud enhancement.
- Validate `.lvdash.json`, Databricks bundle, Terraform and SQL dialects with the actual target tool/runtime before claiming compatibility.
- Add reasonable failure/restart, lag/latency, DQ tests and robust logging. Avoid overselling exactly-once or end-to-end real-time.
- Update docs with measured vs unmeasured claims, reproducible commands and any external dependency / limitation.

## Expected deliverable

A small series of Conventional Commits on a `feat/crypto-market-pulse-*` branch, with CI summary and proof for each runtime tested, then a **draft** PR only after repository permission is confirmed and user has approved pushing. Report unresolved blockers transparently. First priority is local working ClickHouse E2E; second Spark + Beam; cloud deployments are strictly opt-in.

## Environment-specific caveat

Do not move local `@beloz978/weather_dfe` or change remotes merely because earlier sessions contained confusing GitHub 404/auth errors. Inspect the real checkout and owner; if access denied, give steps without destructive changes.
