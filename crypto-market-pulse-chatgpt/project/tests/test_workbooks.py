"""Learning artifacts must remain in the complete reproducible package."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documentation_and_labs_present():
    files = [
        "docs/RUN_AND_DEBUG_GUIDE.md",
        "docs/OPERATOR_MANUAL.md",
        "docs/БЫСТРЫЙ_СТАРТ_RU.md",
        "docs/workbooks/00_environment_inventory.md",
        "docs/workbooks/01_offline_market_math.md",
        "docs/workbooks/02_clickhouse_redpanda.md",
        "docs/workbooks/03_spark_checkpoint.md",
        "docs/workbooks/04_beam_pubsub.md",
        "docs/workbooks/05_fault_injection_and_evidence.md",
    ]
    for file in files:
        assert (ROOT / file).is_file(), file
        assert len((ROOT / file).read_text(encoding="utf-8")) > 200, file


def test_jupyter_workbooks_have_valid_notebook_structure():
    for name in ("01_event_time_ohlcv.ipynb", "02_beam_event_time.ipynb"):
        data = json.loads((ROOT / "notebooks/workbooks" / name).read_text())
        assert data["nbformat"] == 4
        assert sum(c["cell_type"] == "code" for c in data["cells"]) >= 2
        assert all(c["cell_type"] in ("markdown", "code") for c in data["cells"])
