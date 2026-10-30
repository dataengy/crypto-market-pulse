# Workbook 0 — Discover and reuse your existing local services

**Target:** Mac with OS installations, `.apps`, `.app`, Docker/Colima. **Runtime:** read-only; no installs/containers should start.

### Commands

```bash
cd /path/to/crypto_market_pulse
python3 scripts/discover_local_runtime.py --markdown
command -v python3 java spark-submit pyspark rpk kcat clickhouse-client docker colima gcloud terraform || true
# Optional, only if installed:
docker context show
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

### Fill in after execution — DO NOT store passwords

| Component | Existing OS binary? path/version | Existing container? context/name/state | Endpoint/port (non-secret) | Reuse? | Permission/owner |
| --- | --- | --- | --- | --- | --- |
| Python/Java | | | | | |
| Redpanda/Kafka | | | | | |
| ClickHouse | | | | | |
| Spark | | | | | |
| Beam/gcloud | | | | | |
| Minilake | | | | | |
| PostgreSQL/Airbyte | | | | | |

**Decision:** choose reuse of existing OS app first, then existing *authorized* container, then isolated new setup. If a service exists but belongs to another project, do not mutate it without permission. A discovered endpoint may point at production: run read-only version checks first.

**Pass condition:** inventory captured and every write target identified before any `docker compose up`, DDL, topic creation, install or download.
