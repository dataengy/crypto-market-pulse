"""End-to-end local loop: fixture → Redpanda → Spark (availableNow) → Delta marts. Needs `just up`."""
import uuid
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from cmp.kafka import kafka_connection, producer_config, spark_kafka_options
from cmp.publish import KafkaPublisher
from cmp.settings import get, load_config

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


def load_script(name: str):
    spec = spec_from_file_location(f"cmp_{name}", ROOT / f"scripts/{name}.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_through_redpanda_is_exact_and_idempotent(tmp_path):
    cfg = load_config(ROOT)
    local, produce = load_script("local_spark"), load_script("produce")
    topic = f"{get(cfg, 'kafka.topic')}.it-{uuid.uuid4().hex[:8]}"  # isolated from live data
    conn = kafka_connection(cfg, "local", lambda k: pytest.fail(f"local profile looked up {k}"))

    def publish_fixture() -> None:
        pub = KafkaPublisher(producer_config(conn, get(cfg, "kafka.client_id")), topic,
                             get(cfg, "kafka.flush_timeout_s"))
        produce.replay(ROOT / "tests/fixtures/trades.jsonl", pub, None)
        pub.close()

    spark = local.spark_session(cfg)
    options = spark_kafka_options(conn, topic, "earliest", get(cfg, "kafka.jaas_login_module.oss"))
    count = lambda name: spark.sql(f"SELECT COUNT(*) FROM {local.table(tmp_path, name)}").first()[0]

    publish_fixture()
    local.run(spark, options, tmp_path, follow_interval=None)
    assert count("trades_bronze") == 8
    local.run(spark, options, tmp_path, follow_interval=None)        # restart, nothing new: no double read
    assert count("trades_bronze") == 8
    publish_fixture()                                                 # producer replay: bronze grows, marts don't
    local.run(spark, options, tmp_path, follow_interval=None)
    assert count("trades_bronze") == 16 and count("trades_dedup") == 7

    bar = spark.sql(f"SELECT * FROM {local.table(tmp_path, 'trades_1m')} WHERE symbol = 'BTCUSDT' "
                    "ORDER BY window_start LIMIT 1").first()
    assert (bar.trade_count, bar.volume) == (4, Decimal("0.45"))
    assert (bar.open_price, bar.high_price, bar.close_price) == (Decimal(70000), Decimal(70010),
                                                                 Decimal(69990))
