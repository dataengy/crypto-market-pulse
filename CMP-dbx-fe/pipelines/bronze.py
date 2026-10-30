# Lakeflow pipeline source: cloud Kafka → trades_bronze (streaming table).
# Shares cmp.* with scripts/local_spark.py; `spark` and `dbutils` are provided by the pipeline runtime.
import sys
from pathlib import Path

from pyspark import pipelines as dp

ROOT = Path(spark.conf.get("cmp.root"))  # noqa: F821
sys.path.insert(0, str(ROOT / "src"))
from cmp.bronze import parse_trades
from cmp.kafka import kafka_connection, spark_kafka_options
from cmp.settings import get, load_config

CFG = load_config(ROOT)
SCOPE = spark.conf.get("cmp.secret_scope")  # noqa: F821


@dp.table(name="trades_bronze", comment="Parsed Kafka trades, append-only (dedup happens downstream)")
def trades_bronze():
    conn = kafka_connection(CFG, "cloud", lambda key: dbutils.secrets.get(SCOPE, key.lower()))  # noqa: F821
    options = spark_kafka_options(conn, get(CFG, "kafka.topic"), get(CFG, "kafka.starting_offsets"),
                                  get(CFG, "kafka.jaas_login_module.databricks"))
    return parse_trades(spark.readStream.format("kafka").options(**options).load())  # noqa: F821
