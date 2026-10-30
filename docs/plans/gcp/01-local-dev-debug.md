# CMP-gcp — local dev & debug (Pub/Sub emulator → Beam → BigQuery emulator)

Status: plan only (2026-10-30). Implementation goes in `./CMP-gcp/`. Reference: `crypto-market-pulse-chatgpt/project/`, an untracked ChatGPT handoff that has never been run.
Same conventions as the Databricks lane (`CMP-dbx-fe/`):
- uv + Python 3.12, a `justfile`, and `compose.yml` with binds on 127.0.0.1 only
- `config/config.yaml` + `config/.env.common` + `config/.env.secrets.demo`
- strict config reading: no defaults, fail fast with the key name and the file to fill
- a fixture-based assertion and an idempotent rerun check

## Context
The source GCP lane has a clean domain core, but the rest was never executed (`VALIDATION_REPORT.md`: no Beam, no emulator, no BigQuery run). These defects are fixed here, not copied:
- `settings.py` is a dataclass full of defaults (`profile="clickhouse"`, `kafka_bootstrap=...`), and `load_settings` falls back to `"clickhouse"`.
- `bybit_ws.py` hardcodes the endpoint, the 20 s ping, the 30 s backoff cap, the 15/5 s timeouts and the 8 MB frame size. `domain.py` hardcodes the timestamp bounds. `publish.py` hardcodes the drain size 100 and the 30 s timeout.
- `beam_pipeline.py` hardcodes `FixedWindows(60)` and `allowed_lateness=30`. It uses the default trigger with **DISCARDING** panes, so a late pane would *replace* the bar with only the late trades. Fix: ACCUMULATING (below).
- The SQL hardcodes the `crypto_pulse.` dataset.
- The Pub/Sub publisher sets only a `symbol` attribute. Beam needs `event_time_ms` as the timestamp attribute and `event_id` as the id label.
- A finite fixture replay into a streaming pipeline never closes the last window, because the watermark stops moving. Fix: a heartbeat message.

## Layout (`CMP-gcp/`)
```
pyproject.toml   uv; py3.12; apache-beam[gcp] (latest 2.x, pinned in uv.lock), google-cloud-pubsub, google-cloud-bigquery, websockets, pyyaml, pytest
justfile         discover, up/down, produce, shim, beam, sql-apply, test, it, fault-*, debug-*
compose.yml      cmp-gcp-pubsub (google-cloud-cli:emulators, fallback only) + cmp-gcp-bq (ghcr.io/goccy/bigquery-emulator, pinned tag); 127.0.0.1 binds, healthchecks, label com.crypto_market_pulse.owner
config/config.yaml        profiles.local|cloud: project, topic, subscriptions, dataset, location, emulator hosts/ports,
                          window_s, allowed_lateness_s, ws.{endpoint_tmpl,ping_s,backoff_max_s,open_timeout_s,close_timeout_s,max_frame_bytes,recv_timeout_s},
                          domain.{min_ts_ms,max_ts_ms}, publish.{drain_n,result_timeout_s}, producer.heartbeat_attr, symbols, category
config/.env.common        CMP_PROFILE (local|cloud)
config/.env.secrets.demo  GOOGLE_CLOUD_PROJECT (cloud), BILLING_ACCOUNT_ID, GH repo for WIF (no keys, ever)
src/cmp_gcp/  domain.py bybit_ws.py publish.py reference.py settings.py sql.py beam_pipeline.py bq_sink.py
sql/bigquery/{001_raw,002_dedup,003_1m,004_latest,005_1m_beam}.sql   {{dataset}} templates; one dialect for emulator and cloud
scripts/  produce.py  bq_sub_shim.py  sql_apply.py  beam_run.py  discover.py  assert_fixture.py
tests/    unit/  beam/ (TestStream)  it/ (marker: needs_emulators)  fixtures/{trades,trades_late,trades_poison}.jsonl
```

## Steps

### <a id="s1"></a>1. Discover and reuse first → [GCP-L01](tasks.md#gcp-l01)
- Follow `LOCAL_RUNTIME_REUSE_POLICY.md`. `just discover` does a read-only check of:
  - `gcloud` (present: `/opt/homebrew/bin/gcloud`) and `gcloud components list` for `pubsub-emulator` (needs network the first time, and Java 17, which is present at `openjdk@17`)
  - `bq`, `duckdb`, `uv`, `just`, `docker context show`, `colima list`
  - `docker ps -a`, and listeners on the configured ports
- Order of preference for the Pub/Sub emulator:
  1. an already-running emulator that answers on `PUBSUB_EMULATOR_HOST`
  2. the host `gcloud beta emulators pubsub start --project=<cfg> --host-port=127.0.0.1:<cfg>`
  3. the compose service as a last resort
- The BigQuery emulator has no host install, so it comes from compose.
- Record the chosen runtime in the inventory table. Don't commit the inventory.

### <a id="s2"></a>2. Scaffold + strict settings → [GCP-L02](tasks.md#gcp-l02)
- `settings.py`: `load(profile)` reads YAML plus env and returns a frozen dict or dataclass **without defaults**.
- A missing key raises `ValueError("<key> missing in config/config.yaml[profiles.local]")`.
- Env is read with `os.environ["X"]` and loaded with `load_dotenv(..., override=False)`.
- Tests cover: a missing key fails, an unknown profile fails, and nothing is read from `os.getenv` with a default.

### <a id="s3"></a>3. Core port + producer → [GCP-L03](tasks.md#gcp-l03)
- Copy `domain.py`, `bybit_ws.py`, `publish.py`, `tests/fixtures/trades.jsonl` and `tests/test_domain.py`. Every scalar listed in Context comes from config. `beam_pipeline.compute_stats` moves to `reference.py` as the pure-Python oracle.
- `PubSubPublisher` sets these attributes: `event_id`, `event_time_ms` and `symbol`.
- `scripts/produce.py`:
  - `--source fixture|bybit`, `--max-trades`, `--max-seconds`, `--replay N` (for duplicate injection)
  - after a fixture replay, it publishes one **heartbeat** message (attribute `kind=heartbeat`, `event_time_ms = last + window + lateness + 1 s`) so the watermark passes every fixture window. Beam and the SQL views drop heartbeats.

### <a id="s4"></a>4. Local emulators → [GCP-L04](tasks.md#gcp-l04)
- **BigQuery locally = goccy `bigquery-emulator`**, not a DuckDB stand-in. Reasons:
  - It runs **GoogleSQL**, so `sql/bigquery/*.sql` executes unchanged in both places. DuckDB would need a forked dialect for `SAFE.PARSE_JSON`, `JSON_VALUE`, `BIGNUMERIC`, `TIMESTAMP_MILLIS` and `ARRAY_AGG(... LIMIT 1)[OFFSET(0)]`, and the sibling lane's rule is "don't fork the SQL".
  - It supports insertAll, the Storage Write/Read API (gRPC), and logical views.
  - The image is multi-arch (arm64 included).
  - Risk: it is beta and kept up by one maintainer. Step 5 is the compatibility gate; DuckDB is the backlog fallback → [GCP-L14](tasks.md#gcp-l14).
- `just up`:
  - reuses a healthy endpoint, otherwise runs `docker compose -p cmp-gcp up -d --wait`
  - writes `PUBSUB_EMULATOR_HOST` and `BIGQUERY_EMULATOR_HOST` to `.tmp/emulators.env`
  - is idempotent
- `just down` stops only project-labelled containers. It never uses `-v` and is a no-op for reused services.
- The Pub/Sub emulator keeps state in memory only. Restarting it wipes topics, so `just up` re-creates them idempotently.
- Docker needs the sandbox bypass that has already been approved.

### <a id="s5"></a>5. SQL templates + emulator compatibility probe → [GCP-L05](tasks.md#gcp-l05)
- `001_raw.sql` mirrors what a cloud BigQuery subscription with `write_metadata=true` writes: `subscription_name STRING, message_id STRING, publish_time TIMESTAMP, data BYTES, attributes STRING`, with `PARTITION BY DATE(publish_time)`. The column list must be checked against the current docs in [GCP-C02](tasks.md#gcp-c02).
- `002_dedup`:
  - filters heartbeats and invalid rows
  - dedups with `QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at_ms, publish_time, message_id) = 1`, adding `message_id` as a deterministic tie-break
  - reads only `publish_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{lookback_days}} DAY)` for partition pruning
- `002b_dq` counts unparsable rows into a quarantine view, so they are never silently dropped.
- `003_1m` and `004_latest` are ported 1:1 with `{{dataset}}`.
- `sql_apply.py` renders the templates and runs them against the emulator or the cloud through the same client (`client_options.api_endpoint` from env).
- Probe: run every file on the emulator and list any unsupported function in `docs/emulator-gaps.md` inside CMP-gcp. Don't edit the SQL for the emulator: mark that query `skip_on_emulator` and test it in the cloud ([GCP-C05](tasks.md#gcp-c05)).

### <a id="s6"></a>6. BigQuery-subscription shim (local only) → [GCP-L06](tasks.md#gcp-l06)
- The Pub/Sub emulator can create BigQuery subscriptions but never delivers them (docs, updated 2026-10-26).
- `bq_sub_shim.py` pulls from the emulator subscription, `insert_rows_json` into the emulator raw table with the same metadata columns, and acks **after** the insert succeeds, so it is at-least-once like the real subscription.
- The shim imitates only the delivery. It is not a cloud artifact and is never deployed.

### <a id="s7"></a>7. Beam pipeline (event time, dedup, lateness) → [GCP-L07](tasks.md#gcp-l07)
- `ReadFromPubSub(subscription, with_attributes=True, timestamp_attribute="event_time_ms", id_label="event_id")`. `id_label` dedup is a Dataflow feature; locally, dedup comes from the combiner.
- Then: drop heartbeats → parse/validate, with a tagged `invalid` output to `trades_quarantine` → key by symbol.
- Windowing: `WindowInto(FixedWindows(cfg.window_s), trigger=AfterWatermark(late=AfterCount(1)), accumulation_mode=ACCUMULATING, allowed_lateness=cfg.allowed_lateness_s)`.
- `CombinePerKey(StatsCombine)` keeps the first-received copy per `event_id`. It is correct because `event_id` → fixed `event_time` → exactly one window. The output carries `window_start`, `pane_index`, `timing` (ON_TIME/LATE) and `emitted_at`.
- Sink: append-only `trades_1m_beam_panes`. View `005_1m_beam` picks the max `pane_index` per `(symbol, window_start)`. This is idempotent without DML, and sandbox-safe.
  - Local sink: `bq_sink.py`, a DoFn using `google-cloud-bigquery` against the emulator.
  - Cloud sink: `WriteToBigQuery(method=STORAGE_WRITE_API)`, chosen by profile.
  - *Unverified:* whether `WriteToBigQuery` can target the emulator at all. That is why there is a local DoFn.
- Runner: `DirectRunner` with `--streaming`. In Beam 2.68+ the DirectRunner tries Prism first and falls back to `BundleBasedDirectRunner` (see `direct_runner.py` 2.74). TestStream always forces that fallback, and only that path overrides `ReadFromPubSub` for streaming. The job logs which runner actually ran. Prism + Pub/Sub → backlog [GCP-L15](tasks.md#gcp-l15).
- What allowed lateness drops can't be counted inside Beam. It is measured by reconciliation instead: `trades_1m` (SQL over raw, which keeps everything) minus `trades_1m_beam`.

### <a id="s8"></a>8. Deterministic tests (TestStream) → [GCP-L08](tasks.md#gcp-l08)
`tests/beam/` uses `TestStream` + `TestPipeline(streaming)` + `assert_that`, with values checked against `reference.py`:
1. On time, with 1 duplicate: BTCUSDT 10:00 → `trade_count=4, volume=0.45, open 70000, high 70010, close 69990`.
2. Out-of-order arrival with the same event times gives the same bars.
3. A late event within lateness gives a LATE pane with **accumulated** totals, and the view shows the updated bar.
4. A late event beyond lateness is dropped: the Beam bar is unchanged and the reconciliation query shows the diff.
5. A poison message ends up in `invalid`, with no crash.
6. Heartbeat elements are ignored.

### <a id="s9"></a>9. E2E integration + idempotent rerun → [GCP-L09](tasks.md#gcp-l09)
`just it`:
1. `up`
2. `sql-apply`
3. start the shim and `beam_run --profile local` in the background
4. `produce --source fixture`
5. `assert_fixture.py` waits, polling with an interval and timeout from config, then checks **both** `trades_1m` (subscription path) and `trades_1m_beam` (Beam path) for the BTCUSDT 10:00 values above, plus the ETHUSDT buckets from the source test
6. `produce --source fixture` again → raw rows double, but both bars are unchanged

pytest marker: `needs_emulators`.

### <a id="s10"></a>10. Fault injection (evidence per workbook 05) → [GCP-L10](tasks.md#gcp-l10)
| ID | `just` target | Expect |
|---|---|---|
| F1 dup replay | `fault-dup` (`--replay 2`) | raw ×2, dedup/1m and Beam bars unchanged |
| F2 out of order | `fault-shuffle` | identical OHLC (ordered by `(event_time, event_id)`) |
| F3 pipeline restart | `fault-restart`: kill Beam mid-replay, restart, replay | bars correct after replay. The DirectRunner has no durable checkpoint, so note that real restart semantics (drain/update) are cloud-only ([GCP-C10](tasks.md#gcp-c10)) |
| F5 poison | `fault-poison` (`trades_poison.jsonl`) | Beam quarantine row, SQL DQ count +1, pipeline still running |
| F7 late | `fault-late` (`trades_late.jsonl`: within and beyond lateness) | within: LATE pane updates the bar; beyond: reconciliation diff > 0 |
| F10 staleness | `fault-pause` | `trades_latest.latest_event_time_ms` age grows |

Each run is logged with the workbook-05 template in `CMP-gcp/.tmp/evidence/` (gitignored), and status is PASS only with expected vs actual.

### <a id="s11"></a>11. Live Bybit smoke (local) → [GCP-L11](tasks.md#gcp-l11)
- `produce --source bybit --max-seconds <cfg>` publishes to the emulator, and both paths show rows for the current minutes.
- `max_ingest_lag_ms` gets recorded.
- Reconnect is checked by toggling the network in a scratch session. The source gap is written down; there is no backfill.

### <a id="s12"></a>12. Debug tooling → [GCP-L12](tasks.md#gcp-l12)
- `just debug-pubsub`: list topics and subscriptions, pull without ack (`curl $PUBSUB_EMULATOR_HOST/v1/projects/<p>/subscriptions`).
- `just debug-bq "<sql>"`: a query through the same client.
- `just debug-beam`: `--direct_num_workers=1`, DEBUG logs, a `beam.Map(log)` tap after each stage.
- Port `notebooks/workbooks/02_beam_event_time.ipynb` to `cmp_gcp`, and execute it in tests the way the source `test_workbooks.py` does.
- Tip: an empty Beam output with a full raw table almost always means the watermark never advanced. Check the heartbeat and `timestamp_attribute`.

### <a id="s13"></a>13. Hermetic CI → [GCP-L13](tasks.md#gcp-l13)
- GH Actions on PRs runs unit tests, TestStream and the hardcoded-scalars check. The `needs_emulators` job uses service containers (the same images as compose).
- Never with cloud credentials. Cloud smoke is [GCP-C09](tasks.md#gcp-c09).

## Verification
- `just test`: unit tests (domain, settings strictness, SQL render) and TestStream (cases 1–6).
- `just up && just it`: fixture assertions on both paths, then an idempotent rerun.
- `just fault-all`: an evidence log for F1, F2, F3, F5, F7 and F10.
- `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py CMP-gcp/src CMP-gcp/scripts --exit-nonzero-on-find`.

## Unverified (checked during implementation)
- Whether goccy supports `SAFE.PARSE_JSON`, `QUALIFY`, `BIGNUMERIC` and `ARRAY_AGG ... LIMIT` → L05 probe.
- Whether `WriteToBigQuery` works against the emulator. Assumed no, hence the DoFn.
- Whether Prism runs Python `ReadFromPubSub`. Assumed no.
- The exact metadata columns a BigQuery subscription writes.
