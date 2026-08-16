import os
import threading
import logging
from urllib.parse import quote

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from dto import AvitoConfig
from parser_cls import AvitoParse


BOT_TOKEN = os.environ["BOT_TOKEN"]

# Твой Telegram ID
USER_ID = 437716810


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================================================
# RENDER WEB SERVER
# =========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Avito Hunter is running!"


@web_app.route("/health")
def health():
    return "OK"


def run_web_server():
    port = int(os.environ.get("PORT", "10000"))

    web_app.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# AVITO URL
# =========================================================

def build_avito_url(
    query: str,
    min_price: int,
    max_price: int
) -> str:

    return (
        "https://www.avito.ru/omsk"
        "?q=" + quote(query)
        + f"&pmin={min_price}"
        + f"&pmax={max_price}"
    )


# =========================================================
# AVITO PARSER
# =========================================================

def run_avito_parser(
    query: str,
    min_price: int,
    max_price: int
):

    url = build_avito_url(
        query,
        min_price,
        max_price
    )

    logging.info(
        "Запуск Avito Parser: %s",
        url
    )

    config = AvitoConfig(
        urls=[url],

        min_price=min_price,
        max_price=max_price,

        count=2,

        # Telegram
        tg_token=BOT_TOKEN,
        tg_chat_id=[str(USER_ID)],
        tg_only_text=True,

        # Фильтрация
        keys_word_white_list=[],
        keys_word_black_list=[],
        seller_black_list=[],

        geo="Омск",

        # Поведение
        max_age=0,
        max_count_of_retry=5,
        retry_delay=5,
        timeout=30,

        pause_general=5,
        pause_between_links=2,

        ignore_reserv=True,
        ignore_promotion=False,

        # Один запуск
        one_time_start=True,

        # Не нужен Excel
        save_xlsx=False,

        # Сначала HTTP
        use_webdriver=False,

        # Без платного bypass API
        use_bypass_api=False,
        cookies_api_key=None,

        # Без своих cookies
        use_own_cookies=False,

        parse_views=False,
        parse_phone=False,

        proxy_notifier=None,

        block_threshold=3,
    )

    try:

        parser = AvitoParse(config)

        parser.parse()

        logging.info(
            "Avito Parser завершил работу"
        )

    except Exception as error:

        logging.exception(
            "Ошибка Avito Parser"
        )

        logging.error(
            "Ошибка: %s",
            error
        )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter работает!\n\n"

        "/search товар мин_цена макс_цена\n"
        "/test — проверить бота\n"
        "/id — узнать Telegram ID\n\n"

        "Пример:\n"
        "/search видеокарта 5000 15000"
    )


# =========================================================
# /ID
# =========================================================

async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


# =========================================================
# /TEST
# =========================================================

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


# =========================================================
# /SEARCH
# =========================================================

async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:

        await update.message.reply_text(
            "❌ Формат команды:\n\n"
            "/search видеокарта 5000 15000"
        )

        return

    try:

        min_price = int(
            context.args[-2]
        )

        max_price = int(
            context.args[-1]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Цены должны быть числами."
        )

        return

    query = " ".join(
        context.args[:-2]
    )

    if min_price < 0:
        min_price = 0

    if max_price <= min_price:

        await update.message.reply_text(
            "❌ Максимальная цена должна "
            "быть больше минимальной."
        )

        return

    await update.message.reply_text(
        "🔎 Запускаю поиск Avito...\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽\n"
        "📍 Омск\n\n"
        "⏳ Парсер начал работу."
    )

    thread = threading.Thread(
        target=run_avito_parser,
        args=(
            query,
            min_price,
            max_price
        ),
        daemon=True
    )

    thread.start()


# =========================================================
# MAIN
# =========================================================

def main():

    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            get_id
        )
    )

    app.add_handler(
        CommandHandler(
            "test",
            test
        )
    )

    app.add_handler(
        CommandHandler(
            "search",
            search
        )
    )

    logging.info(
        "Avito Hunter started"
    )

    app.run_polling()


if __name__ == "__main__":
    main()