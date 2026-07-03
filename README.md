# Backend do Projeto de BI

Backend para preparar as fontes de dados do trabalho antes do dashboard:

- dados publicos de fundos da CVM;
- indicadores macroeconomicos do Banco Central;
- cotacoes de BCRI11 e Ibovespa via Yahoo Finance/yfinance;
- dados internos fake de clientes, contas e movimentacoes;
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

Gere tambem o perfil exploratorio das fontes publicas:

```powershell
python -m src.explore_public_sources --start-year 2023 --end-year 2025
```

Ou em PostgreSQL:

```powershell
$env:WAREHOUSE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/bi_fundos"
python -m src.pipeline --warehouse $env:WAREHOUSE_URL
```

Os arquivos ficam em:

- `data/raw`: dados brutos baixados;
- `data/internal`: dados internos fake;
- `data/processed`: tabelas dimensionais e fatos em CSV;
- `warehouse/bi_fundos.sqlite`: banco demonstravel localmente.

## Fontes publicas

- CVM Dados Abertos: informes diarios e cadastro de fundos de investimento.
- Banco Central SGS: Selic e IPCA.
- Yahoo Finance via `yfinance`: BCRI11.SA e ^BVSP.

## Modelo

O modelo dimensional esta em `docs/modelo.png`.
