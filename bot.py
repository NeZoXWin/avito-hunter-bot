import os
import logging
import threading
from urllib.parse import quote

from flask import Flask
from curl_cffi import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810


# =========================================================
# RENDER
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
# AVITO REQUEST
# =========================================================

def avito_request(query):
    """
    Запрос к поиску Avito.
    Используем прямой URL, как в успешном тесте.
    """

    search_url = (
        "https://www.avito.ru/omsk"
        "?q=" + quote(query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),

        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),

        "Accept-Language": "ru-RU,ru;q=0.9",

        "Accept-Encoding": "gzip, deflate, br",

        "Connection": "keep-alive",

        "Upgrade-Insecure-Requests": "1",
    }

    logging.info(
        "Avito URL: %s",
        search_url
    )

    response = requests.get(
        search_url,
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )

    logging.info(
        "Avito HTTP: %s",
        response.status_code
    )

    logging.info(
        "Avito response size: %s",
        len(response.text)
    )

    return response


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
        "🤖 Avito Hunter запущен!\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/id — показать ID\n"
        "/testavito — проверить Avito\n"
        "/search — поиск Avito\n\n"
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
        f"Твой Telegram ID: "
        f"{update.effective_user.id}"
    )


# =========================================================
# /TESTAVITO
# =========================================================

async def test_avito(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🔎 Проверяю Avito..."
    )

    try:

        response = avito_request(
            "видеокарта"
        )

        if response.status_code == 200:

            await update.message.reply_text(
                "✅ Avito ответил!\n\n"
                f"HTTP: {response.status_code}\n"
                f"Размер страницы: "
                f"{len(response.text):,} символов"
            )

        else:

            await update.message.reply_text(
                "⚠️ Avito ответил:\n\n"
                f"HTTP: {response.status_code}\n"
                f"Размер ответа: "
                f"{len(response.text):,} символов"
            )

    except Exception as error:

        logging.exception(
            "Avito test error"
        )

        await update.message.reply_text(
            "❌ Ошибка:\n\n"
            f"{error}"
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
            "Использование:\n\n"
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
            "❌ Последние два значения "
            "должны быть ценами.\n\n"
            "Например:\n"
            "/search видеокарта 5000 15000"
        )

        return

    query = " ".join(
        context.args[:-2]
    )

    await update.message.reply_text(
        "🔎 Ищу на Avito:\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽\n\n"
        "⏳ Отправляю запрос..."
    )

    try:

        response = avito_request(
            query
        )

        if response.status_code != 200:

            await update.message.reply_text(
                "❌ Avito не отдал страницу.\n\n"
                f"HTTP: {response.status_code}\n"
                f"Размер ответа: "
                f"{len(response.text):,} символов"
            )

            return

        await update.message.reply_text(
            "✅ Поисковая страница получена!\n\n"
            f"HTTP: {response.status_code}\n"
            f"Размер страницы: "
            f"{len(response.text):,} символов\n\n"
            "📦 Следующий этап — "
            "извлечение объявлений."
        )

    except Exception as error:

        logging.exception(
            "Search error"
        )

        await update.message.reply_text(
            "❌ Ошибка запроса:\n\n"
            f"{error}"
        )


# =========================================================
# MAIN
# =========================================================

def main():

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
            "testavito",
            test_avito
        )
    )

    app.add_handler(
        CommandHandler(
            "search",
            search
        )
    )

    logging.info(
        "Avito Hunter starting..."