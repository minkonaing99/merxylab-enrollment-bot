from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExtractedFields:
    time: Optional[str]
    transaction_id: Optional[str]
    amount: Optional[str]
    name: Optional[str]
    notes: Optional[str]


@dataclass(frozen=True)
class PaymentProcessingResult:
    success: bool
    message: str
    summary_markdown: Optional[str] = None
    transaction_no: Optional[str] = None
