-- 1. Evolucao mensal do patrimonio liquido por fundo
select
  month_start,
  public_fund_name,
  net_worth
from fact_public_fund_monthly
order by month_start, net_worth desc;

-- 2. Fundo com maior rentabilidade acumulada
select
  fund_cnpj,
  public_fund_name,
  exp(sum(ln(1 + monthly_return))) - 1 as accumulated_return
from fact_public_fund_monthly
where monthly_return > -1
group by fund_cnpj, public_fund_name
order by accumulated_return desc;

-- 3 e 4. Volume mensal de aplicacoes, resgates e captacao liquida interna
select
  d.month_start,
  f.fund_type,
  sum(t.application_amount) as applications,
  sum(t.redemption_amount) as redemptions,
  sum(t.net_flow_amount) as net_flow
from fact_transactions t
join dim_date d on d.date_key = t.date_key
join dim_fund f on f.fund_key = t.fund_key
group by d.month_start, f.fund_type
order by d.month_start, f.fund_type;

-- 5. Perfil que mais aplicou por tipo de fundo
select
  f.fund_type,
  c.investor_profile,
  sum(t.application_amount) as applications
from fact_transactions t
join dim_customer c on c.customer_id = t.customer_id
join dim_fund f on f.fund_key = t.fund_key
group by f.fund_type, c.investor_profile
order by f.fund_type, applications desc;

-- 6. Cidades com maior volume investido
select
  c.city,
  c.state,
  sum(t.application_amount) as applications,
  sum(t.net_flow_amount) as net_flow
from fact_transactions t
join dim_customer c on c.customer_id = t.customer_id
group by c.city, c.state
order by applications desc;

-- 7. Base para relacao Selic x captacao em renda fixa
select
  d.month_start,
  m.selic_monthly_pct,
  sum(t.net_flow_amount) as renda_fixa_net_flow
from fact_transactions t
join dim_date d on d.date_key = t.date_key
join dim_fund f on f.fund_key = t.fund_key
join fact_macro_monthly m on m.month_start = d.month_start
where f.fund_type = 'Renda Fixa'
group by d.month_start, m.selic_monthly_pct
order by d.month_start;

-- 8. Base para relacao IPCA x rentabilidade dos fundos publicos
select
  p.month_start,
  p.fund_cnpj,
  p.public_fund_name,
  m.ipca_monthly_pct,
  p.monthly_return
from fact_public_fund_monthly p
join fact_macro_monthly m on m.month_start = p.month_start;

-- 9. BCRI11 comparado ao Ibovespa
select
  month_start,
  ticker,
  monthly_return,
  volatility
from fact_market_monthly
where ticker in ('BCRI11.SA', '^BVSP')
order by month_start, ticker;

-- 10. Melhor relacao entre rentabilidade e risco
select
  fund_cnpj,
  public_fund_name,
  avg(monthly_return) as avg_monthly_return,
  avg(volatility) as avg_daily_volatility,
  avg(monthly_return) / nullif(avg(volatility), 0) as return_risk_ratio
from fact_public_fund_monthly
group by fund_cnpj, public_fund_name
order by return_risk_ratio desc;

