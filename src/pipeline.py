from __future__ import annotations

import argparse

from src.config import PipelineConfig
from src.fake_internal import generate_internal_data
from src.load_warehouse import load_tables
from src.sources_public import (
    download_cvm_fund_reports,
    download_cvm_registry,
    fetch_macro_data,
    fetch_market_prices,
    load_cvm_registry,
    load_cvm_reports,
)
from src.transform import (
    build_date_dimension,
    persist_processed,
    transform_cvm_reports,
    transform_internal,
    transform_macro,
    transform_market,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o pipeline de dados do projeto de BI.")
    parser.add_argument("--start-year", type=int, default=2023)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--warehouse", default=None)
    parser.add_argument("--skip-public", action="store_true")
    args = parser.parse_args()

    config = PipelineConfig(
        start_year=args.start_year,
        end_year=args.end_year,
        warehouse_url=args.warehouse or PipelineConfig().warehouse_url,
    )
    start_date = f"{config.start_year}-01-01"
    end_date = f"{config.end_year + 1}-01-01"

    internal_raw = generate_internal_data(config)
    tables = transform_internal(internal_raw)
    tables["dim_date"] = build_date_dimension(start_date, f"{config.end_year}-12-31")

    if not args.skip_public:
        cvm_paths = download_cvm_fund_reports(config.start_year, config.end_year)
        registry_path = download_cvm_registry()
        cvm_reports = load_cvm_reports(cvm_paths)
        registry = load_cvm_registry(registry_path)
        macro = fetch_macro_data(start_date, f"{config.end_year}-12-31")
        market = fetch_market_prices(start_date, end_date)

        tables["fact_public_fund_monthly"] = transform_cvm_reports(cvm_reports, registry)
        tables["fact_macro_monthly"] = transform_macro(macro)
        tables["fact_market_monthly"] = transform_market(market)

    persist_processed(tables)
    load_tables(tables, config.warehouse_url)
    print(f"Pipeline concluido. Warehouse: {config.warehouse_url}")


if __name__ == "__main__":
    main()

