from __future__ import annotations

import random
from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker

from src.config import INTERNAL_DIR, SELECTED_FUNDS, PipelineConfig


INVESTOR_PROFILES = ["Conservador", "Moderado", "Arrojado"]
BRAZILIAN_CITIES = [
    ("Sao Paulo", "SP"),
    ("Rio de Janeiro", "RJ"),
    ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"),
    ("Porto Alegre", "RS"),
    ("Salvador", "BA"),
    ("Recife", "PE"),
    ("Goiania", "GO"),
    ("Brasilia", "DF"),
    ("Fortaleza", "CE"),
]


def generate_internal_data(config: PipelineConfig) -> dict[str, pd.DataFrame]:
    fake = Faker("pt_BR")
    Faker.seed(config.seed)
    random.seed(config.seed)
    np.random.seed(config.seed)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    customers = []
    for customer_id in range(1, config.n_customers + 1):
        city, state = random.choice(BRAZILIAN_CITIES)
        profile = random.choices(INVESTOR_PROFILES, weights=[0.42, 0.38, 0.20], k=1)[0]
        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": fake.name(),
                "investor_profile": profile,
                "city": city,
                "state": state,
                "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=78),
                "signup_date": fake.date_between(
                    start_date=datetime(config.start_year - 2, 1, 1),
                    end_date=datetime(config.end_year, 12, 31),
                ),
            }
        )
    df_customers = pd.DataFrame(customers)

    accounts = []
    for account_id in range(1, config.n_accounts + 1):
        customer = df_customers.sample(1, random_state=config.seed + account_id).iloc[0]
        accounts.append(
            {
                "account_id": account_id,
                "customer_id": int(customer["customer_id"]),
                "account_open_date": fake.date_between(
                    start_date=customer["signup_date"],
                    end_date=datetime(config.end_year, 12, 31),
                ),
                "channel": random.choice(["App", "Assessoria", "Agencia", "Web"]),
            }
        )
    df_accounts = pd.DataFrame(accounts)

    dates = pd.date_range(
        start=f"{config.start_year}-01-01",
        end=f"{config.end_year}-12-31",
        freq="D",
    )
    transactions = []
    for transaction_id in range(1, config.n_transactions + 1):
        account = df_accounts.sample(1, random_state=config.seed + transaction_id).iloc[0]
        customer = df_customers.loc[df_customers["customer_id"] == account["customer_id"]].iloc[0]
        fund = _choose_fund_by_profile(customer["investor_profile"])
        tx_type = random.choices(["Aplicacao", "Resgate"], weights=[0.66, 0.34], k=1)[0]
        amount = round(float(np.random.lognormal(mean=8.45, sigma=0.85)), 2)
        if tx_type == "Resgate":
            amount = round(amount * random.uniform(0.45, 0.95), 2)
        transactions.append(
            {
                "transaction_id": transaction_id,
                "account_id": int(account["account_id"]),
                "customer_id": int(customer["customer_id"]),
                "fund_key": fund["fund_key"],
                "transaction_date": random.choice(dates).date(),
                "transaction_type": tx_type,
                "amount": amount,
            }
        )
    df_transactions = pd.DataFrame(transactions)

    df_funds_internal = pd.DataFrame(SELECTED_FUNDS)
    outputs = {
        "internal_customers": df_customers,
        "internal_accounts": df_accounts,
        "internal_funds": df_funds_internal,
        "internal_transactions": df_transactions,
    }
    for name, df in outputs.items():
        df.to_csv(INTERNAL_DIR / f"{name}.csv", index=False)
    return outputs


def _choose_fund_by_profile(profile: str) -> dict:
    if profile == "Conservador":
        weights = [0.58, 0.24, 0.06, 0.12]
    elif profile == "Moderado":
        weights = [0.30, 0.36, 0.14, 0.20]
    else:
        weights = [0.14, 0.30, 0.34, 0.22]
    return random.choices(SELECTED_FUNDS, weights=weights, k=1)[0]

