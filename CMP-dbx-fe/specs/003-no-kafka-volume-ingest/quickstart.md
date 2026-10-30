# Quickstart: Volume path (after DBX-A02…A05 are implemented)

```bash
just up && just produce fixture && just ship            # Kafka → .tmp/landing (local target)
just spark --bronze-source volume                       # same bar as the Kafka path
# cloud (bronze_source=volume in the target):
just dbx-deploy && just ship --source fixture && just dbx-run
just dbx-query "SELECT * FROM workspace.crypto_pulse.trades_1m WHERE symbol='BTCUSDT' ORDER BY window_start LIMIT 1"
```
`just ship` and `--bronze-source` do not exist yet. They are delivered by DBX-A03 and DBX-A05. Failure branches: [runbooks/dbx-fe-deploy-verify.md](../../docs/runbooks/dbx-fe-deploy-verify.md#4-gate-failed-kafka-egress-blocked).
