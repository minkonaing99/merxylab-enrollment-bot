from __future__ import annotations

from datetime import datetime, timezone
import logging

import boto3
from boto3.dynamodb.conditions import Attr

from bot.config import AppConfig

logger = logging.getLogger(__name__)


class AwsDataStore:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._dynamodb = boto3.resource(
            "dynamodb",
            region_name=config.region_name,
        )
        self._s3 = boto3.client(
            "s3",
            region_name=config.region_name,
        )

    def upload_payment_image(self, local_path: str, filename: str) -> None:
        self._s3.upload_file(local_path, self._config.bucket_name, f"payments/{filename}")

    def log_payment(self, user_id: int, username: str | None, file_name: str, extracted_data: dict[str, str | None]) -> None:
        table = self._dynamodb.Table(self._config.payment_table)
        item = {
            "user_id": str(user_id),
            "username": username or "N/A",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_name": file_name,
            "transaction_no": extracted_data.get("Transaction No", "") or "",
            "amount": extracted_data.get("Amount", "") or "",
            "transaction_time": extracted_data.get("Transaction Time", "") or "",
            "notes": extracted_data.get("Notes", "") or "",
        }
        table.put_item(Item=item)

    def mark_user_as_invited(self, user_id: int) -> None:
        table = self._dynamodb.Table(self._config.invited_users_table)
        table.put_item(Item={"user_id": str(user_id), "invited": True})

    def has_user_been_invited(self, user_id: int) -> bool:
        table = self._dynamodb.Table(self._config.invited_users_table)
        response = table.get_item(Key={"user_id": str(user_id)})
        return response.get("Item", {}).get("invited", False)

    def is_duplicate_transaction(self, transaction_no: str) -> bool:
        table = self._dynamodb.Table(self._config.payment_table)
        try:
            response = table.scan(FilterExpression=Attr("transaction_no").eq(transaction_no))
            return response["Count"] > 0
        except Exception as exc:
            logger.error("[DynamoDB ERROR] Duplicate check failed: %s", exc)
            return False

    def mark_user_as_started(self, user_id: int) -> None:
        table = self._dynamodb.Table(self._config.started_users_table)
        table.put_item(
            Item={
                "user_id": str(user_id),
                "has_started": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    def has_user_started(self, user_id: int) -> bool:
        table = self._dynamodb.Table(self._config.started_users_table)
        response = table.get_item(Key={"user_id": str(user_id)})
        return response.get("Item", {}).get("has_started", False)

    def mark_user_as_paid(self, user_id: int, full_name: str, username: str | None, transaction_no: str) -> None:
        table = self._dynamodb.Table(self._config.paid_users_table)
        table.put_item(
            Item={
                "user_id": str(user_id),
                "name": full_name,
                "username": username or "N/A",
                "has_paid": True,
                "payment_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_no": transaction_no,
            }
        )

    def has_user_paid(self, user_id: int) -> bool:
        table = self._dynamodb.Table(self._config.paid_users_table)
        response = table.get_item(Key={"user_id": str(user_id)})
        return response.get("Item", {}).get("has_paid", False)
