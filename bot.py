import os
import json
import logging
import requests
import threading

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

TOKEN = os.environ["BOT_TOKEN"]
PARSE_API_KEY = os.environ["PARSE_API_KEY"]
USER_ID = 437716810

WATCH_FILE = "watchlist.json"

PARSE_URL = (
    "https://api.parse.bot/"
    "scraper/b54ad12b-11e9-48dd-a911-3dc6465949c4/"
    "search_items"
)

# -------------------------
# Render HTTP
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
# Watchlist
# -------------------------

def load_watchlist():
    if not os.path.exists(WATCH_FILE):
        return []

    try:
        with open(WATCH_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_watchlist(watchlist):
    with open(WATCH_FILE, "w", encoding="utf-8") as file:
        json.dump(
            watchlist,
            file,
            ensure_ascii=False,
            indent=2
        )


# -------------------------
# Parse.bot / Avito
# -------------------------

def search_avito(
    query,
    min_price,
    max_price
):
    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    params = {
        "page": 1,
        "query": query,
        "category": "elektronika",
        "location": "omsk",
        "price_min": min_price,
        "price_max": max_price
    }

    logging.info(
        "Parse.bot request: %s",
        params
    )

    try:
        response = requests.get(
            PARSE_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        logging.info(
            "Parse.bot response: HTTP %s",
            response.status_code
        )

        if response.status_code != 200:
            logging.error(
                "Parse.bot error: %s",
                response.text[:2000]
            )

            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text
            }

        data = response.json()

        return {
            "status": "ok",
            "data": data
        }

    except Exception as error:
        logging.exception(
            "Parse.bot request failed"
        )

        return {
            "status": "error",
            "message": str(error)
        }


# -------------------------
# Telegram /start
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
        "/search — поиск Avito\n"
        "/watch — добавить мониторинг\n"
        "/list — список мониторингов\n"
        "/clear — очистить мониторинг"
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
# /search
# -------------------------

async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат:\n\n"
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

    await update.message.reply_text(
        "🔎 Ищу на Avito через API...\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽"
    )

    result = search_avito(
        query,
        min_price,
        max_price
    )

    if result["status"] != "ok":

        await update.message.reply_text(
            "❌ Parse.bot вернул ошибку.\n\n"
            f"HTTP: {result.get('code', '?')}\n\n"
            f"{result.get('message', '')[:1500]}"
        )

        return

    data = result["data"]

    items = data.get(
        "items",
        []
    )

    stats = data.get(
        "stats",
        {}
    )

    average_price = stats.get(
        "average_price"
    )

    if not items:

        await update.message.reply_text(
            "🔎 Объявлений не найдено.\n\n"
            f"Средняя цена: "
            f"{average_price or 'нет данных'}"
        )

        return

    text = (
        f"🔥 Найдено: {len(items)}\n"
    )

    if average_price:
        text += (
            f"📊 Средняя цена: "
            f"{average_price:,} ₽\n"
        )

    text += "\n"

    for index, item in enumerate(
        items,
        1
    ):
        title = item.get(
            "title",
            "Без названия"
        )

        price = item.get(
            "price",
            "Цена не указана"
        )

        url = item.get(
            "url",
            ""
        )

        text += (
            f"{index}. {title}\n"
            f"💰 {price} ₽\n"
            f"🔗 {url}\n\n"
        )

        if len(text) > 3500:
            break

    await update.message.reply_text(
        text
    )


# -------------------------
# /watch
# -------------------------

async def watch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат:\n\n"
            "/watch видеокарта 5000 15000"
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
            "должны быть ценами."
        )
        return

    query = " ".join(
        context.args[:-2]
    )

    watchlist = load_watchlist()

    watchlist.append({
        "query": query,
        "min_price": min_price,
        "max_price": max_price
    })

    save_watchlist(
        watchlist
    )

    await update.message.reply_text(
        "🔎 Добавил в мониторинг:\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽"
    )


# -------------------------
# /list
# -------------------------

async def list_watch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != USER_ID:
        return

    watchlist = load_watchlist()

    if not watchlist:
        await update.message.reply_text(
            "📋 Мониторингов пока нет."
        )
        return

    text = "📋 Мониторинги:\n\n"

    for index, item in enumerate(
        watchlist,
        1
    ):
        text += (
            f"{index}. {item['query']}\n"
            f"💰 {item['min_price']:,}–"
            f"{item['max_price']:,} ₽\n\n"
        )

    await update.message.reply_text(
        text
    )


# -------------------------
# /clear
# -------------------------

async def clear_watch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != USER_ID:
        return

    save_watchlist([])

    await update.message.reply_text(
        "🗑 Мониторинг очищен."
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
        .token(TOKEN)
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
            "search",
            search
        )
    )

    app.add_handler(
        CommandHandler(
            "watch",
            watch
        )
    )

    app.add_handler(
        CommandHandler(
            "list",
            list_watch
        )
    )

    app.add_handler(
        CommandHandler(
            "clear",
            clear_watch
        )
    )

    logging.info(
        "Avito Hunter starting..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()