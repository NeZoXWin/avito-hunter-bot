import os
import sys
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

# =========================================================
# Подключаем оригинальный Avito Parser
# =========================================================

PARSER_PATH = "/opt/parser_avito"

if PARSER_PATH not in sys.path:
    sys.path.insert(0, PARSER_PATH)

from dto import AvitoConfig
from parser_cls import AvitoParse


# =========================================================
# Настройки
# =========================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================================================
# Render HTTP server
# =========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Avito Hunter is running!"


@web_app.route("/health")
def health():
    return "OK"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))

    web_app.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# Формируем ссылку Avito
# =========================================================

def build_avito_url(
    query: str,
    min_price: int,
    max_price: int
) -> str:

    encoded_query = quote(
        query,
        safe=""
    )

    return (
        "https://www.avito.ru/omsk"
        f"?q={encoded_query}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )


# =========================================================
# Запуск настоящего парсера
# =========================================================

def run_parser(
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
        "Starting Avito parser: %s",
        url
    )

    config = AvitoConfig(

        # Ссылка поиска
        urls=[url],

        # Фильтр цены
        min_price=min_price,
        max_price=max_price,

        # Только один проход
        one_time_start=True,

        # Не сохраняем Excel
        save_xlsx=False,

        # Используем HTTP-клиент парсера
        # без запуска Chromium
        use_webdriver=False,

        # Telegram уведомления
        tg_token=BOT_TOKEN,
        tg_chat_id=[str(USER_ID)],

        # Базовые настройки
        count=1,
        max_count_of_retry=5,
        retry_delay=5,
        timeout=30,
        pause_general=5,
        pause_between_links=3,

        # Фильтры
        keys_word_white_list=[],
        keys_word_black_list=[],
        seller_black_list=[],

        # Не нужны
        parse_views=False,
        parse_phone=False,
        use_bypass_api=False,
        cookies_api_key=None,
        use_own_cookies=False,

        # Остальное
        ignore_reserv=True,
        ignore_promotion=False,
        geo="Омск",
        max_age=86400,
        debug_mode=0,
        output_dir="result",
        tg_only_text=False,
        block_threshold=3,
    )

    try:

        parser = AvitoParse(
            config
        )

        parser.parse()

        logging.info(
            "Avito parser finished"
        )

    except Exception as error:

        logging.exception(
            "Avito parser error"
        )


# =========================================================
# /start
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter\n\n"
        "Команды:\n\n"
        "/search товар мин_цена макс_цена\n"
        "/test — проверить бота\n"
        "/id — Telegram ID\n\n"
        "Пример:\n"
        "/search видеокарта 5000 15000"
    )


# =========================================================
# /id
# =========================================================

async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Твой Telegram ID: "
        f"{update.effective_user.id}"
    )


# =========================================================
# /test
# =========================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "✅ Telegram-бот работает.\n\n"
        "Парсер Avito подключён."
    )


# =========================================================
# /search
# =========================================================

async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:

        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Используй:\n"
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
            "❌ Цена должна быть числом.\n\n"
            "Например:\n"
            "/search видеокарта 5000 15000"
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

    url = build_avito_url(
        query,
        min_price,
        max_price
    )

    await update.message.reply_text(
        "🔎 Запускаю поиск Avito.\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽\n"
        f"📍 Омск\n\n"
        "⏳ Парсер начал работу.\n"
        "Если объявления найдутся — "
        "я пришлю их сюда."
    )

    # Парсер запускаем отдельно,
    # чтобы Telegram-бот продолжал отвечать
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


# =========================================================
# MAIN
# =========================================================

def main():

    # HTTP-сервер для Render
    server_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    server_thread.start()

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