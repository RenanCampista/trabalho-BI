from __future__ import annotations

import numpy as np
import pandas as pd

MARKET_COMPARISON_COLUMNS = [
    "month_start",
    "bcri11_return",
    "ibovespa_return",
    "bcri11_minus_ibovespa_return",
    "bcri11_index_base_100",
    "ibovespa_index_base_100",
]


def build_dashboard_gold_tables(gold_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Cria data marts gold achatados para consumo pelo dashboard Streamlit."""
    dashboard_tables: dict[str, pd.DataFrame] = {}

    if "fact_public_fund_monthly" in gold_tables:
        dashboard_tables["gold_public_funds_monthly"] = _build_public_funds_monthly(
            gold_tables["fact_public_fund_monthly"]
        )
        dashboard_tables["gold_risk_return"] = _build_risk_return(
            dashboard_tables["gold_public_funds_monthly"]
        )

    if _has_tables(gold_tables, ["fact_transactions", "dim_date", "dim_fund", "dim_customer"]):
        dashboard_tables["gold_internal_flows_monthly"] = _build_internal_flows_monthly(
            gold_tables["fact_transactions"],
            gold_tables["dim_date"],
            gold_tables["dim_fund"],
        )
        dashboard_tables["gold_investor_profile_fund_type"] = _build_investor_profile_fund_type(
            gold_tables["fact_transactions"],
            gold_tables["dim_fund"],
            gold_tables["dim_customer"],
        )
        dashboard_tables["gold_city_investment"] = _build_city_investment(
            gold_tables["fact_transactions"],
            gold_tables["dim_customer"],
        )

    if "fact_market_monthly" in gold_tables:
        dashboard_tables["gold_market_comparison_monthly"] = _build_market_comparison(
            gold_tables["fact_market_monthly"]
        )

    if "fact_macro_monthly" in gold_tables:
        dashboard_tables["gold_macro_funds_monthly"] = _build_macro_funds_monthly(
            gold_tables,
            dashboard_tables,
        )

    return dashboard_tables


def _build_public_funds_monthly(public_funds: pd.DataFrame) -> pd.DataFrame:
    """Monta serie mensal de fundos publicos com retorno acumulado e indice base 100."""
    df = public_funds.copy()
    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df = _filter_named_public_funds(df)
    df = df.sort_values(["fund_cnpj", "month_start"])
    df["monthly_return"] = pd.to_numeric(df["monthly_return"], errors="coerce")
    df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")
    df["return_index_base_100"] = (
        df.groupby("fund_cnpj")["monthly_return"]
        .transform(lambda s: (1 + s.fillna(0)).cumprod() * 100)
        .round(6)
    )
    df["accumulated_return"] = df["return_index_base_100"] / 100 - 1
    return df


def _build_internal_flows_monthly(
    transactions: pd.DataFrame, dates: pd.DataFrame, funds: pd.DataFrame
) -> pd.DataFrame:
    """Agrega aplicacoes, resgates e captacao liquida por mes e tipo de fundo."""
    df = transactions.merge(dates[["date_key", "month_start", "year", "month"]], on="date_key")
    df = df.merge(funds, on="fund_key", how="left")
    return (
        df.groupby(
            ["month_start", "year", "month", "fund_key", "fund_name", "fund_type"], as_index=False
        )
        .agg(
            applications=("application_amount", "sum"),
            redemptions=("redemption_amount", "sum"),
            net_flow_amount=("net_flow_amount", "sum"),
            transaction_count=("transaction_id", "count"),
        )
        .sort_values(["month_start", "fund_type", "fund_name"])
    )


def _build_investor_profile_fund_type(
    transactions: pd.DataFrame, funds: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """Agrega volume aplicado por perfil de investidor e tipo de fundo."""
    df = transactions.merge(funds, on="fund_key", how="left")
    df = df.merge(customers[["customer_id", "investor_profile"]], on="customer_id", how="left")
    return (
        df.groupby(["fund_type", "investor_profile"], as_index=False)
        .agg(
            applications=("application_amount", "sum"),
            redemptions=("redemption_amount", "sum"),
            net_flow_amount=("net_flow_amount", "sum"),
            investor_count=("customer_id", "nunique"),
            transaction_count=("transaction_id", "count"),
        )
        .sort_values(["fund_type", "applications"], ascending=[True, False])
    )


def _build_city_investment(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Agrega volume investido por cidade e UF."""
    df = transactions.merge(
        customers[["customer_id", "city", "state"]], on="customer_id", how="left"
    )
    return (
        df.groupby(["state", "city"], as_index=False)
        .agg(
            applications=("application_amount", "sum"),
            redemptions=("redemption_amount", "sum"),
            net_flow_amount=("net_flow_amount", "sum"),
            investor_count=("customer_id", "nunique"),
            transaction_count=("transaction_id", "count"),
        )
        .sort_values("applications", ascending=False)
    )


def _build_macro_funds_monthly(
    gold_tables: dict[str, pd.DataFrame], dashboard_tables: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Combina Selic, IPCA, captacao de renda fixa e rentabilidade media dos fundos."""
    macro = gold_tables["fact_macro_monthly"].copy()
    macro["month_start"] = pd.to_datetime(macro["month_start"], errors="coerce")

    if "gold_internal_flows_monthly" in dashboard_tables:
        fixed_income = dashboard_tables["gold_internal_flows_monthly"]
        fixed_income = fixed_income[fixed_income["fund_type"].eq("Renda Fixa")]
        fixed_income = fixed_income.groupby("month_start", as_index=False).agg(
            renda_fixa_applications=("applications", "sum"),
            renda_fixa_redemptions=("redemptions", "sum"),
            renda_fixa_net_flow=("net_flow_amount", "sum"),
        )
        macro = macro.merge(fixed_income, on="month_start", how="left")

    if "gold_public_funds_monthly" in dashboard_tables:
        public_returns = (
            dashboard_tables["gold_public_funds_monthly"]
            .groupby("month_start", as_index=False)
            .agg(
                avg_public_fund_return=("monthly_return", "mean"),
                avg_public_fund_volatility=("volatility", "mean"),
                total_public_net_flow=("monthly_net_flow", "sum"),
            )
        )
        macro = macro.merge(public_returns, on="month_start", how="left")

    return macro.sort_values("month_start")


def _build_market_comparison(market: pd.DataFrame) -> pd.DataFrame:
    """Compara BCRI11 e Ibovespa em retorno mensal, volatilidade e indice base 100."""
    df = market.copy()
    if df.empty:
        return pd.DataFrame(columns=MARKET_COMPARISON_COLUMNS)

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df = df.sort_values(["ticker", "month_start"])
    df["return_index_base_100"] = (
        df.groupby("ticker")["monthly_return"]
        .transform(lambda s: (1 + s.fillna(0)).cumprod() * 100)
        .round(6)
    )

    wide = df.pivot(index="month_start", columns="ticker", values="monthly_return").reset_index()
    if "BCRI11.SA" in wide.columns and "^BVSP" in wide.columns:
        wide["bcri11_minus_ibovespa_return"] = wide["BCRI11.SA"] - wide["^BVSP"]
    wide = wide.rename(columns={"BCRI11.SA": "bcri11_return", "^BVSP": "ibovespa_return"})

    index_wide = df.pivot(
        index="month_start", columns="ticker", values="return_index_base_100"
    ).reset_index()
    index_wide = index_wide.rename(
        columns={"BCRI11.SA": "bcri11_index_base_100", "^BVSP": "ibovespa_index_base_100"}
    )
    result = wide.merge(index_wide, on="month_start", how="left")
    for column in MARKET_COMPARISON_COLUMNS:
        if column not in result.columns:
            result[column] = np.nan
    return result[MARKET_COMPARISON_COLUMNS].sort_values("month_start")


def _build_risk_return(public_funds: pd.DataFrame) -> pd.DataFrame:
    """Calcula retorno acumulado, volatilidade media e relacao retorno/risco por fundo."""
    df = public_funds.copy()
    grouped = df.groupby(["fund_cnpj", "public_fund_name"], as_index=False).agg(
        avg_monthly_return=("monthly_return", "mean"),
        accumulated_return=("monthly_return", lambda s: (1 + s.dropna()).prod() - 1),
        avg_daily_volatility=("volatility", "mean"),
        last_net_worth=("net_worth", "last"),
        total_net_flow=("monthly_net_flow", "sum"),
        months_count=("month_start", "nunique"),
    )
    grouped["return_risk_ratio"] = grouped["accumulated_return"] / grouped[
        "avg_daily_volatility"
    ].replace(0, np.nan)
    return grouped.sort_values("return_risk_ratio", ascending=False)


def _filter_named_public_funds(df: pd.DataFrame) -> pd.DataFrame:
    """Remove fundos cujo nome publico esteja ausente ou seja apenas um CNPJ."""
    if "public_fund_name" not in df.columns:
        return df.iloc[0:0].copy()

    names = df["public_fund_name"].astype("string").str.strip()
    cnpjs = df["fund_cnpj"].astype("string").str.strip()
    cnpj_pattern = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
    has_real_name = names.notna() & names.ne("") & names.ne(cnpjs)
    is_not_cnpj = ~names.str.fullmatch(cnpj_pattern, na=False)
    return df[has_real_name & is_not_cnpj].copy()


def _has_tables(tables: dict[str, pd.DataFrame], required: list[str]) -> bool:
    """Verifica se todas as tabelas exigidas estao disponiveis."""
    return all(table_name in tables for table_name in required)
