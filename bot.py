import os
import sys
import threading
import logging

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

PARSER_PATH = "/opt/parser_avito"

if PARSER_PATH not in sys.path:
    sys.path.insert(0, PARSER_PATH)

BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Avito Hunter is running!"


@web_app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(
        host="0.0.0.0",
        port=port
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter работает!\n\n"
        "/search товар мин_цена макс_цена\n"
        "/test — проверка\n"
        "/id — Telegram ID\n\n"
        "Пример:\n"
        "/search видеокарта 5000 15000"
    )


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "✅ Telegram-бот работает.\n"
        "Render работает.\n"
        "Следующим этапом подключим Avito."
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат:\n"
            "/search видеокарта 5000 15000"
        )
        return

    try:
        min_price = int(context.args[-2])
        max_price = int(context.args[-1])
    except ValueError:
        await update.message.reply_text(
            "❌ Цена должна быть числом."
        )
        return

    query = " ".join(context.args[:-2])

    await update.message.reply_text(
        "🔎 Получил запрос!\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–{max_price:,} ₽\n"
        f"📍 Омск\n\n"
        "⏳ Подключаю парсер Avito..."
    )

    # Пока только проверяем, что оригинальный
    # репозиторий действительно доступен.
    try:

        parser_file = os.path.join(
            PARSER_PATH,
            "parser_cls.py"
        )

        if os.path.exists(parser_file):

            await update.message.reply_text(
                "✅ Оригинальный parser_cls.py найден.\n\n"
                "Следующим шагом подключим его "
                "к поиску."
            )

        else:

            await update.message.reply_text(
                "❌ parser_cls.py не найден в "
                "скачанном репозитории."
            )

    except Exception as error:

        await update.message.reply_text(
            f"❌ Ошибка:\n{error}"
        )


def main():

    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("id", get_id)
    )

    app.add_handler(
        CommandHandler("test", test)
    )

    app.add_handler(
        CommandHandler("search", search)
    )

    logging.info("Avito Hunter started")

    app.run_polling()


if __name__ == "__main__":
    main()