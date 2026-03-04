# MerxyLab Enrollment Bot

Telegram bot for course enrollment that verifies KBZPay payment screenshots using OCR, stores payment records in AWS DynamoDB/S3, and sends a one-time invite link after successful verification.

## Bot File

Main entry file:

- `merxy_lab_bot.py`

Internal package layout:

- `bot/app.py` - app wiring and startup
- `bot/config.py` - environment-based config + validation
- `bot/handlers/` - Telegram command/conversation handlers
- `bot/services/` - business logic orchestration
- `bot/adapters/` - AWS and OCR integrations
- `bot/models/` - typed data models

## Requirements

- Python 3.10+
- Tesseract OCR installed on OS
- Telegram bot token
- AWS access to DynamoDB and S3

Install Python packages:

```bash
pip install -r requirements.txt
```

## Tesseract Installation

### Windows
- Install Tesseract OCR (default path should be `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### Linux
- Install `tesseract-ocr` and ensure `tesseract` is available in `PATH`

## Configuration

This project uses environment variables.

Required variables:

```bash
BOT_TOKEN=your_telegram_bot_token
REGION_NAME=ap-southeast-1
BUCKET_NAME=your_s3_bucket
```

Optional variables:

```bash
MIN_AMOUNT_KS=5000
CHANNEL_ID=your_private_course_channel_id
ADMIN_CHANNEL_ID=your_admin_channel_id
EXPECTED_RECEIVER_NAME=U MIN KO NAING
EXPECTED_RECEIVER_LAST4=3307
PAYMENT_TABLE=merxylab-payment
INVITED_USERS_TABLE=merxylab-invited_users
STARTED_USERS_TABLE=merxylab-startedusers
PAID_USERS_TABLE=merxylab-paid_users
```

PowerShell example:

```powershell
$env:BOT_TOKEN="your_telegram_bot_token"
$env:REGION_NAME="ap-southeast-1"
$env:BUCKET_NAME="your_s3_bucket"
```

## AWS Resources Expected

DynamoDB tables used by the bot:
- `merxylab-payment`
- `merxylab-invited_users`
- `merxylab-startedusers`
- `merxylab-paid_users`

S3 path used:
- `payments/<generated_filename>.png`

## Run

Recommended:

```bash
python merxy_lab_bot.py
```

## Core Telegram Commands

- `/start` - start bot and log starter user
- `/pay` - show KBZPay payment instructions
- `/payment_confirm` - begin screenshot verification flow
- `/help` - show bot commands
- `/end` - end session
- `/cancel` - cancel payment confirmation conversation

## Notes

- OCR quality depends heavily on screenshot clarity and language data in Tesseract.
- The bot validates transaction fields and blocks reused transaction numbers.
- Access links are generated as single-use invite links.
