from __future__ import annotations

import argparse

from src.config import PipelineConfig
from src.dashboard_marts import build_dashboard_gold_tables
from src.fake_internal import generate_internal_data
from src.load_warehouse import load_tables
from src.sources_public import (
    download_cvm_fund_reports,
    download_cvm_registry,
    fetch_macro_data,
    fetch_market_prices,
    load_cvm_registry,
    load_cvm_reports,
    select_reference_funds,
)
from src.transform import (
    build_date_dimension,
    build_silver_cvm_daily,
    build_silver_cvm_registry,
    build_silver_internal,
    build_silver_macro,
    build_silver_market,
    persist_gold,
    persist_silver,
    transform_cvm_reports,
    transform_internal,
    transform_macro,
    transform_market,
)


def _log(message: str) -> None:
    """Exibe uma mensagem simples de progresso do pipeline."""
    print(f"[pipeline] {message}", flush=True)


def main() -> None:
    """Executa o pipeline completo de dados de bronze para silver e gold."""
    default_config = PipelineConfig()
    parser = argparse.ArgumentParser(description="Executa o pipeline de dados do projeto de BI.")
    parser.add_argument("--start-year", type=int, default=default_config.start_year)
    parser.add_argument("--end-year", type=int, default=default_config.end_year)
    parser.add_argument("--warehouse", default=None)
    parser.add_argument("--skip-public", action="store_true")
    parser.add_argument(
        "--max-public-funds",
        type=int,
        default=default_config.max_public_funds,
        help="Quantidade de fundos CVM carregados por padrao, escolhidos por maior PL.",
    )
    args = parser.parse_args()

    config = PipelineConfig(
        start_year=args.start_year,
        end_year=args.end_year,
        max_public_funds=args.max_public_funds,
        warehouse_url=args.warehouse or default_config.warehouse_url,
    )
    start_date = f"{config.start_year}-01-01"
    end_date = f"{config.end_year + 1}-01-01"

    _log(
        "Iniciando pipeline "
        f"({config.start_year}-{config.end_year}, "
        f"max_public_funds={config.max_public_funds})"
    )
    _log("Gerando fonte bronze interna fake...")
    bronze_internal = generate_internal_data(config)
    _log("Transformando fonte interna para silver...")
    silver_tables = build_silver_internal(bronze_internal)
    _log("Montando dimensoes e fatos gold internos...")
    gold_tables = transform_internal(silver_tables)
    gold_tables["dim_date"] = build_date_dimension(start_date, f"{config.end_year}-12-31")
    _log("Dimensao de datas criada.")

    if not args.skip_public:
        _log("Baixando/reutilizando informes diarios da CVM...")
        cvm_paths = download_cvm_fund_reports(config.start_year, config.end_year)
        _log(f"Arquivos mensais CVM disponiveis: {len(cvm_paths)}")
        _log("Baixando/reutilizando cadastro de fundos da CVM...")
        registry_path = download_cvm_registry()
        _log("Selecionando fundos publicos de referencia por maior PL...")
        selected_funds = select_reference_funds(cvm_paths, config.max_public_funds)
        _log(f"Fundos publicos selecionados: {len(selected_funds)}")
        _log("Lendo informes CVM filtrados...")
        cvm_reports = load_cvm_reports(cvm_paths, fund_cnpjs=selected_funds)
        _log(f"Linhas CVM carregadas apos filtro: {len(cvm_reports):,}")
        _log("Lendo cadastro CVM...")
        registry = load_cvm_registry(registry_path)
        _log("Buscando indicadores macroeconomicos no Banco Central...")
        macro = fetch_macro_data(start_date, f"{config.end_year}-12-31")
        _log("Buscando cotacoes de mercado...")
        market = fetch_market_prices(start_date, end_date)

        _log("Transformando fontes publicas para silver...")
        silver_tables["silver_cvm_fund_daily"] = build_silver_cvm_daily(cvm_reports)
        silver_tables["silver_cvm_registry"] = build_silver_cvm_registry(registry)
        silver_tables["silver_cvm_registry"] = silver_tables["silver_cvm_registry"][
            silver_tables["silver_cvm_registry"]["fund_cnpj"].isin(selected_funds)
        ]
        silver_tables["silver_macro_daily"] = build_silver_macro(macro)
        silver_tables["silver_market_daily"] = build_silver_market(market)

        _log("Agregando fontes publicas para gold...")
        gold_tables["fact_public_fund_monthly"] = transform_cvm_reports(
            silver_tables["silver_cvm_fund_daily"],
            silver_tables["silver_cvm_registry"],
        )
        gold_tables["fact_macro_monthly"] = transform_macro(silver_tables["silver_macro_daily"])
        gold_tables["fact_market_monthly"] = transform_market(silver_tables["silver_market_daily"])
    else:
        _log("Fontes publicas ignoradas por --skip-public.")

    _log("Gerando data marts gold para o dashboard Streamlit...")
    dashboard_gold_tables = build_dashboard_gold_tables(gold_tables)
    gold_tables.update(dashboard_gold_tables)
    _log(f"Tabelas gold de dashboard geradas: {len(dashboard_gold_tables)}")

    _log("Persistindo camada silver em CSV...")
    persist_silver(silver_tables)
    _log("Persistindo camada gold em CSV...")
    persist_gold(gold_tables)
    _log("Carregando tabelas gold no warehouse...")
    load_tables(gold_tables, config.warehouse_url)
    _log(f"Pipeline concluido. Warehouse: {config.warehouse_url}")


if __name__ == "__main__":
    main()
