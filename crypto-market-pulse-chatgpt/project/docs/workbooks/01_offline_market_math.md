# Workbook 1 — Event identity, reordering, OHLCV and VWAP (offline)

**Goal:** understand event-time vs arrival-time and ensure duplicates do not alter market aggregates. No broker, cloud or trading account required.

### Run

```bash
PYTHONPATH=src pytest -q tests/test_domain.py tests/test_preview_marts.py
python scripts/preview_marts.py
python scripts/produce.py --sink stdout --fixture tests/fixtures/trades.jsonl --max-trades 3
```

### Questions and experiments

1. Inspect `tests/fixtures/trades.jsonl`. Which `event_id` occurs twice? Are their `received_at_ms` values different? Check the normalized ID is `bybit:linear:{symbol}:{trade_id}`.
2. Find the earliest and latest `event_time_ms` within BTCUSDT 10:00 UTC. Do not use file ordering to calculate open/close.
3. Independently calculate `VWAP = SUM(price * quantity) / SUM(quantity)` using Python `Decimal`, not `float`.
4. Copy the fixture to `/tmp/cmp-trades-lab.jsonl`. Append the first row a second time, run `python scripts/preview_marts.py --fixture /tmp/cmp-trades-lab.jsonl`. Check whether OHLCV changed and whether `duplicate_count` increased.
5. Swap the order of the first two lines in the copied fixture, rerun preview. Explain why open/close should be unchanged.
6. Modify `price` in a copied event to `"0"`; rerun and observe validation failure. Never modify the committed fixture to simulate a fault.

### Reference check

For the synthetic BTCUSDT `2026-10-30 10:00 UTC` minute: `trade_count=4`, `open=70000.0`, `close=69990.0`, `high=70010.0`, `volume=0.45`, `duplicate_count=1` (before adding extra duplicates). The fixture is not live market data.

**Pass:** correct event-time ordering, stable OHLCV under duplicate replay, `Decimal` precision and explicit invalid-event failure.
