# Dicionario de dados

## Convencoes

- Datas seguem o formato ISO `YYYY-MM-DD`.
- Valores monetarios sao armazenados em reais.
- Retornos e volatilidades sao armazenados como numeros decimais. Exemplo: `0.01`
  representa 1%.
- Campos com sufixo `_pct` representam valores percentuais informados pela fonte.
- As chaves descritas neste documento sao chaves logicas do modelo. A carga atual com
  Pandas e SQLAlchemy recria as tabelas e nao aplica restricoes fisicas de PK e FK.
- As tabelas Gold sao persistidas como CSV e carregadas no Data Warehouse SQLite ou
  PostgreSQL. O dashboard Streamlit consulta o Data Warehouse.

## Bronze - fonte interna fake

Os arquivos sao gerados por `src/fake_internal.py` em `data/bronze/internal`.

### internal_customers

Granularidade: um registro por cliente.

| Campo | Tipo | Descricao |
|---|---|---|
| `customer_id` | inteiro | Identificador unico do cliente fake |
| `customer_name` | texto | Nome gerado pelo Faker |
| `investor_profile` | texto | Perfil Conservador, Moderado ou Arrojado |
| `city` | texto | Cidade do cliente |
| `state` | texto | Sigla da UF |
| `birth_date` | data | Data de nascimento |
| `signup_date` | data | Data de cadastro na instituicao |

### internal_accounts

Granularidade: um registro por conta.

| Campo | Tipo | Descricao |
|---|---|---|
| `account_id` | inteiro | Identificador unico da conta |
| `customer_id` | inteiro | Cliente proprietario da conta |
| `account_open_date` | data | Data de abertura da conta |
| `channel` | texto | Canal App, Assessoria, Agencia ou Web |

### internal_funds

Granularidade: um registro por produto de investimento interno.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_key` | texto | Chave natural do produto |
| `fund_name` | texto | Nome do fundo |
| `fund_type` | texto | Renda Fixa, Multimercado, Acoes ou FII |
| `risk_bucket` | texto | Faixa qualitativa de risco |
| `ticker` | texto | Codigo de negociacao quando aplicavel |

### internal_transactions

Granularidade: uma movimentacao por registro.

| Campo | Tipo | Descricao |
|---|---|---|
| `transaction_id` | inteiro | Identificador unico da movimentacao |
| `account_id` | inteiro | Conta associada |
| `customer_id` | inteiro | Cliente associado |
| `fund_key` | texto | Fundo movimentado |
| `transaction_date` | data | Data da movimentacao |
| `transaction_type` | texto | Aplicacao ou Resgate |
| `amount` | decimal | Valor positivo da movimentacao |

## Bronze - fontes publicas

Os arquivos originais sao armazenados em `data/bronze/public`.

### Informes diarios da CVM

Fonte: Portal de Dados Abertos da CVM. Granularidade: um fundo por data de competencia.

| Campo original | Tipo | Descricao |
|---|---|---|
| `CNPJ_FUNDO` ou `CNPJ_FUNDO_CLASSE` | texto | Identificador do fundo ou da classe |
| `DT_COMPTC` | data | Data de competencia |
| `VL_TOTAL` | decimal | Valor total da carteira |
| `VL_QUOTA` | decimal | Valor da cota |
| `VL_PATRIM_LIQ` | decimal | Patrimonio liquido |
| `CAPTC_DIA` | decimal | Captacao no dia |
| `RESG_DIA` | decimal | Resgate no dia |
| `NR_COTST` | inteiro | Quantidade de cotistas |

### Cadastro de fundos da CVM

Fonte: Portal de Dados Abertos da CVM. Granularidade: um registro cadastral por fundo.

| Campo original | Tipo | Descricao |
|---|---|---|
| `CNPJ_FUNDO` | texto | Identificador do fundo |
| `DENOM_SOCIAL` | texto | Denominacao social |
| `SIT` | texto | Situacao cadastral |
| `CLASSE` | texto | Classe CVM |
| `DT_REG` | data | Data de registro |
| `DT_CONST` | data | Data de constituicao |
| `DT_CANCEL` | data | Data de cancelamento, quando existente |

### Series SGS do Banco Central

Granularidade: uma observacao por data e indicador.

| Campo | Tipo | Descricao |
|---|---|---|
| `date` | data | Data da observacao |
| `selic_daily_pct` | decimal | Taxa Selic diaria, serie SGS 11 |
| `ipca_monthly_pct` | decimal | IPCA mensal, serie SGS 433 |

### Cotacoes de mercado

Fonte: Yahoo Finance por meio do yfinance. Granularidade: um ativo por pregao.

| Campo | Tipo | Descricao |
|---|---|---|
| `date` | data | Data do pregao |
| `ticker` | texto | `BCRI11.SA` ou `^BVSP` |
| `close` | decimal | Preco ajustado de fechamento |
| `month` | data | Primeiro dia do mes da observacao |

## Silver

As tabelas Silver sao persistidas em `data/silver`.

### silver_internal_customers

Mesmas colunas de `internal_customers`, com `birth_date` e `signup_date`
convertidas para data.

### silver_internal_accounts

Mesmas colunas de `internal_accounts`, com `account_open_date` convertida para
data.

### silver_internal_funds

Mesmas colunas de `internal_funds`.

### silver_internal_transactions

Mesmas colunas de `internal_transactions`, com `transaction_date` tipada,
`amount` numerico e registros sem data ou fundo removidos.

### silver_cvm_fund_daily

Granularidade: um fundo publico por dia.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_cnpj` | texto | Identificador normalizado do fundo |
| `date` | data | Data de competencia |
| `total_assets` | decimal | Valor total da carteira |
| `share_value` | decimal | Valor da cota |
| `net_worth` | decimal | Patrimonio liquido |
| `daily_application` | decimal | Captacao diaria |
| `daily_redemption` | decimal | Resgate diario |
| `quota_holders` | inteiro | Quantidade de cotistas |
| `date_key` | inteiro | Data no formato `YYYYMMDD` |
| `month_start` | data | Primeiro dia do mes |
| `daily_net_flow` | decimal | Captacao menos resgate no dia |
| `daily_return` | decimal | Variacao diaria do valor da cota |

### silver_cvm_registry

Granularidade: um registro por fundo selecionado.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_cnpj` | texto | Identificador do fundo |
| `public_fund_name` | texto | Denominacao social |
| `status` | texto | Situacao cadastral |
| `public_fund_class` | texto | Classe CVM |
| `registry_date` | data | Data de registro |
| `constitution_date` | data | Data de constituicao |
| `cancel_date` | data | Data de cancelamento |

### silver_macro_daily

Granularidade: uma data por registro; as series podem ter calendarios diferentes.

| Campo | Tipo | Descricao |
|---|---|---|
| `date` | data | Data da observacao |
| `selic_daily_pct` | decimal | Taxa Selic diaria |
| `ipca_monthly_pct` | decimal | IPCA informado no mes |
| `month` | data | Primeiro dia do mes |

### silver_market_daily

Granularidade: um ativo por pregao.

| Campo | Tipo | Descricao |
|---|---|---|
| `date` | data | Data do pregao |
| `ticker` | texto | Codigo do ativo |
| `close` | decimal | Fechamento ajustado |
| `month` | data | Primeiro dia do mes |
| `daily_return` | decimal | Retorno entre dois fechamentos consecutivos |

## Gold - modelo dimensional

### dim_date

Granularidade: um registro por dia. Chave logica: `date_key`.

| Campo | Tipo | Descricao |
|---|---|---|
| `date_key` | inteiro | Data no formato `YYYYMMDD` |
| `date` | data | Data completa |
| `year` | inteiro | Ano |
| `quarter` | inteiro | Trimestre |
| `month` | inteiro | Numero do mes |
| `month_start` | data | Primeiro dia do mes |
| `month_name` | texto | Nome abreviado do mes |

### dim_customer

Granularidade: um registro por cliente. Chave logica: `customer_id`.

| Campo | Tipo | Descricao |
|---|---|---|
| `customer_id` | inteiro | Identificador do cliente |
| `customer_name` | texto | Nome fake do cliente |
| `investor_profile` | texto | Perfil de risco |
| `city` | texto | Cidade |
| `state` | texto | UF |
| `birth_date` | data | Data de nascimento |
| `signup_date` | data | Data de cadastro |

### dim_fund

Granularidade: um registro por fundo interno. Chave logica: `fund_key`.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_key` | texto | Identificador do fundo |
| `fund_name` | texto | Nome do fundo |
| `fund_type` | texto | Tipo do fundo |
| `risk_bucket` | texto | Faixa qualitativa de risco |

### fact_transactions

Granularidade: uma movimentacao. Chave logica: `transaction_id`.

| Campo | Tipo | Descricao |
|---|---|---|
| `transaction_id` | inteiro | Identificador da movimentacao |
| `date_key` | inteiro | Referencia logica para `dim_date` |
| `customer_id` | inteiro | Referencia logica para `dim_customer` |
| `account_id` | inteiro | Identificador degenerado da conta |
| `fund_key` | texto | Referencia logica para `dim_fund` |
| `transaction_type` | texto | Aplicacao ou Resgate |
| `amount` | decimal | Valor original da movimentacao |
| `application_amount` | decimal | Valor quando a operacao e Aplicacao; zero caso contrario |
| `redemption_amount` | decimal | Valor quando a operacao e Resgate; zero caso contrario |
| `net_flow_amount` | decimal | Aplicacoes menos resgates |

### fact_public_fund_monthly

Granularidade: um fundo publico por mes. Chave logica: `fund_cnpj` e
`month_start`.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_cnpj` | texto | Identificador do fundo |
| `month_start` | data | Mes de referencia |
| `net_worth` | decimal | Ultimo patrimonio liquido observado no mes |
| `monthly_application` | decimal | Soma das captacoes diarias |
| `monthly_redemption` | decimal | Soma dos resgates diarios |
| `monthly_net_flow` | decimal | Captacao menos resgate no mes |
| `quota_holders` | inteiro | Ultima quantidade de cotistas observada no mes |
| `monthly_return` | decimal | Retorno composto das cotas no mes |
| `volatility` | decimal | Desvio padrao dos retornos diarios no mes |
| `public_fund_name` | texto | Denominacao social; fundos sem nome real sao removidos |

### fact_macro_monthly

Granularidade: um registro por mes. Chave logica: `month_start`.

| Campo | Tipo | Descricao |
|---|---|---|
| `month_start` | data | Mes de referencia |
| `selic_monthly_pct` | decimal | Soma das taxas Selic diarias no mes |
| `ipca_monthly_pct` | decimal | Ultimo IPCA informado no mes |

### fact_market_monthly

Granularidade: um ativo por mes. Chave logica: `ticker` e `month_start`.

| Campo | Tipo | Descricao |
|---|---|---|
| `ticker` | texto | `BCRI11.SA` ou `^BVSP` |
| `month_start` | data | Mes de referencia |
| `month_close` | decimal | Ultimo fechamento observado no mes |
| `monthly_return` | decimal | Retorno composto no mes |
| `volatility` | decimal | Desvio padrao dos retornos diarios no mes |

## Gold - data marts do Streamlit

Essas tabelas achatadas sao criadas por `src/dashboard_marts.py`, carregadas no
Data Warehouse e consultadas diretamente por `app.py`.

### gold_public_funds_monthly

Granularidade: um fundo publico por mes. Acrescenta aos campos de
`fact_public_fund_monthly`:

| Campo adicional | Tipo | Descricao |
|---|---|---|
| `return_index_base_100` | decimal | Evolucao acumulada iniciada em 100 |
| `accumulated_return` | decimal | Retorno acumulado desde o inicio do periodo |

### gold_risk_return

Granularidade: um registro por fundo publico. Chave logica: `fund_cnpj`.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_cnpj` | texto | Identificador do fundo |
| `public_fund_name` | texto | Nome do fundo |
| `avg_monthly_return` | decimal | Media dos retornos mensais |
| `accumulated_return` | decimal | Retorno composto no periodo |
| `avg_daily_volatility` | decimal | Media das volatilidades mensais de retornos diarios |
| `last_net_worth` | decimal | Patrimonio liquido mais recente |
| `total_net_flow` | decimal | Captacao liquida acumulada |
| `months_count` | inteiro | Quantidade de meses observados |
| `return_risk_ratio` | decimal | Retorno acumulado dividido pela volatilidade media |

### gold_internal_flows_monthly

Granularidade: um fundo interno por mes. Chave logica: `month_start` e
`fund_key`.

| Campo | Tipo | Descricao |
|---|---|---|
| `month_start` | data | Mes de referencia |
| `year` | inteiro | Ano |
| `month` | inteiro | Numero do mes |
| `fund_key` | texto | Identificador do fundo |
| `fund_name` | texto | Nome do fundo |
| `fund_type` | texto | Tipo do fundo |
| `applications` | decimal | Volume total de aplicacoes |
| `redemptions` | decimal | Volume total de resgates |
| `net_flow_amount` | decimal | Aplicacoes menos resgates |
| `transaction_count` | inteiro | Quantidade de movimentacoes |

### gold_investor_profile_fund_type

Granularidade: um tipo de fundo por perfil de investidor.

| Campo | Tipo | Descricao |
|---|---|---|
| `fund_type` | texto | Tipo do fundo |
| `investor_profile` | texto | Perfil de risco |
| `applications` | decimal | Volume aplicado |
| `redemptions` | decimal | Volume resgatado |
| `net_flow_amount` | decimal | Aplicacoes menos resgates |
| `investor_count` | inteiro | Quantidade distinta de clientes |
| `transaction_count` | inteiro | Quantidade de movimentacoes |

### gold_city_investment

Granularidade: uma cidade e UF.

| Campo | Tipo | Descricao |
|---|---|---|
| `state` | texto | Sigla da UF |
| `city` | texto | Cidade |
| `applications` | decimal | Volume aplicado |
| `redemptions` | decimal | Volume resgatado |
| `net_flow_amount` | decimal | Aplicacoes menos resgates |
| `investor_count` | inteiro | Quantidade distinta de clientes |
| `transaction_count` | inteiro | Quantidade de movimentacoes |

### gold_macro_funds_monthly

Granularidade: um registro por mes.

| Campo | Tipo | Descricao |
|---|---|---|
| `month_start` | data | Mes de referencia |
| `selic_monthly_pct` | decimal | Selic mensal |
| `ipca_monthly_pct` | decimal | IPCA mensal |
| `renda_fixa_applications` | decimal | Aplicacoes internas em Renda Fixa |
| `renda_fixa_redemptions` | decimal | Resgates internos em Renda Fixa |
| `renda_fixa_net_flow` | decimal | Captacao liquida interna em Renda Fixa |
| `avg_public_fund_return` | decimal | Retorno medio dos fundos publicos |
| `avg_public_fund_volatility` | decimal | Volatilidade media dos fundos publicos |
| `total_public_net_flow` | decimal | Captacao liquida total dos fundos publicos |

### gold_market_comparison_monthly

Granularidade: um registro por mes.

| Campo | Tipo | Descricao |
|---|---|---|
| `month_start` | data | Mes de referencia |
| `bcri11_return` | decimal | Retorno mensal do BCRI11 |
| `ibovespa_return` | decimal | Retorno mensal do Ibovespa |
| `bcri11_minus_ibovespa_return` | decimal | Diferenca de retorno entre BCRI11 e Ibovespa |
| `bcri11_index_base_100` | decimal | Desempenho acumulado do BCRI11 iniciado em 100 |
| `ibovespa_index_base_100` | decimal | Desempenho acumulado do Ibovespa iniciado em 100 |
