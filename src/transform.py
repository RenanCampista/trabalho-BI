from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import GOLD_DIR, SILVER_DIR


def build_date_dimension(start_date: str, end_date: str) -> pd.DataFrame:
    """Cria a dimensao gold de datas para o periodo de analise configurado."""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    return pd.DataFrame(
        {
            "date_key": dates.strftime("%Y%m%d").astype(int),
            "date": dates,
            "year": dates.year,
            "quarter": dates.quarter,
            "month": dates.month,
            "month_start": dates.to_period("M").to_timestamp(),
            "month_name": dates.strftime("%b"),
        }
    )


def build_silver_internal(outputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Padroniza os dados bronze internos fake em tabelas silver limpas."""
    customers = outputs["internal_customers"].copy()
    accounts = outputs["internal_accounts"].copy()
    funds = outputs["internal_funds"].copy()
    transactions = outputs["internal_transactions"].copy()

    customers["birth_date"] = pd.to_datetime(customers["birth_date"], errors="coerce")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"], errors="coerce")
    accounts["account_open_date"] = pd.to_datetime(accounts["account_open_date"], errors="coerce")
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )
    transactions["amount"] = pd.to_numeric(transactions["amount"], errors="coerce").fillna(0)
    transactions = transactions.dropna(subset=["transaction_date", "fund_key"])

    return {
        "silver_internal_customers": customers,
        "silver_internal_accounts": accounts,
        "silver_internal_funds": funds,
        "silver_internal_transactions": transactions,
    }


def build_silver_cvm_daily(cvm_reports: pd.DataFrame) -> pd.DataFrame:
    """Converte informes diarios brutos da CVM em uma tabela silver diaria limpa."""
    df = cvm_reports.copy()
    df = df.rename(
        columns={
            "CNPJ_FUNDO": "fund_cnpj",
            "DT_COMPTC": "date",
            "VL_TOTAL": "total_assets",
            "VL_QUOTA": "share_value",
            "VL_PATRIM_LIQ": "net_worth",
            "CAPTC_DIA": "daily_application",
            "RESG_DIA": "daily_redemption",
            "NR_COTST": "quota_holders",
        }
    )
    keep = [
        "fund_cnpj",
        "date",
        "total_assets",
        "share_value",
        "net_worth",
        "daily_application",
        "daily_redemption",
        "quota_holders",
    ]
    df = df[[col for col in keep if col in df.columns]].dropna(subset=["fund_cnpj", "date"])
    for col in [
        "total_assets",
        "share_value",
        "net_worth",
        "daily_application",
        "daily_redemption",
        "quota_holders",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["daily_net_flow"] = df["daily_application"].fillna(0) - df["daily_redemption"].fillna(0)
    df = df.sort_values(["fund_cnpj", "date"])
    df["daily_return"] = df.groupby("fund_cnpj")["share_value"].pct_change()
    return df


def build_silver_cvm_registry(registry: pd.DataFrame) -> pd.DataFrame:
    """Seleciona e renomeia atributos do cadastro CVM usados pelo modelo analitico."""
    df = registry.copy().rename(
        columns={
            "CNPJ_FUNDO": "fund_cnpj",
            "DENOM_SOCIAL": "public_fund_name",
            "SIT": "status",
            "CLASSE": "public_fund_class",
            "DT_REG": "registry_date",
            "DT_CONST": "constitution_date",
            "DT_CANCEL": "cancel_date",
        }
    )
    keep = [
        "fund_cnpj",
        "public_fund_name",
        "status",
        "public_fund_class",
        "registry_date",
        "constitution_date",
        "cancel_date",
    ]
    return df[[col for col in keep if col in df.columns]].drop_duplicates("fund_cnpj")


def build_silver_macro(macro: pd.DataFrame) -> pd.DataFrame:
    """Prepara observacoes macroeconomicas diarias e mensais para armazenamento silver."""
    df = macro.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    for col in ["selic_daily_pct", "ipca_monthly_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["date"])


def build_silver_market(market: pd.DataFrame) -> pd.DataFrame:
    """Prepara precos de mercado com retornos diarios para armazenamento silver."""
    df = market.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])
    df["daily_return"] = df.groupby("ticker")["close"].pct_change()
    return df


def transform_internal(silver_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Cria dimensoes gold e fato de transacoes a partir das tabelas silver internas."""
    customers = silver_tables["silver_internal_customers"].copy()
    funds = silver_tables["silver_internal_funds"].copy()
    transactions = silver_tables["silver_internal_transactions"].copy()

    transactions["date_key"] = transactions["transaction_date"].dt.strftime("%Y%m%d").astype(int)
    transactions["application_amount"] = np.where(
        transactions["transaction_type"].eq("Aplicacao"), transactions["amount"], 0.0
    )
    transactions["redemption_amount"] = np.where(
        transactions["transaction_type"].eq("Resgate"), transactions["amount"], 0.0
    )
    transactions["net_flow_amount"] = (
        transactions["application_amount"] - transactions["redemption_amount"]
    )

    dim_customer = customers[
        [
            "customer_id",
            "customer_name",
            "investor_profile",
            "city",
            "state",
            "birth_date",
            "signup_date",
        ]
    ].copy()
    dim_fund = funds[["fund_key", "fund_name", "fund_type", "risk_bucket"]].copy()
    fact_transactions = transactions[
        [
            "transaction_id",
            "date_key",
            "customer_id",
            "account_id",
            "fund_key",
            "transaction_type",
            "amount",
            "application_amount",
            "redemption_amount",
            "net_flow_amount",
        ]
    ].copy()

    return {
        "dim_customer": dim_customer,
        "dim_fund": dim_fund,
        "fact_transactions": fact_transactions,
    }


def transform_cvm_reports(
    silver_cvm_daily: pd.DataFrame, silver_registry: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Agrega dados silver diarios da CVM em um fato gold mensal de fundos."""
    df = silver_cvm_daily.copy()
    monthly = df.groupby(["fund_cnpj", "month_start"], as_index=False).agg(
        net_worth=("net_worth", "last"),
        monthly_application=("daily_application", "sum"),
        monthly_redemption=("daily_redemption", "sum"),
        monthly_net_flow=("daily_net_flow", "sum"),
        quota_holders=("quota_holders", "last"),
        monthly_return=(
            "daily_return",
            lambda s: (1 + s.dropna()).prod() - 1 if len(s.dropna()) else np.nan,
        ),
        volatility=("daily_return", "std"),
    )

    if silver_registry is not None and "fund_cnpj" in silver_registry.columns:
        monthly = monthly.merge(
            silver_registry[["fund_cnpj", "public_fund_name"]], on="fund_cnpj", how="left"
        )
    return _filter_named_public_funds(monthly)


def _filter_named_public_funds(df: pd.DataFrame) -> pd.DataFrame:
    """Remove fundos publicos sem nome real para melhorar o consumo no dashboard."""
    if "public_fund_name" not in df.columns:
        return df.iloc[0:0].copy()

    names = df["public_fund_name"].astype("string").str.strip()
    cnpjs = df["fund_cnpj"].astype("string").str.strip()
    cnpj_pattern = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
    has_real_name = names.notna() & names.ne("") & names.ne(cnpjs)
    is_not_cnpj = ~names.str.fullmatch(cnpj_pattern, na=False)
    return df[has_real_name & is_not_cnpj].copy()


def transform_macro(silver_macro: pd.DataFrame) -> pd.DataFrame:
    """Agrega observacoes macroeconomicas silver em indicadores gold mensais."""
    df = silver_macro.copy()
    return (
        df.groupby("month", as_index=False)
        .agg(
            selic_monthly_pct=("selic_daily_pct", "sum"),
            ipca_monthly_pct=("ipca_monthly_pct", "last"),
        )
        .rename(columns={"month": "month_start"})
    )


def transform_market(silver_market: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados silver diarios de mercado em metricas gold mensais de desempenho."""
    df = silver_market.copy()
    return (
        df.groupby(["ticker", "month"], as_index=False)
        .agg(
            month_close=("close", "last"),
            monthly_return=(
                "daily_return",
                lambda s: (1 + s.dropna()).prod() - 1 if len(s.dropna()) else np.nan,
            ),
            volatility=("daily_return", "std"),
        )
        .rename(columns={"month": "month_start"})
    )


def persist_silver(tables: dict[str, pd.DataFrame]) -> None:
    """Persiste todos os DataFrames silver como arquivos CSV em data/silver."""
    _persist_tables(tables, SILVER_DIR)


def persist_gold(tables: dict[str, pd.DataFrame]) -> None:
    """Persiste todos os DataFrames gold como arquivos CSV em data/gold."""
    _persist_tables(tables, GOLD_DIR)


def persist_processed(tables: dict[str, pd.DataFrame]) -> None:
    """Alias retrocompativel que persiste tabelas analiticas na camada gold."""
    persist_gold(tables)


def _persist_tables(tables: dict[str, pd.DataFrame], target_dir: Path) -> None:
    """Grava DataFrames nomeados como CSV no diretorio alvo da camada medalhao."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(target_dir / f"{name}.csv", index=False)
