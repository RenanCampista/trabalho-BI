# Backend do Projeto de BI

Backend para preparar as fontes de dados do trabalho antes do dashboard:

- dados publicos de fundos da CVM;
- indicadores macroeconomicos do Banco Central;
- cotacoes de BCRI11 e Ibovespa via Yahoo Finance/yfinance;
- dados internos fake de clientes, contas e movimentacoes;
- pipeline medalhao com camadas bronze, silver e gold;
- modelo dimensional e carga em SQLite ou PostgreSQL.

## Perguntas de negocio cobertas

1. Qual foi a evolucao mensal do patrimonio liquido por fundo?
2. Qual fundo teve maior rentabilidade acumulada no periodo?
3. Qual foi o volume mensal de aplicacoes e resgates?
4. Em quais meses houve maior captacao liquida?
5. Qual perfil de investidor mais aplicou em cada tipo de fundo?
6. Quais cidades concentram maior volume investido?
7. Existe relacao entre Selic e captacao em fundos de renda fixa?
8. Existe relacao entre IPCA e rentabilidade dos fundos?
9. Como o BCRI11 se comportou em comparacao ao Ibovespa?
10. Quais fundos tiveram melhor relacao entre rentabilidade e risco?

## Stack

- Python/Pandas para ingestao e tratamento;
- SQLite para demonstracao local;
- PostgreSQL opcional como data warehouse;
- Looker Studio conectado ao banco/export CSV;
- dbdiagram.io para documentar o modelo dimensional.

## Pipeline medalhao

- `data/bronze/public`: arquivos publicos brutos baixados da CVM e demais fontes.
- `data/bronze/internal`: fonte interna fake gerada com Faker.
- `data/silver`: dados limpos, tipados, padronizados e ainda pouco agregados.
- `data/gold`: dimensoes, fatos e agregacoes analiticas produzidas pelo pipeline.
- `warehouse`: banco SQLite ou PostgreSQL carregado com as tabelas gold e usado pelo dashboard.

## Como rodar

Crie um ambiente Python 3.11+ e instale as dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Execute o pipeline em SQLite:

```powershell
python -m src.pipeline --warehouse sqlite:///warehouse/bi_fundos.sqlite
```

Por padrao, o pipeline carrega os 80 maiores fundos da CVM por patrimonio liquido no mes de referencia. Isso evita carregar a base inteira da CVM em memoria. Para reduzir ainda mais o consumo:

```powershell
python -m src.pipeline --max-public-funds 30
```

Gere tambem o perfil exploratorio das fontes publicas:

```powershell
python -m src.explore_public_sources --start-year 2023 --end-year 2025 --max-public-funds 80
```

Ou em PostgreSQL:

```powershell
$env:WAREHOUSE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/bi_fundos"
python -m src.pipeline --warehouse $env:WAREHOUSE_URL
```



## Dashboard Streamlit

Tambem ha um dashboard local em Streamlit para validar e apresentar as 10 perguntas sem depender do Looker Studio.

O Data Warehouse e a fonte analitica principal do dashboard. Portanto, execute primeiro o pipeline para
tratar os dados e carregar as tabelas gold no SQLite:

```powershell
pip install -r requirements.txt
python -m src.pipeline --warehouse sqlite:///warehouse/bi_fundos.sqlite
streamlit run app.py
```

O app usa a `WAREHOUSE_URL` definida no `.env`, a mesma configuracao utilizada pelo pipeline. Se o banco
estiver indisponivel, o dashboard usa temporariamente os CSVs de `data/gold` e exibe um aviso na barra
lateral. Na apresentacao, confirme que a barra lateral mostra `Fonte: Data Warehouse (SQLITE)`.

O dashboard organiza os graficos em cinco abas:

- Visao geral
- Fundos e captacao
- Investidores e geografia
- Macro x fundos
- Mercado e risco

O fluxo demonstrado pelo projeto fica:

```text
Fontes internas e publicas -> Bronze -> Silver -> Gold -> Data Warehouse -> Streamlit
```

## Google Sheets e Looker Studio

Ao final do pipeline, tambem e gerada uma planilha pronta para importar no Google Sheets:

```text
data/gold/google_sheets_dashboard.xlsx
```

Essa planilha contem abas da camada gold ja achatadas para dashboard, como:

- `public_funds_monthly`
- `risk_return`
- `internal_flows_monthly`
- `investor_profile_fund_type`
- `city_investment`
- `macro_funds_monthly`
- `market_comparison_monthly`

Importe esse arquivo no Google Sheets e conecte a planilha no Looker Studio. O prompt para orientar o Gemini na criacao dos graficos esta em:

```text
docs/prompt_gemini_looker_studio.md
```
## Fontes publicas

- CVM Dados Abertos: informes diarios e cadastro de fundos de investimento.
- Banco Central SGS: Selic e IPCA.
- Yahoo Finance via `yfinance`: BCRI11.SA e ^BVSP.

## Modelo

O modelo dimensional esta em `docs/modelo.png`.



