from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from modules.dashboard import render_app


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database" / "pios.db"


TABLES = {
    "planning_report.xlsx": "planning_report",
    "procurement_report.xlsx": "procurement_report",
    "store_inventory.xlsx": "store_inventory",
    "contracts_report.xlsx": "contracts_report",
    "quality_report.xlsx": "quality_report",
    "risk_register.xlsx": "risk_register",
    "milestone_register.xlsx": "milestone_register",
}


def bootstrap_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        return
    with sqlite3.connect(DB_PATH) as conn:
        for filename, table in TABLES.items():
            source = DATA_DIR / filename
            if not source.exists():
                raise FileNotFoundError(f"Missing required data file: {source}")
            df = pd.read_excel(source)
            df.to_sql(table, conn, index=False, if_exists="replace")


if __name__ == "__main__":
    bootstrap_database()
    render_app(DB_PATH)
