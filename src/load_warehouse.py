from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from src.config import WAREHOUSE_DIR


def load_tables(tables: dict[str, pd.DataFrame], warehouse_url: str) -> None:
    if warehouse_url.startswith("sqlite:///"):
        sqlite_path = Path(warehouse_url.replace("sqlite:///", ""))
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_engine(warehouse_url)
    with engine.begin() as connection:
        for table_name, df in tables.items():
            df.to_sql(table_name, connection, if_exists="replace", index=False)

