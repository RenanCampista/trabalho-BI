from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from src.config import DEFAULT_WAREHOUSE_URL, GOLD_DIR

DEFAULT_CHART_HEIGHT = 560
RANKING_CHART_HEIGHT = 620
DASHBOARD_TABLES = frozenset(
    {
        "gold_public_funds_monthly",
        "gold_risk_return",
        "gold_internal_flows_monthly",
        "gold_investor_profile_fund_type",
        "gold_city_investment",
        "gold_macro_funds_monthly",
        "gold_market_comparison_monthly",
    }
)

st.set_page_config(
    page_title="Dashboard BI - Fundos",
    page_icon="BI",
    layout="wide",
)


@st.cache_resource
def get_warehouse_engine(warehouse_url: str) -> Engine:
    """Cria e reutiliza a conexao SQLAlchemy com o data warehouse."""
    return create_engine(warehouse_url, pool_pre_ping=True)


@st.cache_data(show_spinner=False, ttl=60)
def inspect_warehouse(warehouse_url: str) -> tuple[tuple[str, ...], str | None]:
    """Lista as tabelas disponiveis e informa falhas de conexao com o warehouse."""
    try:
        engine = get_warehouse_engine(warehouse_url)
        return tuple(inspect(engine).get_table_names()), None
    except SQLAlchemyError as exc:
        return (), type(exc).__name__


@st.cache_data(show_spinner=False, ttl=60)
def load_gold_table(
    name: str,
    warehouse_url: str,
    use_warehouse: bool,
) -> pd.DataFrame:
    """Carrega uma tabela gold do warehouse ou do CSV de contingencia."""
    if name not in DASHBOARD_TABLES:
        raise ValueError(f"Tabela nao permitida no dashboard: {name}")

    if use_warehouse:
        try:
            df = pd.read_sql_table(name, get_warehouse_engine(warehouse_url))
        except (SQLAlchemyError, ValueError):
            return pd.DataFrame()
    else:
        path = GOLD_DIR / f"{name}.csv"
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)

    for column in ["month_start", "date"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def brl(value: float | int | None) -> str:
    """Formata um numero como moeda brasileira."""
    if pd.isna(value):
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_compact(value: float | int | None) -> str:
    """Formata valores monetarios extensos com uma unidade abreviada."""
    if pd.isna(value):
        return "R$ 0,00"

    scales = (
        (1_000_000_000_000, "tri"),
        (1_000_000_000, "bi"),
        (1_000_000, "mi"),
        (1_000, "mil"),
    )
    for divisor, suffix in scales:
        if abs(value) >= divisor:
            compact_value = f"{value / divisor:,.2f}"
            compact_value = compact_value.replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {compact_value} {suffix}"
    return brl(value)


def pct(value: float | int | None) -> str:
    """Formata um numero decimal como percentual."""
    if pd.isna(value):
        return "0,00%"
    return f"{value * 100:.2f}%".replace(".", ",")


def ensure_columns(df: pd.DataFrame, columns: list[str], chart_name: str) -> bool:
    """Mostra aviso quando uma tabela nao possui os campos exigidos por um grafico."""
    missing = [column for column in columns if column not in df.columns]
    if df.empty:
        return False
    if missing:
        st.warning(f"Sem colunas para {chart_name}: {', '.join(missing)}")
        return False
    return True


def filter_period(df: pd.DataFrame, period: tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    """Filtra uma tabela mensal pelo periodo escolhido no dashboard."""
    if df.empty or "month_start" not in df.columns:
        return df
    start, end = period
    return df[df["month_start"].between(start, end)].copy()


def get_period_options(*frames: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Calcula o menor e maior mes disponivel nas tabelas carregadas."""
    dates = []
    for df in frames:
        if not df.empty and "month_start" in df.columns:
            dates.append(df["month_start"].dropna())
    if not dates:
        today = pd.Timestamp.today().normalize()
        return today, today
    all_dates = pd.concat(dates)
    return all_dates.min(), all_dates.max()


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    labels: dict[str, str] | None = None,
    height: int = DEFAULT_CHART_HEIGHT,
) -> None:
    """Renderiza um grafico de linha padronizado."""
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        markers=True,
        title=title,
        labels=labels,
        color_discrete_sequence=px.colors.qualitative.Alphabet if color else None,
    )
    fig.update_layout(
        height=height,
        legend_title_text="",
        hovermode="x unified",
        margin={"l": 30, "r": 30, "t": 70, "b": 100},
        legend={"orientation": "h", "yanchor": "top", "y": -0.15},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    orientation: str = "v",
    labels: dict[str, str] | None = None,
    height: int = DEFAULT_CHART_HEIGHT,
    show_legend: bool = True,
    categorical_axis: bool = False,
) -> None:
    """Renderiza um grafico de barras padronizado."""
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        orientation=orientation,
        labels=labels,
        color_discrete_sequence=px.colors.qualitative.Alphabet if color else None,
    )
    fig.update_layout(
        height=height,
        showlegend=show_legend,
        legend_title_text="",
        margin={"l": 30, "r": 30, "t": 70, "b": 100},
        legend={"orientation": "h", "yanchor": "top", "y": -0.15},
    )
    if categorical_axis:
        if orientation == "h":
            fig.update_yaxes(type="category")
        else:
            fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


def render_overview(
    public_funds: pd.DataFrame,
    risk_return: pd.DataFrame,
    flows: pd.DataFrame,
    period: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    """Renderiza a visao geral do dashboard."""
    st.header("Visao geral")
    public_funds = filter_period(public_funds, period)
    flows = filter_period(flows, period)

    latest_public = public_funds.sort_values("month_start").groupby("fund_cnpj").tail(1)
    total_net_worth = latest_public["net_worth"].sum() if "net_worth" in latest_public else 0
    total_applications = flows["applications"].sum() if "applications" in flows else 0
    total_redemptions = flows["redemptions"].sum() if "redemptions" in flows else 0
    total_net_flow = flows["net_flow_amount"].sum() if "net_flow_amount" in flows else 0
    avg_return = public_funds["monthly_return"].mean() if "monthly_return" in public_funds else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "PL publico mais recente",
        brl_compact(total_net_worth),
        help=f"Valor exato: {brl(total_net_worth)}",
    )
    col2.metric(
        "Aplicacoes",
        brl_compact(total_applications),
        help=f"Valor exato: {brl(total_applications)}",
    )
    col3.metric(
        "Resgates",
        brl_compact(total_redemptions),
        help=f"Valor exato: {brl(total_redemptions)}",
    )
    col4.metric(
        "Captacao liquida",
        brl_compact(total_net_flow),
        help=f"Valor exato: {brl(total_net_flow)}",
    )
    col5.metric("Retorno medio mensal", pct(avg_return))

    if ensure_columns(
        public_funds,
        ["month_start", "net_worth", "public_fund_name"],
        "evolucao mensal do patrimonio liquido",
    ):
        top_funds = (
            latest_public.sort_values("net_worth", ascending=False)["public_fund_name"]
            .head(8)
            .tolist()
        )
        chart_data = public_funds[public_funds["public_fund_name"].isin(top_funds)]
        line_chart(
            chart_data,
            "month_start",
            "net_worth",
            "1. Evolucao mensal do patrimonio liquido por fundo",
            "public_fund_name",
            {"month_start": "Mes", "net_worth": "Patrimonio liquido"},
        )

    if ensure_columns(
        risk_return,
        ["public_fund_name", "accumulated_return"],
        "maior rentabilidade acumulada",
    ):
        ranking = risk_return.nlargest(10, "accumulated_return").sort_values("accumulated_return")
        bar_chart(
            ranking,
            "accumulated_return",
            "public_fund_name",
            "2. Fundos com maior rentabilidade acumulada",
            color="public_fund_name",
            orientation="h",
            labels={
                "accumulated_return": "Rentabilidade acumulada",
                "public_fund_name": "Fundo",
            },
            height=RANKING_CHART_HEIGHT,
            show_legend=False,
        )


def render_funds_and_flows(
    public_funds: pd.DataFrame,
    flows: pd.DataFrame,
    period: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    """Renderiza analises de fundos, aplicacoes, resgates e captacao."""
    st.header("Fundos e captacao")
    public_funds = filter_period(public_funds, period)
    flows = filter_period(flows, period)

    if ensure_columns(
        flows, ["month_start", "applications", "redemptions"], "aplicacoes e resgates"
    ):
        monthly = flows.groupby("month_start", as_index=False).agg(
            applications=("applications", "sum"), redemptions=("redemptions", "sum")
        )
        melted = monthly.melt(
            id_vars="month_start",
            value_vars=["applications", "redemptions"],
            var_name="tipo",
            value_name="valor",
        )
        bar_chart(
            melted,
            "month_start",
            "valor",
            "3. Volume mensal de aplicacoes e resgates",
            "tipo",
            labels={"month_start": "Mes", "valor": "Valor", "tipo": "Tipo"},
        )

    if ensure_columns(flows, ["month_start", "net_flow_amount"], "meses com maior captacao"):
        monthly_net = flows.groupby("month_start", as_index=False).agg(
            net_flow_amount=("net_flow_amount", "sum")
        )
        top_months = monthly_net.nlargest(12, "net_flow_amount").sort_values("net_flow_amount")
        top_months["mes_ano"] = top_months["month_start"].dt.strftime("%m/%Y")
        bar_chart(
            top_months,
            "net_flow_amount",
            "mes_ano",
            "4. Meses com maior captacao liquida",
            orientation="h",
            labels={"net_flow_amount": "Captacao liquida", "mes_ano": "Mes/ano"},
            categorical_axis=True,
        )

    if ensure_columns(
        public_funds,
        ["public_fund_name", "net_worth", "monthly_net_flow", "monthly_return", "volatility"],
        "tabela de fundos",
    ):
        st.subheader("Tabela de fundos publicos")
        st.dataframe(
            public_funds.sort_values("net_worth", ascending=False)[
                [
                    "month_start",
                    "public_fund_name",
                    "net_worth",
                    "monthly_net_flow",
                    "monthly_return",
                    "volatility",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_investors(
    profile: pd.DataFrame,
    city: pd.DataFrame,
) -> None:
    """Renderiza analises por perfil de investidor e cidade."""
    st.header("Investidores e geografia")

    if ensure_columns(
        profile,
        ["fund_type", "investor_profile", "applications"],
        "perfil por tipo de fundo",
    ):
        bar_chart(
            profile,
            "fund_type",
            "applications",
            "5. Perfil de investidor que mais aplicou por tipo de fundo",
            "investor_profile",
            labels={
                "fund_type": "Tipo de fundo",
                "applications": "Aplicacoes",
                "investor_profile": "Perfil",
            },
        )
        st.dataframe(
            profile.sort_values(["fund_type", "applications"], ascending=[True, False]),
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    if ensure_columns(city, ["city", "state", "applications"], "cidades com maior volume"):
        top_cities = city.nlargest(15, "applications").sort_values("applications")
        top_cities["cidade_uf"] = top_cities["city"] + " - " + top_cities["state"]
        bar_chart(
            top_cities,
            "applications",
            "cidade_uf",
            "6. Cidades que concentram maior volume investido",
            orientation="h",
            labels={"applications": "Aplicacoes", "cidade_uf": "Cidade"},
            height=RANKING_CHART_HEIGHT,
        )
        st.dataframe(
            top_cities,
            use_container_width=True,
            hide_index=True,
            height=420,
        )


def render_macro(macro: pd.DataFrame, period: tuple[pd.Timestamp, pd.Timestamp]) -> None:
    """Renderiza relacoes entre indicadores macroeconomicos e fundos."""
    st.header("Macro x fundos")
    macro = filter_period(macro, period)

    if ensure_columns(
        macro,
        ["month_start", "selic_monthly_pct", "renda_fixa_net_flow"],
        "Selic x captacao em renda fixa",
    ):
        fig = px.line(
            macro,
            x="month_start",
            y="selic_monthly_pct",
            markers=True,
            title="7. Selic e captacao liquida em fundos de renda fixa",
            labels={"month_start": "Mes", "selic_monthly_pct": "Selic mensal (%)"},
        )
        fig.update_traces(
            line={"color": "#F28E2B", "width": 3},
            marker={"color": "#F28E2B", "size": 8},
        )
        fig.add_bar(
            x=macro["month_start"],
            y=macro["renda_fixa_net_flow"],
            name="Captacao liquida RF",
            marker_color="#4E79A7",
        )
        fig.data = fig.data[::-1]
        fig.data[0].yaxis = "y"
        fig.data[1].yaxis = "y2"
        fig.update_layout(
            height=DEFAULT_CHART_HEIGHT,
            yaxis={
                "side": "right",
                "title": "Captacao liquida RF",
                "showgrid": False,
            },
            yaxis2={
                "overlaying": "y",
                "side": "left",
                "title": "Selic mensal (%)",
                "showgrid": True,
            },
            hovermode="x unified",
            margin={"l": 30, "r": 30, "t": 70, "b": 40},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

    if ensure_columns(
        macro,
        ["ipca_monthly_pct", "avg_public_fund_return"],
        "IPCA x rentabilidade dos fundos",
    ):
        fig = px.scatter(
            macro,
            x="ipca_monthly_pct",
            y="avg_public_fund_return",
            hover_data=["month_start"],
            title="8. Relacao entre IPCA e rentabilidade media dos fundos",
            labels={
                "ipca_monthly_pct": "IPCA mensal (%)",
                "avg_public_fund_return": "Retorno medio dos fundos",
            },
        )
        fig.update_layout(
            height=DEFAULT_CHART_HEIGHT,
            margin={"l": 30, "r": 30, "t": 70, "b": 40},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


def render_market_and_risk(
    market: pd.DataFrame,
    risk_return: pd.DataFrame,
    period: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    """Renderiza comparacao de mercado e relacao risco-retorno."""
    st.header("Mercado, risco e retorno")
    market = filter_period(market, period)

    if ensure_columns(
        market,
        ["month_start", "bcri11_index_base_100", "ibovespa_index_base_100"],
        "BCRI11 x Ibovespa",
    ):
        market_index = market.melt(
            id_vars="month_start",
            value_vars=["bcri11_index_base_100", "ibovespa_index_base_100"],
            var_name="indice",
            value_name="valor",
        )
        line_chart(
            market_index,
            "month_start",
            "valor",
            "9. BCRI11 em comparacao ao Ibovespa - indice base 100",
            "indice",
            {"month_start": "Mes", "valor": "Indice base 100", "indice": "Ativo"},
        )

    if ensure_columns(
        risk_return,
        ["public_fund_name", "avg_daily_volatility", "accumulated_return", "return_risk_ratio"],
        "risco x retorno",
    ):
        fig = px.scatter(
            risk_return,
            x="avg_daily_volatility",
            y="accumulated_return",
            size="last_net_worth" if "last_net_worth" in risk_return.columns else None,
            color="public_fund_name",
            color_discrete_sequence=px.colors.qualitative.Alphabet,
            hover_name="public_fund_name",
            title="10. Melhor relacao entre rentabilidade e risco",
            labels={
                "avg_daily_volatility": "Volatilidade media diaria",
                "accumulated_return": "Rentabilidade acumulada",
                "last_net_worth": "PL mais recente",
                "public_fund_name": "Fundo",
            },
        )
        fig.update_traces(marker={"line": {"color": "white", "width": 1}, "opacity": 0.85})
        fig.update_layout(
            height=700,
            margin={"l": 30, "r": 30, "t": 70, "b": 150},
            legend={
                "orientation": "h",
                "title_text": "",
                "yanchor": "top",
                "y": -0.15,
            },
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

        ranking = risk_return.nlargest(15, "return_risk_ratio")
        st.subheader("Ranking retorno/risco")
        st.dataframe(
            ranking[
                [
                    "public_fund_name",
                    "accumulated_return",
                    "avg_daily_volatility",
                    "return_risk_ratio",
                    "last_net_worth",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    """Executa o dashboard Streamlit."""
    warehouse_tables, warehouse_error = inspect_warehouse(DEFAULT_WAREHOUSE_URL)
    use_warehouse = bool(warehouse_tables)

    public_funds = load_gold_table(
        "gold_public_funds_monthly", DEFAULT_WAREHOUSE_URL, use_warehouse
    )
    risk_return = load_gold_table("gold_risk_return", DEFAULT_WAREHOUSE_URL, use_warehouse)
    flows = load_gold_table("gold_internal_flows_monthly", DEFAULT_WAREHOUSE_URL, use_warehouse)
    profile = load_gold_table(
        "gold_investor_profile_fund_type", DEFAULT_WAREHOUSE_URL, use_warehouse
    )
    city = load_gold_table("gold_city_investment", DEFAULT_WAREHOUSE_URL, use_warehouse)
    macro = load_gold_table("gold_macro_funds_monthly", DEFAULT_WAREHOUSE_URL, use_warehouse)
    market = load_gold_table("gold_market_comparison_monthly", DEFAULT_WAREHOUSE_URL, use_warehouse)

    st.title("Dashboard BI - Fundos de Investimento")
    if use_warehouse:
        backend = make_url(DEFAULT_WAREHOUSE_URL).get_backend_name()
        st.caption(f"Fonte analitica: Data Warehouse {backend.upper()}.")
        missing_tables = sorted(DASHBOARD_TABLES.difference(warehouse_tables))
        if missing_tables:
            st.sidebar.warning(
                "O warehouse nao possui todas as tabelas do dashboard. "
                "Execute o pipeline novamente."
            )
    else:
        st.caption("Fonte de contingencia: arquivos CSV da camada gold.")
        error_detail = f" ({warehouse_error})" if warehouse_error else ""
        st.sidebar.warning(
            "Data Warehouse indisponivel"
            f"{error_detail}. O dashboard esta usando os CSVs de contingencia."
        )

    min_date, max_date = get_period_options(public_funds, flows, macro, market)
    period = st.sidebar.date_input(
        "Periodo de analise",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    if isinstance(period, tuple) and len(period) == 2:
        selected_period = (pd.Timestamp(period[0]), pd.Timestamp(period[1]))
    else:
        selected_period = (min_date, max_date)

    tabs = st.tabs(
        [
            "Visao geral",
            "Fundos e captacao",
            "Investidores e geografia",
            "Macro x fundos",
            "Mercado e risco",
        ]
    )

    with tabs[0]:
        render_overview(public_funds, risk_return, flows, selected_period)
    with tabs[1]:
        render_funds_and_flows(public_funds, flows, selected_period)
    with tabs[2]:
        render_investors(profile, city)
    with tabs[3]:
        render_macro(macro, selected_period)
    with tabs[4]:
        render_market_and_risk(market, risk_return, selected_period)


if __name__ == "__main__":
    main()
