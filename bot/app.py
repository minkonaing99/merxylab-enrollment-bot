from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder

from bot.adapters.aws_store import AwsDataStore
from bot.adapters.ocr import configure_tesseract
from bot.config import ConfigError, load_config
from bot.handlers.commands import BotHandlers, build_handlers
from bot.services.payment_service import PaymentService


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        config = load_config()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    configure_tesseract()

    store = AwsDataStore(config)
    service = PaymentService(config=config, store=store)
    bot_handlers = BotHandlers(service=service, channel_id=config.channel_id, admin_channel_id=config.admin_channel_id)

    app = ApplicationBuilder().token(config.bot_token).build()
    command_handlers, conversation_handler = build_handlers(bot_handlers)

    for handler in command_handlers:
        app.add_handler(handler)
    app.add_handler(conversation_handler)

    logging.getLogger(__name__).info("merxylab bot is running")
    app.run_polling()


if __name__ == "__main__":
    run()
