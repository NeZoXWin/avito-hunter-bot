import os
import json
import logging
import threading
import asyncio

from flask import Flask
from playwright.async_api import async_playwright
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

async def search_avito(query, min_price, max_price):
    url = (
        "https://www.avito.ru/omsk"
        f"?q={query.replace(' ', '%20')}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = await browser.new_page(
            viewport={"width": 1366, "height": 768},
            locale="ru-RU"
        )

        try:
            logging.info("Opening Avito: %s", url)

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            await page.wait_for_timeout(3000)

            title = await page.title()

            logging.info("Avito page title: %s", title)

            # Получаем ссылки на объявления
            links = await page.locator(
                'a[href*="/items/"]'
            ).all()

            results = []
            seen = set()

            for link in links:

                href = await link.get_attribute("href")

                if not href:
                    continue

                if href in seen:
                    continue

                seen.add(href)

                text = (await link.inner_text()).strip()

                if not text:
                    continue

                if href.startswith("/"):
                    href = "https://www.avito.ru" + href

                results.append({
                    "title": text[:200],
                    "url": href
                })

                if len(results) >= 10:
                    break

            return {
                "status": "ok",
                "title": title,
                "items": results
            }

        except Exception as e:

            logging.exception("Avito search error")

            return {
                "status": "error",
                "error": str(e),
                "items": []
            }

        finally:
            await browser.close()


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
        "/search — поиск Avito\n"
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
        "⏳ Запускаю браузер..."
    )

    result = await search_avito(
        query,
        min_price,
        max_price
    )

    if result["status"] == "error":

        await update.message.reply_text(
            "❌ Ошибка при открытии Avito:\n\n"
            f"{result['error'][:1500]}"
        )

        return

    items = result["items"]

    if not items:

        await update.message.reply_text(
            "🔎 Avito открылся, "
            "но объявления не удалось получить.\n\n"
            f"Заголовок страницы:\n{result['title']}"
        )

        return

    text = (
        f"🔎 Найдено объявлений: {len(items)}\n\n"
    )

    for i, item in enumerate(items, 1):

        text += (
            f"{i}. {item['title']}\n"
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