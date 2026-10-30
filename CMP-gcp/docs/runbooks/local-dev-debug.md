# Runbook — CMP-gcp local dev & debug

Scope: the `local` profile only. Cloud runbooks live in [`../../deploy/`](../../deploy/README.md). The recipes named here are specified in the [stories](../epics.md) and do not exist until each story is done.

## Happy path
```bash
just discover                 # read-only; pick reuse / host / compose (story 1.1)
just sync && just test        # unit + TestStream, offline (1.2, 1.3, 3.2)
just up                       # emulators; idempotent; writes .tmp/emulators.env (2.1)
just sql-apply                # templates → emulator; gaps → docs/emulator-gaps.md (2.2)
just it                       # FX on both paths + idempotent rerun (4.1)
just fault-all                # F1 F2 F3 F5 F7 F10 → .tmp/evidence/ (4.2)
just down                     # stops project-owned containers only; never -v
```
Shell setup for ad-hoc tools: `set -a; . .tmp/emulators.env; set +a`.

## Failure modes
| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| <a id="empty-beam"></a>Raw table full, `trades_1m_beam` empty | watermark never advanced: no heartbeat, or wrong `timestamp_attribute` | `just debug-pubsub` → last message has `kind=heartbeat` and `event_time_ms` past the window end + lateness; Beam log shows the timestamp attribute | re-run `produce` (it emits the heartbeat); check that the publisher sets the `event_time_ms` attribute ([ADR-0003](../adr/0003-dedup-and-late-data.md)) |
| Late pane shows only the late trades | DISCARDING accumulation crept back | `tests/beam` case 3 fails | restore `ACCUMULATING` ([AD-4](../architecture.md#ad-4--late-data-accumulates-sink-is-append-only-panes)) |
| `trades_raw` empty, Pub/Sub has messages | shim not running, or BigQuery subscription expected to deliver (it never does on the emulator) | `pgrep -f bq_sub_shim`; `just debug-pubsub` | `just shim` ([ADR-0004](../adr/0004-bq-subscription-shim.md)) |
| `NotFound: topic` after a restart | Pub/Sub emulator state is memory-only | `curl $PUBSUB_EMULATOR_HOST/v1/projects/<p>/topics` | `just up` (re-creates topics and subs idempotently) |
| Client hits real GCP / auth error | `PUBSUB_EMULATOR_HOST` / `BIGQUERY_EMULATOR_HOST` not exported | `env \| grep EMULATOR_HOST` | source `.tmp/emulators.env`; scripts must refuse to run without it in the local profile |
| `ValueError: missing config key …` | strict config, by design | the message names the key and file | fill `config/config.yaml` / `.env.*`; **never** add a default in code |
| SQL fails only on the emulator | goccy function gap | `docs/emulator-gaps.md` | mark the query `skip_on_emulator`; do not edit the SQL ([ADR-0001](../adr/0001-bigquery-emulator-goccy.md)) |
| Beam behaves differently after a Beam upgrade | the effective runner changed (Prism vs BundleBased) | first log line of `beam_run` | re-pin in `uv.lock`; record it in [ADR-0002](../adr/0002-directrunner-not-prism.md) |
| Port already in use on `just up` | another project's emulator / container | `just discover` (listeners table) | reuse it if compatible, else change the port **in config**; never stop the other container |
| `docker` errors inside an agent | sandbox blocks the Docker socket | error mentions socket / permission | run with the approved sandbox bypass (the user can manage this with `/sandbox`) |
| Pub/Sub emulator won't start on host | missing Java 17 or the `pubsub-emulator` component | `java -version`; `gcloud components list` | install the component once (network), or use the compose fallback |
| Bars differ between SQL and Beam | lateness drop (expected beyond `allowed_lateness_s`) or a dedup tie-break mismatch | reconciliation view (story 4.2) | beyond lateness: expected, record it as evidence; otherwise compare `event_id` sets |
| Poison message crashes the pipeline | validation outside the tagged-output `try` | `tests/beam` case 5 | route it to the `invalid` output; quarantine row |
| `just it` hangs | the assertion waits forever | config `assert.timeout_s` | timeout must come from config; check the shim and Beam are alive |

## Debug recipes (story 3.3)
- `just debug-pubsub` — topics, subs, peek without ack.
- `just debug-bq "<sql>"` — query the emulator through the same client.
- `just debug-beam` — one worker, DEBUG logs, a tap after each stage.

## Evidence
`.tmp/evidence/<id>-<ts>.md` (gitignored), using the [workbook-05](../../../crypto-market-pulse-chatgpt/project/docs/workbooks/05_fault_injection_and_evidence.md) template. PASS requires expected and actual side by side.
