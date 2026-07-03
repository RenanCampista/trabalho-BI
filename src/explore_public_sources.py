from __future__ import annotations

import argparse

import pandas as pd

from src.config import PROCESSED_DIR, PipelineConfig
from src.sources_public import (
    download_cvm_fund_reports,
    download_cvm_registry,
    fetch_macro_data,
    fetch_market_prices,
    load_cvm_registry,
    load_cvm_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera um resumo exploratorio das fontes publicas.")
    parser.add_argument("--start-year", type=int, default=2023)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()

    config = PipelineConfig(start_year=args.start_year, end_year=args.end_year)
    start_date = f"{config.start_year}-01-01"
    end_date = f"{config.end_year}-12-31"

    reports = load_cvm_reports(download_cvm_fund_reports(config.start_year, config.end_year))
    registry = load_cvm_registry(download_cvm_registry())
    macro = fetch_macro_data(start_date, end_date)
    market = fetch_market_prices(start_date, f"{config.end_year + 1}-01-01")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report_path = PROCESSED_DIR / "public_sources_profile.md"
    report_path.write_text(
        "\n".join(
            [
                "# Perfil das Fontes Publicas",
                "",
                "## CVM - informes diarios de fundos",
                f"- Linhas: {len(reports):,}",
                f"- Fundos distintos: {reports['CNPJ_FUNDO'].nunique():,}",
                f"- Periodo: {reports['DT_COMPTC'].min().date()} a {reports['DT_COMPTC'].max().date()}",
                f"- Colunas: {', '.join(reports.columns)}",
                "",
                "## CVM - cadastro de fundos",
                f"- Linhas: {len(registry):,}",
                f"- Colunas principais: {', '.join(registry.columns[:15])}",
                "",
                "## Banco Central SGS",
                f"- Linhas: {len(macro):,}",
                f"- Periodo: {macro['date'].min().date()} a {macro['date'].max().date()}",
                "",
                "## Mercado - yfinance",
                f"- Linhas: {len(market):,}",
                f"- Tickers: {', '.join(sorted(market['ticker'].unique()))}",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Perfil salvo em {report_path}")


if __name__ == "__main__":
    main()

