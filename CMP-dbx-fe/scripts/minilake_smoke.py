#!/usr/bin/env python3
"""MiniLake smoke: real Databricks SDK against the local emulator — UC objects, SQL statements, models.

MiniLake runs SQL with DuckDB semantics and has no Lakeflow, Delta or Kafka, so this checks the SDK/UC
code path and model portability, not streaming. Models that hit a dialect gap are reported, not forked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cmp.settings import get, load_config
from cmp.sql_models import model_sql, valid_trade_predicate

COLUMNS = (("schema_version", "INT"), ("event_id", "STRING"), ("source", "STRING"), ("category", "STRING"),
           ("symbol", "STRING"), ("trade_id", "STRING"), ("event_time_ms", "BIGINT"),
           ("received_at_ms", "BIGINT"), ("side", "STRING"), ("price", "DECIMAL(38,12)"),
           ("quantity", "DECIMAL(38,12)"), ("kafka_partition", "INT"), ("kafka_offset", "BIGINT"),
           ("kafka_timestamp", "TIMESTAMP"))


def sql_literal(value) -> str:
    return str(value) if isinstance(value, int) else "'" + str(value).replace("'", "''") + "'"


def main() -> int:
    from databricks.sdk import WorkspaceClient

    cfg = get(load_config(ROOT), "minilake")
    if not cfg["host"].startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("MiniLake smoke runs only against localhost (it has no auth)")
    w = WorkspaceClient(host=cfg["host"], token=cfg["token"])
    catalog, schema = cfg["catalog"], cfg["schema"]
    for create in (lambda: w.catalogs.create(name=catalog),
                   lambda: w.schemas.create(name=schema, catalog_name=catalog)):
        try:
            create()
        except Exception as exc:  # idempotent rerun
            if "already exists" not in str(exc).lower():
                raise
    warehouse = w.warehouses.create(name=cfg["warehouse_name"], cluster_size=cfg["warehouse_size"])
    fq = lambda name: f"{catalog}.{schema}.{name}"

    def execute(sql: str):
        res = w.statement_execution.execute_statement(warehouse_id=warehouse.id, statement=sql,
                                                      wait_timeout=cfg["wait_timeout"])
        state = str(res.status.state).split(".")[-1] if res.status else "UNKNOWN"
        if state != "SUCCEEDED":
            raise RuntimeError(f"{state}: {res.status}")
        return res.result.data_array if res.result else []

    execute(f"DROP TABLE IF EXISTS {fq('trades_bronze')}")
    execute(f"CREATE TABLE {fq('trades_bronze')} ({', '.join(f'{n} {t}' for n, t in COLUMNS)})")
    rows = []
    for offset, line in enumerate(x for x in (ROOT / "tests/fixtures/trades.jsonl").read_text().splitlines() if x):
        e = json.loads(line)
        values = [e[n] for n, _ in COLUMNS[:11]] + [0, offset]
        rows.append("(" + ", ".join(sql_literal(v) for v in values) + ", CURRENT_TIMESTAMP)")
    execute(f"INSERT INTO {fq('trades_bronze')} VALUES " + ", ".join(rows))

    steps = [("trades_silver", f"SELECT * FROM ({model_sql('10_silver', fq('trades_bronze'))}) AS s "
                               f"WHERE {valid_trade_predicate()}"),
             ("trades_dedup", model_sql("20_dedup", fq("trades_silver"))),
             ("trades_1m", model_sql("30_1m", fq("trades_dedup"))),
             ("trades_latest", model_sql("40_latest", fq("trades_dedup")))]
    gaps = []
    for name, sql in steps:
        try:
            execute(f"CREATE OR REPLACE VIEW {fq(name)} AS {sql}")
            print(f"PASS {name}: {execute(f'SELECT COUNT(*) FROM {fq(name)}')}")
        except Exception as exc:
            gaps.append(name)
            print(f"DIALECT GAP {name}: {str(exc)[:300]}")
    dedup = execute(f"SELECT COUNT(*) FROM {fq('trades_dedup')}") if "trades_dedup" not in gaps else None
    assert dedup and int(dedup[0][0]) == 7, f"dedup must keep 7 distinct trades, got {dedup}"
    print(f"MiniLake smoke PASS (SDK + UC + silver/dedup); dialect gaps: {gaps or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
