# Runbook — local dev and debug loop

Spec: [001](../../specs/001-local-kafka-spark-delta/spec.md) · commands: [README › Local loop](../../README.md#local-loop-dev-and-debug-only). Work from `CMP-dbx-fe/`.

## Happy path
1. `just sync && just test`: the unit tests, which include the build-sync check.
2. `uv run pytest -m spark`: Spark + Delta without Kafka. The first run downloads jars.
3. Reuse check: `docker ps --format '{{.Names}} {{.Ports}}' | grep -E '19092|18000'`. If a compatible Redpanda or MiniLake is already running, point `config.yaml: kafka.profiles.local.bootstrap` / `minilake.host` at it and skip step 4.
4. `just up`: `cmp-dbx-redpanda` and `cmp-dbx-minilake`, localhost only, `--wait` on the healthcheck.
5. `just it` (DBX-L05), then `just minilake-smoke` (DBX-L06).
6. To debug by hand: `just produce fixture && just spark --reset`, then `just spark`. Inspect a table with `uv run pyspark` and ``spark.read.format("delta").load(".tmp/lake/trades_1m")``.
7. `just down`. It stops the containers and never removes volumes.

Done when: the BTCUSDT 10:00 bar is `4 / 0.45 / 70000 / 70010 / 69990` and `trades_dedup` = 7.

## Failure modes
### Docker daemon down
Symptom: `just up` fails with `Cannot connect to the Docker daemon`, or Docker Desktop returns `HTTP 500` (this happened once on 2026-10-30, and was resolved by a restart).
1. Run `docker context ls`, then `docker info`, to see which context is active and whether it answers.
2. For Docker Desktop: quit and restart it. If it still fails, use Troubleshoot › Restart.
3. Or use Colima: `colima start`, then `docker context use colima`.
4. In an agent session, the sandbox blocks the Docker socket. Docker commands need an approved sandbox bypass; this is not a daemon fault.

Steps 1 and 2 of the happy path need no Docker, so keep working on them meanwhile.

### Maven jar download (first Spark run)
Symptom: `unresolved dependency` or `Connection refused` while the Spark session starts, or the start hangs.

Cause: `spark.jars.packages` pulls `delta-spark` and `spark-sql-kafka-0-10_2.13:<pyspark version>` from Maven Central into the Ivy cache (`~/.ivy2*`).

Fix:
- Run `uv run pytest -m spark` once with network access. In an agent sandbox, allow `repo1.maven.org`.
- On a VPN or behind a proxy, check that the JVM sees the proxy (`JAVA_TOOL_OPTIONS=-Dhttps.proxyHost=…`).
- A broken cache: delete only the failing module directory in the Ivy cache, then retry.

### Wrong Java
Symptom: `UnsupportedClassVersionError`, or the gateway exits at start. Spark 4.0 needs Java 17: check `java -version`, then set `JAVA_HOME`.

### Stale generated files
Symptom: `test_generated_files_are_in_sync` fails with `<file> is stale: run just build`, or `just verify` shows a git diff in `pipelines/` or `dashboards/`.

Fix: `just build` and commit the regenerated files together with the model change. Never hand-edit `pipelines/*.sql` or `dashboards/*.json` ([ADR-0002](../adr/0002-shared-sql-models-and-build.md)).

### Missing config or env
Symptom: `ValueError: missing config key 'x.y' in config/config.yaml` or `env X is not set: fill …`.

Fix: add the key to the named file (secrets go in `config/.env.secrets`, from `.env.secrets.demo`). Do not add a default in code.

### Port already in use (19092 / 18000)
Another stack owns the port. This is why MiniLake moved from 8000 to 18000. Prefer reusing that service (step 3). Otherwise stop *your own* container. Never remove another project's containers or volumes.

### Bar is wrong or doubled
- A doubled `trades_bronze` count after a rerun with the same topic is expected (producer replay). Check `trades_dedup` = 7 instead.
- Live trades in the fixture minute change the bar. Use `just spark --reset` with a fresh topic: the integration test uses `market.trades.v1.it-<uuid>`.
- MiniLake `DIALECT GAP trades_1m/trades_latest` is expected ([ADR-0004](../adr/0004-minilake-dmux-emulator.md)). Use Spark for the bar.
