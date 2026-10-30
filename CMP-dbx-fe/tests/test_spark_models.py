"""Spark + Delta check of bronze parsing and the shared SQL models, without Kafka (fake Kafka rows)."""
from datetime import UTC, datetime
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/trades.jsonl"
pytestmark = pytest.mark.spark


def load_local_spark():
    spec = spec_from_file_location("cmp_local_spark", ROOT / "scripts/local_spark.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def spark():
    from cmp.settings import load_config
    session = load_local_spark().spark_session(load_config(ROOT))
    yield session
    session.stop()


def write_bronze(spark, lake: Path, lines: list[str]) -> None:
    from cmp.bronze import parse_trades
    now = datetime.now(UTC)
    kafka_like = spark.createDataFrame(
        [(line.encode(), 0, i, now) for i, line in enumerate(lines)],
        "value BINARY, partition INT, offset BIGINT, timestamp TIMESTAMP")
    parse_trades(kafka_like).write.format("delta").mode("append").save(str(lake / "trades_bronze"))


def test_models_match_reference_and_dedup(spark, tmp_path):
    local = load_local_spark()
    lines = [x for x in FIXTURE.read_text().splitlines() if x.strip()]
    write_bronze(spark, tmp_path, lines + ["not json"])  # malformed row must be dropped in silver
    local.build_models(spark, tmp_path)
    write_bronze(spark, tmp_path, lines)                  # full replay must not change the marts
    local.build_models(spark, tmp_path)

    t = lambda name: local.table(tmp_path, name)
    assert spark.sql(f"SELECT COUNT(*) FROM {t('trades_bronze')}").first()[0] == 2 * len(lines) + 1
    assert spark.sql(f"SELECT COUNT(*) FROM {t('trades_dedup')}").first()[0] == 7
    bar = spark.sql(f"SELECT * FROM {t('trades_1m')} WHERE symbol = 'BTCUSDT' "
                    "ORDER BY window_start LIMIT 1").first()
    assert bar.trade_count == 4
    assert (bar.open_price, bar.high_price, bar.close_price) == (Decimal(70000), Decimal(70010),
                                                                 Decimal(69990))
    assert bar.volume == Decimal("0.45")
    latest = {r.symbol: r for r in spark.sql(f"SELECT * FROM {t('trades_latest')}").collect()}
    assert latest["ETHUSDT"].last_price == Decimal(3502) and latest["BTCUSDT"].total_trades == 5
