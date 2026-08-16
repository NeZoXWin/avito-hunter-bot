
    import os
import logging
import threading

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

# -------------------------
# Render health server
# -------------------------

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


# -------------------------
# Avito test
# -------------------------

def get_avito():

    url = "https://www.avito.ru/omsk"

    params = {
        "q": "видеокарта"
    }

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
        "Connection": "keep-alive",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )

    return response


# -------------------------
# /start
# -------------------------

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
        "/id — Telegram ID\n"
        "/testavito — проверить Avito\n"
    )


# -------------------------
# /id
# -------------------------

async def get_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Твой Telegram ID: "
        f"{update.effective_user.id}"
    )


# -------------------------
# /testavito
# -------------------------

async def test_avito(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🔎 Проверяю подключение к Avito..."
    )

    try:

        response = get_avito()

        status = response.status_code
        size = len(response.text)

        if status == 200:

            await update.message.reply_text(
                "✅ Avito ответил!\n\n"
                f"HTTP: {status}\n"
                f"Размер страницы: {size:,} символов\n\n"
                "Следующий этап — достать "
                "из страницы объявления."
            )

        else:

            await update.message.reply_text(
                "⚠️ Avito ответил.\n\n"
                f"HTTP: {status}\n"
                f"Размер ответа: {size:,} символов\n\n"
                "Это уже не ошибка Telegram-бота."
            )

        logging.info(
            "Avito HTTP=%s SIZE=%s",
            status,
            size
        )

    except Exception as error:

        logging.exception(
            "Avito request failed"
        )

        await update.message.reply_text(
            "❌ Ошибка запроса к Avito:\n\n"
            f"{error}"
        )


# -------------------------
# Main
# -------------------------

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

    logging.info(
        "Avito Hunter starting..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()