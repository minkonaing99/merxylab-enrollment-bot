from __future__ import annotations

import logging
import platform
import re

from PIL import Image
import pytesseract

from bot.models.payment import ExtractedFields

logger = logging.getLogger(__name__)


def configure_tesseract() -> None:
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    else:
        pytesseract.pytesseract.tesseract_cmd = "tesseract"


def clean_kbz_ocr_text(text: str) -> str:
    pattern = (
        r"(?i)ae\s*Thank you for using KBZPay!\s*The e-receipt only means you already paid for the\s*"
        r"merchant\.?\s*You need to confirm the final transaction status\s*with merchant\.?"
    )
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="eng")
    if not re.search(r"[a-zA-Z]", text):
        text = pytesseract.image_to_string(image, lang="mya")

    text = clean_kbz_ocr_text(text)
    logger.debug("OCR text extracted")
    return text


def extract_fields(text: str) -> ExtractedFields:
    result: dict[str, str | None] = {
        "time": None,
        "transaction_id": None,
        "amount": None,
        "name": None,
        "notes": None,
    }

    text = re.sub(r"\s+", " ", text).strip()

    eng_time = re.search(r"Transaction Time\s*([\d/]+ [\d:]+)", text)
    eng_id = re.search(r"Transaction No\.?\s*(\d{16,20})", text)
    eng_amount = re.search(r"Amount\s*(-?\d[\d,]*\.?\d*)\s*Ks", text)

    if eng_time or eng_id or eng_amount:
        if eng_time:
            result["time"] = eng_time.group(1)
        if eng_id:
            result["transaction_id"] = eng_id.group(1)
        if eng_amount:
            amount = eng_amount.group(1).replace(",", "")
            result["amount"] = f"{amount} Ks"

        name_match = re.search(r"Transfer To\s*([A-Z][A-Za-z\s]+)\s*[\(<]?[*#]+(\d{4})[\)>]?", text)
        if not name_match:
            name_match = re.search(r"Transfer To\s*([A-Z][A-Za-z\s]+)\s*[*#]+\d{4}", text)
        if name_match:
            result["name"] = f"{name_match.group(1).strip()} ({name_match.group(2) if len(name_match.groups()) > 1 else name_match.group(1).split()[-1]})"

        notes_match = re.search(r"Notes\s*([^\n]+?)(?=\s*(?:Transaction|Transfer|Amount|$))", text)
        if notes_match:
            result["notes"] = notes_match.group(1).strip()
        else:
            amount_pos = text.find("Amount") if "Amount" in text else -1
            if amount_pos > -1:
                notes_part = text[amount_pos:].split("Ks")[-1].strip()
                if notes_part and not any(x in notes_part for x in ["Transaction", "Transfer"]):
                    result["notes"] = notes_part.split("\n")[0].strip()

        return ExtractedFields(**result)

    my_time = re.search(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})", text)
    my_id = re.search(r"(\d{16,20})", text)
    my_amount = re.search(r"(-?\d[\d,]*\.?\d*)\s*Ks", text)

    if my_time or my_id or my_amount:
        if my_time:
            result["time"] = my_time.group(1)
        if my_id:
            result["transaction_id"] = my_id.group(1)
        if my_amount:
            amount = my_amount.group(1).replace(",", "")
            result["amount"] = f"{amount} Ks"

        name_match = re.search(r"([A-Z][A-Za-z\s]+)\s*[\(<]?[*#]+(\d{4})[\)>]?", text)
        if not name_match:
            name_match = re.search(r"([A-Z][A-Za-z\s]+)\s*[*#]+\d{4}", text)
        if name_match:
            result["name"] = f"{name_match.group(1).strip()} ({name_match.group(2) if len(name_match.groups()) > 1 else name_match.group(1).split()[-1]})"

        amount_pos = text.find("Ks") if "Ks" in text else -1
        if amount_pos > -1:
            notes_part = text[amount_pos + 2 :].strip()
            if notes_part and not any(x in notes_part for x in ["Transaction", "Transfer"]):
                result["notes"] = notes_part.split("\n")[0].strip()

        return ExtractedFields(**result)

    time_match = re.search(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})", text)
    id_match = re.search(r"(\d{16,20})", text)
    amount_match = re.search(r"(-?\d[\d,]*\.?\d*)\s*Ks", text)

    if time_match:
        result["time"] = time_match.group(1)
    if id_match:
        result["transaction_id"] = id_match.group(1)
    if amount_match:
        amount = amount_match.group(1).replace(",", "")
        result["amount"] = f"{amount} Ks"

    name_match = re.search(r"([A-Z][A-Za-z\s]+)\s*[\(<]?[*#]+(\d{4})[\)>]?", text)
    if not name_match:
        name_match = re.search(r"([A-Z][A-Za-z\s]+)\s*[*#]+\d{4}", text)
    if name_match:
        result["name"] = f"{name_match.group(1).strip()} ({name_match.group(2) if len(name_match.groups()) > 1 else name_match.group(1).split()[-1]})"

    return ExtractedFields(**result)
