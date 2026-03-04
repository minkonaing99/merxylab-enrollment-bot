from __future__ import annotations

import logging

from bot.adapters.aws_store import AwsDataStore
from bot.adapters.ocr import extract_fields, extract_text_from_image
from bot.config import AppConfig
from bot.models.payment import ExtractedFields, PaymentProcessingResult

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, config: AppConfig, store: AwsDataStore) -> None:
        self.config = config
        self.store = store

    def ensure_started(self, user_id: int) -> None:
        if not self.store.has_user_started(user_id):
            self.store.mark_user_as_started(user_id)

    def has_paid(self, user_id: int) -> bool:
        return self.store.has_user_paid(user_id)

    def has_invited(self, user_id: int) -> bool:
        return self.store.has_user_been_invited(user_id)

    def mark_invited(self, user_id: int) -> None:
        self.store.mark_user_as_invited(user_id)

    def process_payment_image(self, user_id: int, full_name: str, username: str | None, local_path: str, filename: str) -> PaymentProcessingResult:
        extracted_text = extract_text_from_image(local_path)
        fields = extract_fields(extracted_text)

        if not fields.transaction_id or not fields.amount:
            return PaymentProcessingResult(
                success=False,
                message=(
                    "Could not extract valid payment details. Please send a clear KBZPay history screenshot "
                    "and try /payment_confirm again."
                ),
            )

        validation_error = self._validate_fields(fields)
        if validation_error:
            return PaymentProcessingResult(success=False, message=validation_error)

        transaction_no = fields.transaction_id
        if self.store.is_duplicate_transaction(transaction_no):
            return PaymentProcessingResult(
                success=False,
                message="This transaction has already been used. If this is a mistake, contact support.",
            )

        self.store.upload_payment_image(local_path, filename)
        self.store.log_payment(
            user_id=user_id,
            username=username,
            file_name=filename,
            extracted_data={
                "Transaction No": transaction_no,
                "Amount": fields.amount,
                "Transaction Time": fields.time,
                "Notes": fields.notes,
            },
        )
        self.store.mark_user_as_paid(user_id=user_id, full_name=full_name, username=username, transaction_no=transaction_no)

        summary = self._build_summary(transaction_no, fields)
        return PaymentProcessingResult(
            success=True,
            message="Payment successfully verified.",
            summary_markdown=summary,
            transaction_no=transaction_no,
        )

    def _validate_fields(self, fields: ExtractedFields) -> str | None:
        name_field = fields.name or ""
        if self.config.expected_receiver_name not in name_field or self.config.expected_receiver_last4 not in name_field:
            return (
                "Payment must be sent to the registered KBZPay account: "
                f"{self.config.expected_receiver_name} ({self.config.expected_receiver_last4})."
            )

        amount_str = (fields.amount or "").replace("Ks", "").replace(",", "").strip()
        if amount_str.startswith("-"):
            amount_str = amount_str[1:]

        try:
            amount_value = float(amount_str)
        except ValueError:
            return "Could not read the payment amount from the screenshot."

        if amount_value < self.config.min_amount_ks:
            return f"Payment amount must be at least {self.config.min_amount_ks} Ks."

        return None

    @staticmethod
    def _build_summary(transaction_no: str, fields: ExtractedFields) -> str:
        return (
            f"*Transaction No:* `{transaction_no}`\n"
            f"*Amount:* `{fields.amount}`\n"
            f"*Time:* `{fields.time}`\n"
            f"*Notes:* `{fields.notes or 'N/A'}`"
        )
