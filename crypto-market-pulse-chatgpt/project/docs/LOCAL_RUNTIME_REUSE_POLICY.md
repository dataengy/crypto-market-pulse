# Local runtime discovery and reuse policy (mandatory before setup)

**Scope:** any local ClickHouse, Redpanda/Kafka, Spark/PySpark, PostgreSQL, MiniLake, Airbyte, DuckDB, Beam, Pub/Sub Emulator, and supporting tools (Docker/Colima, Java, Python, gcloud, just, terraform, etc.). This is an agent implementation requirement, not a claim that these services exist on the operator's machine.

## Selection priority (strict descending order)

1. **Existing host/OS installations**: executables on `PATH`, macOS applications and binaries under `~/.apps/` and `~/.app/` (including nested `bin/` and `.app/Contents/MacOS/`), plus standard package-manager locations if already on `PATH`. Use a suitable version if accessible and safe to isolate.
2. **Existing Docker/Colima containers and images**: running or stopped containers, including pre-existing Docker Compose projects; inspect active Docker context and Colima profiles. Reuse a *compatible* endpoint or start an *existing* stopped container only with permission and non-destructive impact assessment. An image alone is not a service; reuse an image if a new container is really needed.
3. **New local deployment only if no compatible safe resource exists**: add a new container or install a missing package; isolate names, ports, networks, volumes, data and Kafka topics. Pin/test versions and record exactly why existing services could not be reused.

**Never** interpret discovery as consent to modify or stop shared services. Non-destructive and read-only by default; if existing DB/topic/volume belongs to another project, seek consent or create a separate logical DB/topic/consumer group, and never mutate somebody else's schemas. Reuse means connect to an existing installation/service **without altering its shared configuration**.

## Required preflight and inventory

Run from the project's root on the developer's Mac **before** `pip install`, Docker pull, `docker compose up`, image build or package-manager install:

```bash
python3 scripts/discover_local_runtime.py --markdown
python3 scripts/discover_local_runtime.py --json > /tmp/weather-dfe-local-runtime.json
# Confirm manually where used:
command -v clickhouse rpk spark-submit pyspark psql minilake airbyte gcloud docker colima java python3 || true
ls -la "$HOME/.apps" "$HOME/.app" 2>/dev/null || true
docker context ls 2>/dev/null || true
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
docker compose ls --all 2>/dev/null || true
colima list 2>/dev/null || true
```

The discovery script executes only read-only inspection commands and does not install/start/stop anything. It reports names, binaries and container images, which can include private metadata; **do not commit inventory output to Git or publish container names/paths containing secrets**. It does not verify protocol compatibility by itself.

Capture a summary in the local handoff report:

| Service | Host installation path/version | Existing container/context/endpoint | Selected option | Compatibility check | Reason | Owner/cleanup scope |
|---|---|---|---|---|---|---|
| ClickHouse | ... | ... | ... | `SELECT version()` using safe credentials | ... | ... |
| Redpanda/Kafka | ... | ... | ... | metadata / read-only cluster check | ... | ... |
| Spark | ... | ... | ... | `spark-submit --version`, compatible Java/Python | ... | ... |
| PostgreSQL | ... | ... | ... | `SHOW server_version` on test DB | ... | ... |
| MiniLake | ... | ... | ... | localhost `/ready`, SDK smoke isolated | ... | ... |
| Airbyte | ... | ... | ... | service version/API; no sync without consent | ... | ... |
| GCP emulator/Beam | ... | ... | ... | client/runner sanity tests | ... | ... |

Prioritize minimal setup. **Do not start PostgreSQL or Airbyte simply because they appear in the inventory**; neither is a required dependency for the initial ClickHouse or GCP MVP. Spark and MiniLake are used in their own Databricks debug lane only.

## Docker/Colima usage rules

- Determine active Docker context with `docker context show` and compare with `colima list`. Docker CLI connected to Colima is already sufficient; **do not start Docker Desktop or Colima blindly**.
- List containers on the active context and (if needed) other *already-running* contexts without changing their global default selection; use `docker --context NAME ...` per command. Never `docker context use` as a background side effect.
- Check published ports with `docker port NAME`, service health logs and protocol reachability. Kafka bootstrap listener must be reachable from the selected client network (host vs container), and advertised broker addresses must match the network.
- Distinguish a running compatible service, a stopped reusable container and a reusable image. Do not `docker start` a stopped container or alter network settings without permission.
- For project-owned containers, label with `com.weather_dfe.owner=weather_dfe`; allocate project-specific Compose name, dedicated DB names, topics, consumer groups and ephemeral test paths. For reused services, record `external` or `managed_by_other_project`; do not run destructive cleanup against them.
- **Never run** `docker compose down -v`, `docker system prune`, forced removal, volume removal, blanket stopping, or destructive migrations on existing shared services. Teardown only explicitly project-owned newly created resources; require explicit approval for destructive actions.
- A `just *-down` target must be a no-op for externally reused containers and must never delete their data.
- For PR CI on clean runners, use isolated fresh services; local-laptop reuse policy does **not** bypass hermetic CI.

## Acceptance checks

1. `discover_local_runtime.py` exits successfully even when Docker/Colima or search directories are absent.
2. Its inventory is **read-only**, paths contain no secret file content or environment-variable dumps.
3. Local setup reports the chosen runtime for every required dependency and checks version/compatibility.
4. Running setup twice does not create duplicate services or destroy unrelated resources (idempotent).
5. Stopping the demo leaves all externally reused services, databases and volumes untouched.
6. On reuse failure, operator sees explicit reason and a non-destructive fallback plan; no silent reinstall.
