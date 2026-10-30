#!/usr/bin/env python3
"""Generate serialized Databricks AI/BI dashboard from a SQL dataset file.

The format is based on the project Weather DFE reference; validate in workspace.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = "market_history"
SQL = ROOT / "sql/databricks/dashboard_history.sql"
OUT = ROOT / "dashboards/market_pulse.lvdash.json"


def line_widget(key: str, y_field: str, title: str, y_type: str = "quantitative") -> dict:
    return {
        "widget": {
            "name": key,
            "queries": [{"name": "main_query", "query": {
                "datasetName": DATASET,
                "fields": [
                    {"name": "window_start", "expression": "`window_start`"},
                    {"name": y_field, "expression": f"`{y_field}`"}
                ],
                "disaggregated": True
            }}],
            "spec": {
                "version": 3,
                "widgetType": "line",
                "encodings": {
                    "x": {"fieldName": "window_start", "scale": {"type": "temporal"}},
                    "y": {"fieldName": y_field, "scale": {"type": y_type}}
                },
                "frame": {"title": title, "showTitle": True}
            }
        }
    }


def build() -> dict:
    layout = []
    for idx, (key, field, title) in enumerate([
        ("close_price_chart", "close_price", "Close price · 1m"),
        ("vwap_chart", "vwap", "VWAP · 1m"),
        ("volume_chart", "volume", "Volume · 1m"),
    ]):
        item = line_widget(key, field, title)
        item["position"] = {"x": 0 if idx == 0 else (6 if idx == 1 else 0),
                            "y": 0 if idx < 2 else 6,
                            "width": 12 if idx == 2 else 6, "height": 6}
        layout.append(item)
    return {
        "datasets": [{"name": DATASET, "displayName": "Market history", "query": SQL.read_text(encoding="utf-8")}],
        "pages": [{"name": "market_page", "displayName": "Crypto Market Pulse", "pageType": "PAGE_TYPE_CANVAS", "layout": layout}]
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
