# Quickstart: cloud loop

The commands are in [README › Cloud loop](../../README.md#cloud-loop-free-edition). The step-by-step guide with failure branches is [runbooks/dbx-fe-deploy-verify.md](../../docs/runbooks/dbx-fe-deploy-verify.md).

```bash
just dbx-validate && just dbx-secrets && just dbx-deploy && just dbx-probe   # US1 gate
CMP_PROFILE=cloud just produce fixture && just dbx-run                        # US2
just dbx-query "SELECT * FROM workspace.crypto_pulse.trades_1m WHERE symbol='BTCUSDT' ORDER BY window_start LIMIT 1"
```
