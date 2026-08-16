import os
import sys
import threading
import logging
from urllib.parse import quote

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

sys.path.insert(0, "parser_avito")

from dto import AvitoConfig
from parser_cls import AvitoParse


BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app_web = Flask(__name__)


@app_web.route("/")
def home():
    return "Avito Hunter is running!"


@app_web.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app_web.run(host="0.0.0.0", port=port)


def build_url(query, min_price, max_price):
    return (
        "https://www.avito.ru/omsk"
        f"?q={quote(query)}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )


def run_parser(query, min_price, max_price):

    url = build_url(
        query,
        min_price,
        max_price
    )

    logging.info("Avito URL: %s", url)

    try:

        config = AvitoConfig(
            urls=[url],
            min_price=min_price,
            max_price=max_price,

            count=10,

            tg_token=BOT_TOKEN,
            tg_chat_id=[str(USER_ID)],
            tg_only_text=True,

            keys_word_white_list=[],
            keys_word_black_list=[],
            seller_black_list=[],

            geo="Омск",

            max_age=0,
            max_count_of_retry=5,
            retry_delay=5,
            timeout=30,

            pause_general=5,
            pause_between_links=2,

            ignore_reserv=True,
            ignore_promotion=False,

            one_time_start=True,
            save_xlsx=False,

            use_webdriver=False,

            use_bypass_api=False,
            cookies_api_key=None,
            use_own_cookies=False,

            parse_views=False,
            parse_phone=False,

            proxy_notifier=None,
            block_threshold=3,
        )

        parser = AvitoParse(config)

        logging.info("Starting AvitoParse")

        parser.parse()

        logging.info("AvitoParse finished")

    except Exception as e:

        logging.exception(
            "Avito parser error: %s",
            e
        )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter работает!\n\n"
        "/search товар мин_цена макс_цена\n"
        "/test\n"
        "/id\n\n"
        "Пример:\n"
        "/search видеокарта 5000 15000"
    )


async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "✅ Telegram-бот работает.\n"
        "✅ Render работает.\n"
        "✅ Avito Parser подключён."
    )


async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:

        await update.message.reply_text(
            "❌ Формат:\n"
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

    query = " ".join(
        context.args[:-2]
    )

    if max_price <= min_price:

        await update.message.reply_text(
            "❌ Максимальная цена должна "
            "быть больше минимальной."
        )

        return

    await update.message.reply_text(
        "🔎 Ищу на Avito...\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽\n"
        "📍 Омск\n\n"
        "⏳ Загружаю объявления..."
    )

    thread = threading.Thread(
        target=run_parser,
        args=(
            query,
            min_price,
            max_price
        ),
        daemon=True
    )

    thread.start()


def main():

    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    telegram_app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    telegram_app.add_handler(
        CommandHandler("start", start)
    )

    telegram_app.add_handler(
        CommandHandler("id", get_id)
    )

    telegram_app.add_handler(
        CommandHandler("test", test)
    )

    telegram_app.add_handler(
        CommandHandler("search", search)
    )

    logging.info("Avito Hunter started")

    telegram_app.run_polling()


if __name__ == "__main__":
    main()