# Dicionario de Dados

## Camadas do pipeline

### Bronze

- `data/bronze/public`: arquivos baixados das fontes publicas, preservando o formato original sempre que possivel.
- `data/bronze/internal`: CSVs fake que simulam uma fonte transacional interna.

### Silver

- `silver_internal_customers`: clientes fake com datas padronizadas.
- `silver_internal_accounts`: contas fake com data de abertura padronizada.
- `silver_internal_funds`: cadastro interno de produtos de investimento.
- `silver_internal_transactions`: movimentacoes internas tipadas e limpas.
- `silver_cvm_fund_daily`: informes diarios da CVM renomeados, tipados e com retorno diario.
- `silver_cvm_registry`: cadastro de fundos CVM com atributos selecionados.
- `silver_macro_daily`: series Selic/IPCA padronizadas por data.
- `silver_market_daily`: cotacoes diarias com retorno diario.

### Gold

As tabelas gold sao carregadas no warehouse e usadas pelo dashboard.

## dim_customer

- `customer_id`: identificador fake do cliente.
- `investor_profile`: perfil de risco: Conservador, Moderado ou Arrojado.
- `city`, `state`: localizacao usada para responder concentracao geografica.

## dim_fund

- `fund_key`: chave interna do produto fake.
- `fund_type`: classe do fundo usada nas analises por perfil.
- `risk_bucket`: faixa qualitativa de risco.

## fact_transactions

- `application_amount`: valor aplicado quando a transacao e aplicacao.
- `redemption_amount`: valor resgatado quando a transacao e resgate.
- `net_flow_amount`: aplicacoes menos resgates.

## fact_public_fund_monthly

- `net_worth`: patrimonio liquido mensal do fundo publico.
- `monthly_application`: soma mensal de captacoes informadas pela CVM.
- `monthly_redemption`: soma mensal de resgates informados pela CVM.
- `monthly_net_flow`: captacao liquida mensal.
- `monthly_return`: retorno mensal estimado pela variacao da cota.
- `volatility`: desvio padrao dos retornos diarios no mes.

## fact_macro_monthly

- `selic_monthly_pct`: soma das taxas Selic diarias do mes, serie SGS 11.
- `ipca_monthly_pct`: IPCA mensal, serie SGS 433.

## fact_market_monthly

- `ticker`: BCRI11.SA ou ^BVSP.
- `monthly_return`: retorno mensal calculado a partir dos fechamentos diarios.
- `volatility`: desvio padrao dos retornos diarios no mes.
