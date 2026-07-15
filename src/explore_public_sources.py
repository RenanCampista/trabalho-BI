from __future__ import annotations

import argparse

from src.config import PROCESSED_DIR, PipelineConfig
from src.sources_public import (
    download_cvm_fund_reports,
    download_cvm_registry,
    fetch_macro_data,
    fetch_market_prices,
    load_cvm_registry,
    load_cvm_reports,
    select_reference_funds,
)


def _log(message: str) -> None:
    """Exibe uma mensagem simples de progresso da exploracao."""
    print(f"[explore] {message}", flush=True)


def main() -> None:
    """Baixa as fontes publicas e grava um relatorio compacto de perfilamento."""
    parser = argparse.ArgumentParser(description="Gera um resumo exploratorio das fontes publicas.")
    parser.add_argument("--start-year", type=int, default=2023)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument(
        "--max-public-funds",
        type=int,
        default=PipelineConfig().max_public_funds,
        help="Quantidade de fundos CVM usados no perfil exploratorio.",
    )
    args = parser.parse_args()

    config = PipelineConfig(
        start_year=args.start_year,
        end_year=args.end_year,
        max_public_funds=args.max_public_funds,
    )
    start_date = f"{config.start_year}-01-01"
    end_date = f"{config.end_year}-12-31"

    _log(
        "Iniciando exploracao publica "
        f"({config.start_year}-{config.end_year}, "
        f"max_public_funds={config.max_public_funds})"
    )
    _log("Baixando/reutilizando informes diarios da CVM...")
    cvm_paths = download_cvm_fund_reports(config.start_year, config.end_year)
    _log(f"Arquivos mensais CVM disponiveis: {len(cvm_paths)}")
    _log("Selecionando fundos de referencia por maior PL...")
    selected_funds = select_reference_funds(cvm_paths, config.max_public_funds)
    _log(f"Fundos selecionados: {len(selected_funds)}")
    _log("Lendo informes CVM filtrados...")
    reports = load_cvm_reports(cvm_paths, fund_cnpjs=selected_funds)
    _log(f"Linhas CVM carregadas apos filtro: {len(reports):,}")
    _log("Baixando/reutilizando cadastro de fundos da CVM...")
    registry = load_cvm_registry(download_cvm_registry())
    _log(f"Linhas no cadastro CVM: {len(registry):,}")
    _log("Buscando series macroeconomicas no Banco Central...")
    macro = fetch_macro_data(start_date, end_date)
    _log(f"Linhas macroeconomicas carregadas: {len(macro):,}")
    _log("Buscando cotacoes de mercado...")
    market = fetch_market_prices(start_date, f"{config.end_year + 1}-01-01")
    _log(f"Linhas de mercado carregadas: {len(market):,}")

    _log("Gravando relatorio de perfilamento...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report_path = PROCESSED_DIR / "public_sources_profile.md"
    report_path.write_text(
        "\n".join(
            [
                "# Perfil das Fontes Publicas",
                "",
                "## CVM - informes diarios de fundos",
                f"- Fundos selecionados por maior PL: {len(selected_funds):,}",
                f"- Linhas carregadas: {len(reports):,}",
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
    _log(f"Perfil salvo em {report_path}")


if __name__ == "__main__":
    main()
