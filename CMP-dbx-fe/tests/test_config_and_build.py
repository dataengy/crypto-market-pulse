from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from cmp.kafka import kafka_connection, producer_config, spark_kafka_options
from cmp.settings import env, get, load_config
from cmp.sql_models import model_sql

ROOT = Path(__file__).resolve().parents[1]
CFG = load_config(ROOT)
SECRETS = {"KAFKA_BOOTSTRAP": "pkc-x.confluent.cloud:9092", "KAFKA_API_KEY": "key", "KAFKA_API_SECRET": "s3cr3t"}


def test_strict_config_and_env(monkeypatch):
    with pytest.raises(ValueError, match="kafka.nope"):
        get(CFG, "kafka.nope")
    monkeypatch.delenv("CMP_NOT_SET", raising=False)
    with pytest.raises(ValueError, match="CMP_NOT_SET"):
        env("CMP_NOT_SET")


def test_local_kafka_is_plaintext():
    conn = kafka_connection(CFG, "local", lambda k: pytest.fail(f"local must not look up {k}"))
    opts = spark_kafka_options(conn, "t", "earliest", "M")
    assert opts["kafka.security.protocol"] == "PLAINTEXT" and "kafka.sasl.jaas.config" not in opts


def test_cloud_kafka_uses_lookup_for_creds():
    conn = kafka_connection(CFG, "cloud", SECRETS.__getitem__)
    assert producer_config(conn, "c")["sasl.username"] == "key"
    jaas = spark_kafka_options(conn, "t", "earliest", get(CFG, "kafka.jaas_login_module.databricks"))
    assert jaas["kafka.sasl.jaas.config"].startswith("kafkashaded.")
    assert 'password="s3cr3t";' in jaas["kafka.sasl.jaas.config"]
    with pytest.raises(ValueError):
        spark_kafka_options({**conn, "password": 'a"b'}, "t", "earliest", "M")


def test_model_placeholder_rules():
    assert "FROM src" in model_sql("30_1m", "src")
    with pytest.raises(ValueError):
        model_sql("30_1m", "{{source}}")


def test_generated_files_are_in_sync():
    spec = spec_from_file_location("cmp_build", ROOT / "scripts/build.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    for rel, content in module.generated_files().items():
        assert (ROOT / rel).read_text(encoding="utf-8") == content, f"{rel} is stale: run `just build`"
