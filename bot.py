import os
import sys
import threading
import logging
from urllib.parse import quote

import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Папка с parser_avito, которую Render скачивает при сборке
sys.path.insert(0, "parser_avito")

from dto import AvitoConfig
from parser_cls import AvitoParse


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]

USER_ID = 437716810


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# WEB SERVER ДЛЯ RENDER
# =========================

app_web = Flask(__name__)


@app_web.route("/")
def home():
    return "Avito Hunter is running!"


@app_web.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", "10000"))

    app_web.run(
        host="0.0.0.0",
        port=port
    )


# =========================
# AVITO URL
# =========================

def build_url(query, min_price, max_price):

    return (
        "https://www.avito.ru/omsk"
        f"?q={quote(query)}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )


# =========================
# ЗАПУСК PARSER_AVITO
# =========================

def run_parser(query, min_price, max_price):

    url = build_url(
        query,
        min_price,
        max_price
    )

    logging.info(
        "Avito URL: %s",
        url
    )

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

        logging.info(
            "Starting AvitoParse"
        )

        parser.parse()

        logging.info(
            "AvitoParse finished"
        )

    except Exception as e:

        logging.exception(
            "Avito parser error: %s",
            e
        )


# =========================
# /START
# =========================

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
        "/id\n"
        "/avito_test\n\n"

        "Пример:\n"
        "/search видеокарта 5000 15000"
    )


# =========================
# /ID
# =========================

async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Telegram ID: {update.effective_user.id}"
    )


# =========================
# /TEST
# =========================

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


# =========================
# /AVITO_TEST
# =========================

async def avito_test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🔎 Проверяю прямое подключение Render → Avito..."
    )

    url = "https://www.avito.ru/omsk"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0.0.0 "
            "Safari/537.36"
        ),

        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),

        "Accept-Language": (
            "ru-RU,ru;q=0.9,en;q=0.8"
        ),

        "Connection": "keep-alive",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        logging.info(
            "Avito direct test HTTP: %s",
            response.status_code
        )

        logging.info(
            "Avito direct test size: %s",
            len(response.text)
        )

        await update.message.reply_text(
            "📡 Результат проверки Avito:\n\n"

            f"HTTP: {response.status_code}\n"
            f"Размер страницы: "
            f"{len(response.text):,} символов\n\n"

            "URL:\n"
            f"{url}"
        )

    except Exception as e:

        logging.exception(
            "Avito direct test error"
        )

        await update.message.reply_text(
            "❌ Ошибка подключения к Avito:\n\n"
            f"{type(e).__name__}: {e}"
        )


# =========================
# /SEARCH
# =========================

async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:

        await update.message.reply_text(
            "❌ Неправильный формат.\n\n"

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

            "Пример:\n"
            "/search видеокарта 5000 15000"
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


# =========================
# MAIN
# =========================

def main():

    # Запускаем веб-сервер Render
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    # Создаём Telegram-приложение
    telegram_app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Команды
    telegram_app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "id",
            get_id
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "test",
            test
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "avito_test",
            avito_test
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "search",
            search
        )
    )

    logging.info(
        "Avito Hunter started"
    )

    # Запускаем Telegram polling
    telegram_app.run_polling()


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    main()