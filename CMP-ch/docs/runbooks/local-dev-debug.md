# Runbook: local dev & debug

These are the target recipes from [add-local-redpanda-clickhouse-loop](../../openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md). They are not implemented yet. Full plan: [01-local-dev-debug.md](../../../docs/plans/clickhouse/01-local-dev-debug.md).

## Ground rules
- Discover first, and reuse a compatible running Redpanda/Kafka or ClickHouse before starting anything (`just inventory`, read-only).
- Only project-owned objects may be created or dropped:
  - containers labelled `com.crypto_market_pulse.owner=cmp-ch`
  - DBs `market_pulse_dev` / `market_pulse_it_*`
  - group `cmp-ch-local-v1`
- Never use `docker compose down -v`, `docker system prune`, or drop someone else's DB, topic or group.
- Docker needs an approved sandbox bypass. Agents ask before `just up`.

## Happy path
```bash
just inventory                       # what is already running (read-only)
just up                              # only if nothing fits; idempotent
just ch-setup                        # DDL into market_pulse_dev (IF NOT EXISTS)
just produce fixture && just consume # 8 msgs → trades_raw (exits after idle_exit_s)
just verify market_pulse_dev         # BTCUSDT 10:00 = 4 / 0.45 / 70000 / 70010 / 69990
just dashboard                       # Streamlit on the views
just down                            # stop owned containers; volumes kept
```

## Failure modes
| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `KeyError`/`ValueError` naming a key at startup | config or secret not filled | the error names the file | fill `config/config.yaml` or `config/.env.secrets` (template `.env.secrets.demo`); never add a default |
| compose: `variable is not set` | `.env.common` port missing | `just inventory` | set `CMP_*_PORT` in `config/.env.common` |
| `bind: address already in use` | another Kafka or ClickHouse already on the port | `docker ps`, `lsof -i :<port>` | reuse that service (endpoint in `.env.secrets`) or change the port in `.env.common`; do not stop the other one |
| producer exits non-zero, "undelivered N" | broker unreachable, or the advertised listener is wrong | `just dbg-rpk-topic` | the advertised address must be `127.0.0.1:${CMP_RP_KAFKA_PORT}` |
| consumer exits non-zero with partition/offset | poison message (F5) | `rpk topic consume … -o <offset> -n 1` | fix the producer or skip it deliberately by committing past it with `rpk group seek`; record it in evidence |
| consumer hangs | it should not: idle exit | `kafka.idle_exit_s` | treat as a bug against the `ingest` spec |
| `verify` count 8 but bar wrong | dedup bypassed (query not using `FINAL`) or MV missing | `just dbg-counts`, `SHOW CREATE` of the views | re-run `just ch-setup`; check that MV 035 exists |
| bar differs only on a 2026-10-30 run | live data collides with the fixture minutes | which DB was asserted | assert only on an isolated `market_pulse_it_*` DB |
| `ch-setup` refuses the host | the remote-DDL guard | `CLICKHOUSE_URL` | intended; cloud only, with `CMP_ALLOW_REMOTE_DDL=YES` |
| Decimal overflow error | notional exceeds `Decimal(38,24)` | the offending row | expected loud failure; investigate the source data |
| query slow, many parts | merges are behind, so `FINAL` does more work | `just dbg-sys-parts` | `OPTIMIZE TABLE … FINAL` on owned tables only; consider CH-LB2 |

<a id="fault-injection"></a>
## Fault injection (CH-L08)
Run each fault on owned resources only, and record UTC, SHA, command, expected / actual and PASS / FAIL in `docs/evidence/`. The fault table (F1–F5, F7, F10) is in [01 §7](../../../docs/plans/clickhouse/01-local-dev-debug.md#l-faults). The pass criteria are the scenarios in the [ingest](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ingest/spec.md) and [ohlcv-marts](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ohlcv-marts/spec.md) specs.
