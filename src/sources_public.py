from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from src.config import RAW_DIR

CVM_INF_DIARIO_URL = (
    "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{year}{month:02d}.zip"
)
CVM_CADASTRO_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
CVM_REPORT_USECOLS = [
    "CNPJ_FUNDO",
    "CNPJ_FUNDO_CLASSE",
    "DT_COMPTC",
    "VL_TOTAL",
    "VL_QUOTA",
    "VL_PATRIM_LIQ",
    "CAPTC_DIA",
    "RESG_DIA",
    "NR_COTST",
]


def _download(url: str, path: Path, timeout: int = 90) -> Path:
    """Baixa um arquivo para a pasta bronze publica, reutilizando-o quando ja existir."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return path
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def download_cvm_fund_reports(start_year: int, end_year: int) -> list[Path]:
    """Baixa arquivos ZIP mensais de informes diarios de fundos da CVM no periodo solicitado."""
    paths: list[Path] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            url = CVM_INF_DIARIO_URL.format(year=year, month=month)
            path = RAW_DIR / "cvm" / f"inf_diario_fi_{year}{month:02d}.zip"
            paths.append(_download(url, path))
    return paths


def download_cvm_registry() -> Path:
    """Baixa o CSV de cadastro de fundos da CVM para a pasta bronze publica."""
    return _download(CVM_CADASTRO_URL, RAW_DIR / "cvm" / "cad_fi.csv")


def select_reference_funds(paths: list[Path], max_funds: int) -> list[str]:
    """Seleciona os maiores fundos do ultimo informe disponivel para limitar uso de memoria."""
    if max_funds <= 0:
        raise ValueError("max_funds deve ser maior que zero para evitar carga integral da CVM.")

    for path in sorted(paths, reverse=True):
        df = _read_cvm_report_file(path)
        if df.empty or "CNPJ_FUNDO" not in df.columns:
            continue
        df = df.dropna(subset=["CNPJ_FUNDO", "VL_PATRIM_LIQ"])
        if df.empty:
            continue
        return (
            df.sort_values("VL_PATRIM_LIQ", ascending=False)["CNPJ_FUNDO"]
            .drop_duplicates()
            .head(max_funds)
            .tolist()
        )
    return []


def load_cvm_reports(paths: list[Path], fund_cnpjs: Iterable[str] | None = None) -> pd.DataFrame:
    """Le informes bronze da CVM usando somente colunas e fundos necessarios."""
    selected_funds = None if fund_cnpjs is None else set(fund_cnpjs)
    frames = []
    for path in paths:
        df = _read_cvm_report_file(path)
        if "CNPJ_FUNDO" not in df.columns:
            continue
        if selected_funds is not None:
            df = df[df["CNPJ_FUNDO"].isin(selected_funds)]
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=CVM_REPORT_USECOLS)
    return pd.concat(frames, ignore_index=True)


def _read_cvm_report_file(path: Path) -> pd.DataFrame:
    """Le um arquivo mensal da CVM com colunas reduzidas e tipos ja padronizados."""
    csv_paths = unzip_if_needed(path)
    frames = [
        pd.read_csv(
            csv_path,
            sep=";",
            encoding="ISO-8859-1",
            decimal=",",
            usecols=lambda col: col in CVM_REPORT_USECOLS,
            low_memory=False,
        )
        for csv_path in csv_paths
    ]
    if not frames:
        return pd.DataFrame(columns=CVM_REPORT_USECOLS)

    df = pd.concat(frames, ignore_index=True)
    if "CNPJ_FUNDO" not in df.columns and "CNPJ_FUNDO_CLASSE" in df.columns:
        df = df.rename(columns={"CNPJ_FUNDO_CLASSE": "CNPJ_FUNDO"})
    if "CNPJ_FUNDO_CLASSE" in df.columns:
        df = df.drop(columns=["CNPJ_FUNDO_CLASSE"])
    if "CNPJ_FUNDO" not in df.columns or "DT_COMPTC" not in df.columns:
        return pd.DataFrame(columns=CVM_REPORT_USECOLS)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"], errors="coerce")
    numeric_cols = ["VL_TOTAL", "VL_QUOTA", "VL_PATRIM_LIQ", "CAPTC_DIA", "RESG_DIA", "NR_COTST"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_cvm_registry(path: Path) -> pd.DataFrame:
    """Le o CSV bronze de cadastro da CVM e interpreta as colunas de data conhecidas."""
    df = pd.read_csv(path, sep=";", encoding="ISO-8859-1", low_memory=False)
    for col in ["DT_REG", "DT_CONST", "DT_CANCEL"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def fetch_bcb_series(code: int, name: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Busca uma serie SGS do Banco Central e normaliza para colunas de data e valor."""
    params = {
        "formato": "json",
        "dataInicial": pd.to_datetime(start_date).strftime("%d/%m/%Y"),
        "dataFinal": pd.to_datetime(end_date).strftime("%d/%m/%Y"),
    }
    response = requests.get(BCB_SGS_URL.format(code=code), params=params, timeout=60)
    response.raise_for_status()
    df = pd.DataFrame(response.json())
    df["date"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df[name] = pd.to_numeric(df["valor"], errors="coerce")
    return df[["date", name]].dropna()


def fetch_macro_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Busca Selic e IPCA no Banco Central e combina as series por data."""
    selic = fetch_bcb_series(11, "selic_daily_pct", start_date, end_date)
    ipca = fetch_bcb_series(433, "ipca_monthly_pct", start_date, end_date)
    macro = pd.merge(selic, ipca, on="date", how="outer").sort_values("date")
    macro["month"] = macro["date"].dt.to_period("M").dt.to_timestamp()
    return macro


def fetch_market_prices(start_date: str, end_date: str) -> pd.DataFrame:
    """Busca precos diarios ajustados de fechamento do BCRI11 e Ibovespa no Yahoo Finance."""
    raw = yf.download(
        tickers=["BCRI11.SA", "^BVSP"],
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        close = (
            raw["Close"].reset_index().melt(id_vars="Date", var_name="ticker", value_name="close")
        )
    else:
        close = raw[["Close"]].rename(columns={"Close": "close"}).reset_index()
        close["ticker"] = "BCRI11.SA"
    close = close.rename(columns={"Date": "date"})
    close["date"] = pd.to_datetime(close["date"]).dt.tz_localize(None)
    close["month"] = close["date"].dt.to_period("M").dt.to_timestamp()
    return close.dropna(subset=["close"])


def unzip_if_needed(path: Path) -> list[Path]:
    """Extrai um arquivo ZIP quando necessario e retorna os caminhos dos CSVs para carga."""
    if path.suffix.lower() != ".zip":
        return [path]
    target_dir = path.with_suffix("")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        archive.extractall(target_dir)
    return list(target_dir.glob("*.csv"))
