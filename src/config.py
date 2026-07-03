from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERNAL_DIR = DATA_DIR / "internal"
PROCESSED_DIR = DATA_DIR / "processed"
WAREHOUSE_DIR = ROOT_DIR / "warehouse"
DEFAULT_WAREHOUSE_URL = f"sqlite:///{(WAREHOUSE_DIR / 'bi_fundos.sqlite').as_posix()}"


@dataclass(frozen=True)
class PipelineConfig:
    start_year: int = 2023
    end_year: int = 2025
    seed: int = 20261
    n_customers: int = 900
    n_accounts: int = 1100
    n_transactions: int = 14000
    warehouse_url: str = DEFAULT_WAREHOUSE_URL


SELECTED_FUNDS = [
    {
        "fund_key": "RF_CONSERVADOR",
        "fund_name": "Fundo Renda Fixa Conservador",
        "fund_type": "Renda Fixa",
        "risk_bucket": "Baixo",
    },
    {
        "fund_key": "MULTI_MACRO",
        "fund_name": "Fundo Multimercado Macro",
        "fund_type": "Multimercado",
        "risk_bucket": "Medio",
    },
    {
        "fund_key": "ACOES_BRASIL",
        "fund_name": "Fundo Acoes Brasil",
        "fund_type": "Acoes",
        "risk_bucket": "Alto",
    },
    {
        "fund_key": "IMOB_FII",
        "fund_name": "Fundo Imobiliario BCRI11",
        "fund_type": "FII",
        "risk_bucket": "Medio-alto",
        "ticker": "BCRI11.SA",
    },
]
