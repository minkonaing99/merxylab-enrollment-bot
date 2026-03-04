from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    channel_id: Optional[int]
    admin_channel_id: Optional[int]
    region_name: str
    bucket_name: str
    min_amount_ks: int = 5000
    expected_receiver_name: str = "U MIN KO NAING"
    expected_receiver_last4: str = "3307"
    payment_table: str = "merxylab-payment"
    invited_users_table: str = "merxylab-invited_users"
    started_users_table: str = "merxylab-startedusers"
    paid_users_table: str = "merxylab-paid_users"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _optional_int(name: str) -> Optional[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer, got: {raw}") from exc


def load_config() -> AppConfig:
    return AppConfig(
        bot_token=_required("BOT_TOKEN"),
        channel_id=_optional_int("CHANNEL_ID"),
        admin_channel_id=_optional_int("ADMIN_CHANNEL_ID"),
        region_name=_required("REGION_NAME"),
        bucket_name=_required("BUCKET_NAME"),
        min_amount_ks=int(os.getenv("MIN_AMOUNT_KS", "5000")),
        expected_receiver_name=os.getenv("EXPECTED_RECEIVER_NAME", "U MIN KO NAING"),
        expected_receiver_last4=os.getenv("EXPECTED_RECEIVER_LAST4", "3307"),
        payment_table=os.getenv("PAYMENT_TABLE", "merxylab-payment"),
        invited_users_table=os.getenv("INVITED_USERS_TABLE", "merxylab-invited_users"),
        started_users_table=os.getenv("STARTED_USERS_TABLE", "merxylab-startedusers"),
        paid_users_table=os.getenv("PAID_USERS_TABLE", "merxylab-paid_users"),
    )
