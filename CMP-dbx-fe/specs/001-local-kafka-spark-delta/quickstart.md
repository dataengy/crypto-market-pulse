# Quickstart: local loop

The commands are in [README › Local loop](../../README.md#local-loop-dev-and-debug-only). Failure modes are in [runbooks/local-dev-debug.md](../../docs/runbooks/local-dev-debug.md). The minimal proof path:

```bash
just sync && just test && uv run pytest -m spark   # US1, US2, US4: no Docker needed
just up && just it                                   # US3: Kafka E2E (DBX-L05)
just minilake-smoke                                  # US5 (DBX-L06)
just down
```
Expected result: the BTCUSDT 10:00 bar is `4 / 0.45 / 70000 / 70010 / 69990` and `trades_dedup` = 7.
