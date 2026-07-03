from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR


def build_date_dimension(start_date: str, end_date: str) -> pd.DataFrame:
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


def transform_internal(outputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    customers = outputs["internal_customers"].copy()
    funds = outputs["internal_funds"].copy()
    transactions = outputs["internal_transactions"].copy()

    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"])
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
        ["customer_id", "customer_name", "investor_profile", "city", "state", "birth_date", "signup_date"]
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


def transform_cvm_reports(cvm_reports: pd.DataFrame, registry: pd.DataFrame | None = None) -> pd.DataFrame:
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
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["daily_net_flow"] = df["daily_application"].fillna(0) - df["daily_redemption"].fillna(0)
    df = df.sort_values(["fund_cnpj", "date"])
    df["daily_return"] = df.groupby("fund_cnpj")["share_value"].pct_change()

    monthly = (
        df.groupby(["fund_cnpj", "month_start"], as_index=False)
        .agg(
            net_worth=("net_worth", "last"),
            monthly_application=("daily_application", "sum"),
            monthly_redemption=("daily_redemption", "sum"),
            monthly_net_flow=("daily_net_flow", "sum"),
            quota_holders=("quota_holders", "last"),
            monthly_return=("daily_return", lambda s: (1 + s.dropna()).prod() - 1 if len(s.dropna()) else np.nan),
            volatility=("daily_return", "std"),
        )
    )

    if registry is not None and "CNPJ_FUNDO" in registry.columns:
        names = registry.rename(columns={"CNPJ_FUNDO": "fund_cnpj", "DENOM_SOCIAL": "public_fund_name"})
        monthly = monthly.merge(names[["fund_cnpj", "public_fund_name"]], on="fund_cnpj", how="left")
    return monthly


def transform_macro(macro: pd.DataFrame) -> pd.DataFrame:
    df = macro.copy()
    monthly = (
        df.groupby("month", as_index=False)
        .agg(
            selic_monthly_pct=("selic_daily_pct", "sum"),
            ipca_monthly_pct=("ipca_monthly_pct", "last"),
        )
        .rename(columns={"month": "month_start"})
    )
    return monthly


def transform_market(market: pd.DataFrame) -> pd.DataFrame:
    df = market.sort_values(["ticker", "date"]).copy()
    df["daily_return"] = df.groupby("ticker")["close"].pct_change()
    return (
        df.groupby(["ticker", "month"], as_index=False)
        .agg(
            month_close=("close", "last"),
            monthly_return=("daily_return", lambda s: (1 + s.dropna()).prod() - 1 if len(s.dropna()) else np.nan),
            volatility=("daily_return", "std"),
        )
        .rename(columns={"month": "month_start"})
    )


def persist_processed(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)

