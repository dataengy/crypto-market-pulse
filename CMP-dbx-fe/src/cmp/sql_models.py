"""Portable SELECT models (sql/models) shared by local Spark, MiniLake and Lakeflow."""
from __future__ import annotations

from .settings import ROOT

MODELS = ROOT / "sql/models"


def model_sql(name: str, source: str) -> str:
    if not source or "{{" in source or "}}" in source:
        raise ValueError(f"invalid model source: {source!r}")
    sql = (MODELS / f"{name}_select.sql").read_text(encoding="utf-8").strip().rstrip(";")
    if sql.count("{{source}}") != 1:
        raise ValueError(f"exactly one {{{{source}}}} placeholder expected in {name}_select.sql")
    return sql.replace("{{source}}", source)


def valid_trade_predicate() -> str:
    """Silver quality rule: Lakeflow EXPECT ... DROP ROW in the cloud, WHERE locally."""
    lines = (MODELS / "valid_trade.sql").read_text(encoding="utf-8").splitlines()
    return "\n".join(x for x in lines if not x.lstrip().startswith("--")).strip()
