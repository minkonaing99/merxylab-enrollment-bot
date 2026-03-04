from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

AWAITING_IMAGE = 1


class BotHandlers:
    def __init__(self, service: PaymentService, channel_id: Optional[int], admin_channel_id: Optional[int]) -> None:
        self.service = service
        self.channel_id = channel_id
        self.admin_channel_id = admin_channel_id

    async def _notify_admin(self, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        if self.admin_channel_id is None:
            return
        await context.bot.send_message(chat_id=self.admin_channel_id, text=text, parse_mode="Markdown")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.service.ensure_started(user_id)

        await update.message.reply_text(
            "Hello, welcome from Merxy's Lab.\n"
            "This assistant will help you buy the course.\n\n"
            "If you decide to buy, click /pay."
        )

    async def pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.service.has_paid(user_id):
            await update.message.reply_text(
                "Thank you. Your payment has already been confirmed.\n\n"
                "If you have not received access yet, contact support."
            )
            return

        await update.message.reply_text(
            "Currently I can only accept KBZPay\n\n"
            "Amount: 5000 Ks\n"
            "Name: Min Ko Naing\n"
            "Phone: 09787753307\n"
            "Notes: Shopping, payment\n\n"
            "After transfer, click /payment_confirm."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Available Commands:\n"
            "/start - Start chatting with the bot\n"
            "/pay - Payment instructions\n"
            "/payment_confirm - Confirm your payment\n"
            "/help - Show this help message\n"
            "/end - End the session"
        )

    async def end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bot session ended. You can /start again anytime.")
        return ConversationHandler.END

    async def start_payment_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.service.has_paid(user_id):
            await update.message.reply_text(
                "Thank you. Your payment has already been confirmed.\n\n"
                "If you need help, contact support."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Please send your KBZPay payment screenshot from History section.\n\n"
            "Important:\n"
            "1. Make sure complete transaction details are visible\n"
            "2. Send the original image (not cropped or edited)\n"
            "3. The image should be clear and readable\n\n"
            "You have 2 minutes to send the image or this session will timeout."
        )
        return AWAITING_IMAGE

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Payment confirmation cancelled.")
        return ConversationHandler.END

    async def handle_payment_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        photo_file = await update.message.photo[-1].get_file()
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{now_str}.png"

        await photo_file.download_to_drive(filename)

        try:
            result = self.service.process_payment_image(
                user_id=user_id,
                full_name=user.full_name,
                username=user.username,
                local_path=filename,
                filename=filename,
            )

            if not result.success:
                await update.message.reply_text(result.message)
                await self._notify_admin(
                    context,
                    (
                        "*Payment Validation Failed*\n"
                        f"*User ID:* `{user_id}`\n"
                        f"*File:* `{filename}`\n"
                        f"*Reason:* `{result.message}`"
                    ),
                )
                return ConversationHandler.END

            await update.message.reply_text(result.message)
            await update.message.reply_text(f"*Payment Details:*\n{result.summary_markdown}", parse_mode="Markdown")

            if self.channel_id is not None and not self.service.has_invited(user_id):
                try:
                    invite_link = await context.bot.create_chat_invite_link(chat_id=self.channel_id, member_limit=1)
                    await update.message.reply_text(
                        "Here is your exclusive access link (valid for 24 hours):\n"
                        f"{invite_link.invite_link}\n\n"
                        "This link can only be used once."
                    )
                    self.service.mark_invited(user_id)
                except Exception as exc:
                    logger.error("Failed to create invite link: %s", exc)
                    await update.message.reply_text(
                        "Payment verified but failed to generate access link. Contact support with your transaction number."
                    )

            await self._notify_admin(
                context,
                (
                    "*New Payment Confirmed*\n\n"
                    f"*User:* `{user.full_name}` (`{user_id}`)\n"
                    f"*File:* `{filename}`\n"
                    f"*Transaction No:* `{result.transaction_no}`\n"
                    f"*Invite Sent:* `{self.service.has_invited(user_id)}`"
                ),
            )
        except Exception as exc:
            logger.exception("[ERROR] Failed to process payment image")
            await update.message.reply_text("An error occurred while processing the image.")
            await self._notify_admin(
                context,
                (
                    "*Payment Error*\n\n"
                    f"*User ID:* `{user_id}`\n"
                    f"*Error:* `{str(exc)}`"
                ),
            )
        finally:
            if os.path.exists(filename):
                os.remove(filename)

        return ConversationHandler.END


def build_handlers(bot_handlers: BotHandlers) -> tuple[list[CommandHandler], ConversationHandler]:
    command_handlers = [
        CommandHandler("start", bot_handlers.start),
        CommandHandler("pay", bot_handlers.pay),
        CommandHandler("help", bot_handlers.help_command),
        CommandHandler("end", bot_handlers.end),
    ]

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("payment_confirm", bot_handlers.start_payment_confirm)],
        states={AWAITING_IMAGE: [MessageHandler(filters.PHOTO, bot_handlers.handle_payment_image)]},
        fallbacks=[CommandHandler("cancel", bot_handlers.cancel)],
        conversation_timeout=120,
    )
    return command_handlers, conversation_handler
