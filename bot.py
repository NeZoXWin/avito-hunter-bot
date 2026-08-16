import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter запущен!\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/id — показать ID\n"
        "/watch — добавить товар в мониторинг\n"
        "/list — список мониторинга\n"
    )


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Твой Telegram ID: {update.effective_user.id}"
    )


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "Например:\n/watch Ryzen 5 5600 5000"
        )
        return

    query = " ".join(context.args)

    await update.message.reply_text(
        f"🔎 Добавил в мониторинг:\n\n{query}\n\n"
        "Мониторинг пока тестовый."
    )


async def list_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "📋 Пока активных поисков нет."
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("list", list_watch))

    app.run_polling()


if __name__ == "__main__":
    main()