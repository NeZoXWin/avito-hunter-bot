import os
import json
import logging
import threading
import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810
WATCH_FILE = "watchlist.json"

# -------------------------
# HTTP-сервер для Render
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
    web_app.run(host="0.0.0.0", port=port)


# -------------------------
# Мониторинги
# -------------------------

def load_watchlist():
    if not os.path.exists(WATCH_FILE):
        return []

    try:
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_watchlist(watchlist):
    with open(WATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


# -------------------------
# Поиск Avito
# -------------------------

def search_avito(query, min_price, max_price):
    url = (
        "https://www.avito.ru/omsk"
        f"?q={quote_plus(query)}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        logging.info(
            "Avito response: status=%s length=%s url=%s",
            response.status_code,
            len(response.text),
            response.url
        )

        if response.status_code != 200:
            return {
                "status": "blocked",
                "code": response.status_code,
                "items": []
            }

        soup = BeautifulSoup(response.text, "html.parser")

        items = []

        # Ищем ссылки на объявления
        links = soup.find_all("a", href=True)

        seen = set()

        for link in links:
            href = link.get("href", "")

            if "/items/" not in href:
                continue

            if href in seen:
                continue

            seen.add(href)

            title = link.get_text(" ", strip=True)

            if not title:
                continue

            # Пытаемся найти цену рядом с объявлением
            parent = link

            for _ in range(5):
                if parent.parent:
                    parent = parent.parent

            text = parent.get_text(" ", strip=True)

            price_match = re.search(
                r"(\d[\d\s]*)\s*₽",
                text
            )

            price = None

            if price_match:
                try:
                    price = int(
                        price_match.group(1)
                        .replace(" ", "")
                    )
                except ValueError:
                    pass

            if not href.startswith("http"):
                href = "https://www.avito.ru" + href

            items.append({
                "title": title[:150],
                "price": price,
                "url": href
            })

            if len(items) >= 10:
                break

        return {
            "status": "ok",
            "code": response.status_code,
            "items": items
        }

    except requests.RequestException as e:
        logging.exception("Avito request failed")
        return {
            "status": "error",
            "error": str(e),
            "items": []
        }


# -------------------------
# Telegram
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter запущен!\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/id — показать ID\n"
        "/watch — добавить мониторинг\n"
        "/search — выполнить поиск\n"
        "/list — список мониторингов\n"
        "/clear — очистить мониторинг"
    )


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Твой Telegram ID: {update.effective_user.id}"
    )


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат:\n"
            "/watch запрос минимальная_цена максимальная_цена\n\n"
            "Пример:\n"
            "/watch видеокарта 5000 15000"
        )
        return

    try:
        min_price = int(context.args[-2])
        max_price = int(context.args[-1])
    except ValueError:
        await update.message.reply_text(
            "❌ Последние два значения должны быть ценами."
        )
        return

    query = " ".join(context.args[:-2])

    if min_price > max_price:
        await update.message.reply_text(
            "❌ Минимальная цена больше максимальной."
        )
        return

    watchlist = load_watchlist()

    watchlist.append({
        "query": query,
        "min_price": min_price,
        "max_price": max_price
    })

    save_watchlist(watchlist)

    await update.message.reply_text(
        "🔎 Добавил в мониторинг:\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–{max_price:,} ₽"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат:\n"
            "/search запрос минимальная_цена максимальная_цена\n\n"
            "Пример:\n"
            "/search видеокарта 5000 15000"
        )
        return

    try:
        min_price = int(context.args[-2])
        max_price = int(context.args[-1])
    except ValueError:
        await update.message.reply_text(
            "❌ Последние два значения должны быть ценами."
        )
        return

    query = " ".join(context.args[:-2])

    await update.message.reply_text(
        f"🔎 Ищу на Avito:\n"
        f"{query}\n"
        f"{min_price:,}–{max_price:,} ₽\n\n"
        "⏳ Подожди..."
    )

    result = search_avito(
        query,
        min_price,
        max_price
    )

    if result["status"] == "blocked":
        await update.message.reply_text(
            "🛑 Avito не отдал страницу.\n\n"
            f"HTTP-код: {result['code']}\n\n"
            "Это тест обычного HTTP-запроса. "
            "По логам Render определим следующий способ."
        )
        return

    if result["status"] == "error":
        await update.message.reply_text(
            "❌ Ошибка соединения с Avito.\n\n"
            f"{result.get('error', 'Неизвестная ошибка')}"
        )
        return

    items = result["items"]

    if not items:
        await update.message.reply_text(
            "🔎 Страница Avito получена, "
            "но объявления не удалось извлечь.\n\n"
            "Это тоже полезный результат теста."
        )
        return

    text = f"🔎 Найдено объявлений: {len(items)}\n\n"

    for i, item in enumerate(items, 1):
        price = (
            f"{item['price']:,} ₽"
            if item["price"]
            else "цена не определена"
        )

        text += (
            f"{i}. {item['title']}\n"
            f"💰 {price}\n"
            f"🔗 {item['url']}\n\n"
        )

        if len(text) > 3500:
            break

    await update.message.reply_text(text)


async def list_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    watchlist = load_watchlist()

    if not watchlist:
        await update.message.reply_text(
            "📋 Активных мониторингов нет."
        )
        return

    text = "📋 Твои мониторинги:\n\n"

    for i, item in enumerate(watchlist, 1):
        text += (
            f"{i}. 🔎 {item['query']}\n"
            f"💰 {item['min_price']:,}–"
            f"{item['max_price']:,} ₽\n\n"
        )

    await update.message.reply_text(text)


async def clear_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    save_watchlist([])

    await update.message.reply_text(
        "🗑 Мониторинг очищен."
    )


# -------------------------
# Запуск
# -------------------------

def main():
    server_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )
    server_thread.start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("list", list_watch))
    app.add_handler(CommandHandler("clear", clear_watch))

    logging.info("Avito Hunter starting...")

    app.run_polling()


if __name__ == "__main__":
    main()