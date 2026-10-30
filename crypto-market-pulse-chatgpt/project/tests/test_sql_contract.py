from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_versioned_sql_marts():
    for dialect in ("clickhouse", "bigquery", "databricks"):
        files = list((ROOT / "sql" / dialect).glob("*.sql"))
        text = "\n".join(f.read_text().lower() for f in files)
        for token in ("event_id", "trades_1m", "vwap", "trades_latest"):
            assert token in text, (dialect, token)
        assert "weather" not in text.lower()


def test_fixture_and_compose_valid():
    for line in (ROOT / "tests/fixtures/trades.jsonl").read_text().splitlines():
        assert json.loads(line)["source"] == "bybit"
