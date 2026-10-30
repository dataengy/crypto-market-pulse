# CMP-ch — local dev & debug (Redpanda → ClickHouse → Streamlit)

Lane index: [README.md](README.md) · tasks: [tasks.md](tasks.md) · cloud: [02-cloud-deploy-test.md](02-cloud-deploy-test.md)

## Context
The reference is `crypto-market-pulse-chatgpt/project`, a ChatGPT handoff that was never run. Its ClickHouse lane has the right shape: Bybit `publicTrade` → `normalize_trade` → Kafka `market.trades.v1` → `trades_raw` → dedup → 1m OHLCV → latest → Streamlit. Its own `VALIDATION_REPORT.md` says none of that was executed end to end: no Kafka client, Docker, ClickHouse or live WS. These source defects get fixed here, not copied:

| Source issue | Fix in CMP-ch |
|---|---|
| `settings.py` has a dataclass with defaults, `os.getenv(..., default)`, and `profile or "clickhouse"` | strict loader: `config["k"]` / `os.environ["K"]`; a missing key raises with the key name and the file to fill |
| `clickhouse_sink._auth()` defaults to `default` / `""` | `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` are required, from `config/.env.secrets` |
| scalars in code: WS URL, 20 s ping, 30 s backoff cap, 15/5 s timeouts, 8 MB frame, ts bounds 2000–2100, 30 s flush/HTTP timeouts, 1.0 s poll, `sasl.mechanisms=PLAIN` | moved to `config/config.yaml` |
| password literal in `infra/clickhouse/compose.yml` | `env_file: config/.env.secrets`; ports come from `${VAR:?}` (fail fast, no fallback) |
| `trades_dedup` is a `row_number()` view over all of raw, so every query scans everything | `ReplacingMergeTree` dedup table fed by an MV, read with `FINAL` ([§4](#l-schema)) |
| `clickhouse_setup.py` splits on `";\n"` and does a string `replace("market_pulse.")` | one statement per file, a `{db}` placeholder, `clickhouse-connect` |
| `--max-messages 8` hangs forever when no traffic arrives | consumer exits after `kafka.idle_exit_s` with no messages |
| `produce.py` defaults (`--sink stdout`, profile `None`) | `--source fixture|bybit` and `--sink` are required |

Layout mirrors the Databricks lane (`partitioned-purring-pillow.md`). The implementation lives in a new sibling dir, **`./CMP-ch/`**, a standalone copy.

## 1. Layout <a id="l-layout"></a>
→ [CH-L01](tasks.md#ch-l01), [CH-L02](tasks.md#ch-l02)
```
CMP-ch/
  pyproject.toml          uv; py3.12; confluent-kafka, clickhouse-connect, websockets, pyyaml, streamlit, pandas, pytest
  justfile                inventory, up/down, topic, ch-setup, produce, consume, verify, test, it, dashboard, dbg-*
  compose.yml             cmp-ch-redpanda + cmp-ch-clickhouse, 127.0.0.1-only binds, owner label, healthchecks
  config/config.yaml      symbols, category, bybit.*, domain.*, kafka.*, clickhouse.*, dashboard.*, profiles.local|cloud
  config/.env.common      CMP_PROFILE, CMP_RP_KAFKA_PORT, CMP_CH_HTTP_PORT, CMP_CH_NATIVE_PORT
  config/.env.secrets.demo  CLICKHOUSE_URL/USER/PASSWORD, KAFKA_BOOTSTRAP, KAFKA_API_KEY/SECRET (empty)
  src/cmp_ch/  domain.py bybit_ws.py publish.py   copied from source; scalars → config
               settings.py                        rewritten, strict
               sink.py                            consume loop: insert-then-commit, idle exit, poison stop
               reference.py                       pure-Python OHLCV (from beam_pipeline.compute_stats) for asserts
  sql/clickhouse/{010_db,020_raw,030_dedup,035_dedup_mv,040_1m,050_latest}.sql   one statement each, {db} placeholder
  sql/checks/fixture_1m.sql                       assertion query, reused by the cloud check
  scripts/{produce,consume,ch_setup,verify}.py    thin CLIs over src/
  dashboards/app.py       Streamlit, ClickHouse only
  tests/  unit (domain, settings strictness, SQL render) + it/ (marker `needs_docker`) + fixtures/trades.jsonl
```
Strict read pattern: `cfg["kafka"]["topic"]`, `os.environ["CLICKHOUSE_PASSWORD"]`. Load with `load_dotenv(config/.env.common)` then `.env.secrets`, both with `override=False`. Check the required keys once at startup.

## 2. Local runtime: discover first, then compose <a id="l-runtime"></a>
→ [CH-L03](tasks.md#ch-l03)
1. `just inventory` copies the read-only discovery from the source `scripts/discover_local_runtime.py`, plus `docker ps -a`, `docker compose ls --all`, `colima list` and `command -v clickhouse rpk`. Record the chosen runtime per service in the run log. Never commit inventory output.
2. **Reuse** a compatible running ClickHouse or Kafka: put its endpoint in `.env.secrets`, then create a project-owned DB `market_pulse_dev`, topic and group `cmp-ch-local-v1`. Never alter someone else's schema, topic or group.
3. **Only if nothing fits**, `just up` runs `docker compose -p cmp-ch up -d --wait`:
   - Containers `cmp-ch-redpanda` (Kafka `127.0.0.1:${CMP_RP_KAFKA_PORT}`, advertised external = the same) and `cmp-ch-clickhouse` (HTTP and native on `127.0.0.1`).
   - Pin images: a Redpanda v25.x tag and a ClickHouse LTS tag. Re-check the current tags on Docker Hub; the source used `v24.3.10` and `25.3`.
   - Label every container `com.crypto_market_pulse.owner=cmp-ch`.
   - Healthchecks: `rpk cluster health`, `clickhouse-client -q 'SELECT 1'`.
4. `just down` runs `compose -p cmp-ch stop` and only touches containers with our label. It never uses `-v` and never prunes. Volumes are removed only by an explicit `just nuke-own`, which asks first.
5. Docker socket access needs an approved sandbox bypass. Agents ask before `up`.

## 3. Producer <a id="l-producer"></a>
→ [CH-L05](tasks.md#ch-l05)
- `just produce fixture` runs `scripts/produce.py --source fixture --sink kafka --file tests/fixtures/trades.jsonl`. It produces 8 messages, including 1 duplicate (`t02`). The message key is `event_id`, so duplicates land on the same partition.
- `just produce bybit <max_trades>` connects to the live WS with `symbols` and `category` from config. Reconnect and backoff come from `bybit.*`. Use `--sink stdout` for a dry look.
- `KafkaPublisher` builds its config from `profiles.<p>.kafka.*` plus secrets: `security.protocol`, `sasl.mechanisms` and `client.id` come from config. Delivery errors raise, and a `close()` flush with undelivered messages fails.

## 4. Schema & SQL <a id="l-schema"></a>
→ [CH-L04](tasks.md#ch-l04)

**Decision:** keep raw, dedup with RMT, and serve through views.
```
trades_raw     MergeTree, ORDER BY (symbol, event_time_ms, event_id), PARTITION BY toYYYYMM(event time)
               landing table, also the ClickPipes target in cloud; keeps physical duplicates as evidence
trades_dedup   ReplacingMergeTree, same ORDER BY/PARTITION; fed by MV 035 (validity filters of source 003)
trades_1m      VIEW: SELECT … FROM trades_dedup FINAL GROUP BY symbol, toStartOfMinute(...)
               open/close = argMin/argMax(price, (event_time_ms, event_id)); VWAP; buy_trades; max_ingest_lag_ms
trades_latest  VIEW over trades_dedup FINAL: argMax(price, (event_time_ms, event_id)) per symbol
```
- The dedup key is `event_id`, and it is the last column of the ORDER BY. A duplicate trade carries the same `symbol` and `event_time_ms`, so it collapses, and it sits in the same partition. That makes `SETTINGS do_not_merge_across_partitions_select_final=1` safe and fast.
- RMT runs without a version column, so the last inserted copy survives. The only field that differs between copies is `received_at_ms`, so `max_ingest_lag_ms` may reflect either arrival. This is a documented deviation from the source's "first arrival wins". OHLCV is unaffected.
- **Trade-offs considered:** `FINAL` dedups at query time, which is exact and cheap at our volume. A `row_number` view (the source) is exact but scans all of raw, so it is rejected. An AggregatingMergeTree 1m mart is fast, but the MV sees every insert, including duplicates, so `count` and `sum` double-count. It would need dedup upstream of the MV, so it goes to the backlog → [CH-LB2](tasks.md#ch-lb2).
- **Late events:** views recompute on every query, so late or out-of-order trades simply revise their minute. There is no watermark and nothing is dropped. This policy is what F7 tests.
- Decimal: `Decimal(38,12) × Decimal(38,12)` gives scale 24 and a max of about 1e14. That is fine for 1m notional. Add a unit test with a large-qty row so an overflow fails loudly.
- `just ch-setup` runs `scripts/ch_setup.py`, which applies the files in order. All of them are `IF NOT EXISTS`. A non-local host is refused unless `CMP_ALLOW_REMOTE_DDL=YES` is set (strict read, used only by the cloud task).

## 5. Consumer <a id="l-consumer"></a>
→ [CH-L06](tasks.md#ch-l06)

**Decision:** a Python consumer (`confluent-kafka` + `clickhouse-connect`) writing to `trades_raw`.
- Why: it writes to the same table as ClickPipes, so the MV, dedup and views downstream are identical in local and cloud. The commit boundary is explicit and in our code, so F3 can be injected with `--crash-after-insert`. Poison messages stop the consumer instead of being skipped. And the same binary is the cloud fallback ingest ([CH-CB2](tasks.md#ch-cb2)).
- The alternative, a ClickHouse `Kafka` engine table + MV → `trades_raw`, needs no extra process but has a different config and failure surface. It goes to the backlog → [CH-LB1](tasks.md#ch-lb1).
- Loop: poll → validate (`domain.validate_event`) → batch up to `clickhouse.insert_batch_size` or `kafka.batch_max_wait_s` → `INSERT JSONEachRow` → `commit(asynchronous=False)`. Delivery is at-least-once by design, and dedup absorbs the replays.
- Exit when `--max-messages` is reached or after `kafka.idle_exit_s` with no messages. A poison message raises and leaves its offset uncommitted.

## 6. Dashboard <a id="l-dashboard"></a>
→ [CH-L09](tasks.md#ch-l09)

**Decision:** Streamlit. It reuses the source `dashboards/app.py` with the GCP and DBX branches removed, and the same app deploys to Streamlit Community Cloud ([CH-C07](tasks.md#ch-c07)).
- TTL and row limit come from `dashboard.*`. The app shows a stale-data badge when `now - latest_event_time_ms > dashboard.stale_after_s`, which covers F10. It connects with a read-only `cmp_dash` user.
- Grafana with the ClickHouse plugin → backlog [CH-LB3](tasks.md#ch-lb3).

## 7. Fault injection <a id="l-faults"></a>
→ [CH-L08](tasks.md#ch-l08)

Run only against project-owned resources. Each experiment fills one row of the source `05_fault_injection_and_evidence.md` run record.

| ID | Inject | Expect |
|---|---|---|
| F1 dup replay | `just produce fixture` twice + consume | `count()` raw grows by 8; `uniqExact(event_id)`=7 in a fresh DB; `trades_1m` unchanged |
| F2 out-of-order | `--shuffle-seed N` fixture | identical bars (open/close ordered by `(event_time_ms, event_id)`) |
| F3 crash before commit | `consume --crash-after-insert 3`, restart | raw has replayed rows; dedup + 1m unchanged; `rpk group describe` lag → 0 |
| F4 consumer pause | stop consumer, produce bybit 200, restart | lag rises then drains |
| F5 poison | `rpk topic produce` invalid JSON | consumer exits non-zero, offset not committed, message identifiable |
| F7 late event | `tests/fixtures/late.jsonl`: BTCUSDT 10:00:59 trade sent after 10:01 data | 10:00 bar revised to `reference.py` expectation |
| F10 staleness | stop producer | dashboard stale badge after `stale_after_s` |

F6 (WS disconnect) and F8 (schema drift) are out of scope for this lane, so they get no task.

## 8. Debug tooling <a id="l-debug"></a>
→ [CH-L10](tasks.md#ch-l10)

`just dbg-*` recipes are thin wrappers. Container names come from `.env.common`.
- **Kafka:**
  - `rpk topic list|describe market.trades.v1`
  - `rpk topic consume market.trades.v1 -n 5 -o start`
  - `rpk group describe cmp-ch-local-v1` (lag per partition)
  - `rpk topic produce` (for F5)
- **ClickHouse:**
  - `clickhouse-client` (`docker exec -it cmp-ch-clickhouse clickhouse-client`, or the host binary if one was found)
  - `system.parts` (active parts and rows per table, i.e. whether a merge happened)
  - `system.query_log` (failed inserts: `type='ExceptionWhileProcessing'`)
  - `system.errors`
  - `system.part_log` (MV inserts)
  - `system.mutations`
- **Sanity SQL** (`just dbg-counts`): raw count vs `uniqExact(event_id)` vs `count() FROM trades_dedup FINAL`, plus the latest minute per symbol.

## 9. Tests & verification <a id="l-verify"></a>
→ [CH-L07](tasks.md#ch-l07), [CH-L11](tasks.md#ch-l11)
- `just test` runs the unit tests:
  - domain (copied)
  - settings strictness: a missing key raises with the file name
  - SQL render (`{db}` substitution)
  - `reference.py` against the fixture
- `just it` runs the integration tests (`needs_docker`): a fresh DB `market_pulse_it_<pid>`, a fresh topic and group, then fixture → Redpanda → consumer → CH. The test:
  - asserts the BTCUSDT 10:00 bar (2026-10-30 10:00 UTC): `trade_count=4, volume=0.45, open=70000, high=70010, close=69990`, and `uniqExact(event_id)=7` against `count()=8`
  - replays plus a rerun with the same group, and asserts the bar is unchanged (idempotency)
  - drops its DB and topic at the end
- `sql/checks/fixture_1m.sql` is the shared assertion and runs as `just verify <db>`.
- Fixture minutes collide with live data from the same date, so the assertion always runs on an isolated database.
- `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py CMP-ch/src CMP-ch/scripts --exit-nonzero-on-find`.
- CI ([CH-L11](tasks.md#ch-l11)): a GH Actions job runs `just test` plus `just it` with fresh Redpanda and ClickHouse service containers. The local reuse policy does not apply in CI, which is hermetic.

**Done when:** `just up && just ch-setup && just produce fixture && just consume && just verify market_pulse_dev` passes twice in a row, the F1–F5, F7 and F10 rows are logged, and `just dashboard` shows the bars.
