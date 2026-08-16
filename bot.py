import os
import re
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
# RENDER HEALTH SERVER
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
# AVITO
# =========================================================

def get_avito_page(query):
    """
    Получает страницу поиска Avito через curl_cffi.
    """

    url = "https://www.avito.ru/omsk"

    params = {
        "q": query
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

    logging.info(
        "Avito search: %s",
        query
    )

    response = requests.get(
        url,
        params=params,
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )

    logging.info(
        "Avito HTTP: %s",
        response.status_code
    )

    return response


# =========================================================
# PARSE AVITO ITEMS
# =========================================================

def parse_items(html):
    """
    Пытаемся найти объявления непосредственно
    в HTML Avito.

    Avito использует JSON внутри страницы,
    поэтому ищем ссылки / объявления и цены.
    """

    items = []

    # -----------------------------------------------------
    # Вариант 1 — ссылки объявлений
    # -----------------------------------------------------

    pattern = re.compile(
        r'href="([^"]*?/item/[^"]+)"',
        re.IGNORECASE
    )

    links = pattern.findall(html)

    # -----------------------------------------------------
    # Убираем дубли
    # -----------------------------------------------------

    unique_links = []

    for link in links:

        if link not in unique_links:
            unique_links.append(link)

    logging.info(
        "Найдено ссылок: %s",
        len(unique_links)
    )

    # -----------------------------------------------------
    # Создаём базовый список
    # -----------------------------------------------------

    for link in unique_links[:50]:

        if link.startswith("/"):
            link = "https://www.avito.ru" + link

        items.append({
            "title": "Объявление Avito",
            "price": None,
            "url": link,
        })

    return items


# =========================================================
# EXTRACT PRICES
# =========================================================

def extract_prices(html):
    """
    Ищем цены в HTML.
    """

    prices = []

    patterns = [
        r'"price"\s*:\s*"?(\d[\d\s]*)"?',
        r'"priceDetailed"\s*:\s*"(\d[\d\s]*)',
        r'(\d[\d\s]{2,})\s*₽',
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html,
            re.IGNORECASE
        )

        for match in matches:

            value = re.sub(
                r"\s+",
                "",
                match
            )

            try:

                price = int(value)

                if 100 <= price <= 10000000:
                    prices.append(price)

            except ValueError:
                pass

    return prices


# =========================================================
# SEARCH
# =========================================================

def search_avito(
    query,
    min_price,
    max_price
):

    response = get_avito_page(
        query
    )

    if response.status_code != 200:

        return {
            "status": "error",
            "code": response.status_code,
            "items": []
        }

    html = response.text

    logging.info(
        "HTML size: %s",
        len(html)
    )

    items = parse_items(
        html
    )

    prices = extract_prices(
        html
    )

    logging.info(
        "Найдено цен: %s",
        len(prices)
    )

    # -----------------------------------------------------
    # Применяем диапазон цены
    # -----------------------------------------------------

    filtered_prices = []

    for price in prices:

        if min_price <= price <= max_price:

            filtered_prices.append(
                price
            )

    # -----------------------------------------------------
    # Если нашли ссылки — прикрепляем цены
    # -----------------------------------------------------

    for index, item in enumerate(items):

        if index < len(filtered_prices):

            item["price"] = (
                filtered_prices[index]
            )

    # -----------------------------------------------------
    # Оставляем только объявления
    # -----------------------------------------------------

    result_items = []

    for item in items:

        price = item.get(
            "price"
        )

        if price is not None:

            if min_price <= price <= max_price:

                result_items.append(
                    item
                )

    return {
        "status": "ok",
        "items": result_items,
        "total": len(result_items),
        "html_size": len(html)
    }


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
        "/id — Telegram ID\n"
        "/search — поиск Avito\n"
        "/testavito — проверка Avito\n\n"
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

        response = get_avito_page(
            "видеокарта"
        )

        await update.message.reply_text(
            "✅ Avito ответил!\n\n"
            f"HTTP: {response.status_code}\n"
            f"Размер страницы: "
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
            "Формат:\n\n"
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
            "❌ Цена должна быть числом."
        )

        return

    query = " ".join(
        context.args[:-2]
    )

    await update.message.reply_text(
        "🔎 Ищу на Avito...\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–"
        f"{max_price:,} ₽\n\n"
        "⏳ Загружаю объявления..."
    )

    try:

        result = search_avito(
            query,
            min_price,
            max_price
        )

    except Exception as error:

        logging.exception(
            "Search error"
        )

        await update.message.reply_text(
            "❌ Ошибка при запросе Avito:\n\n"
            f"{error}"
        )

        return

    if result["status"] != "ok":

        await update.message.reply_text(
            "❌ Avito не отдал страницу.\n\n"
            f"HTTP: {result['code']}"
        )

        return

    items = result["items"]

    if not items:

        await update.message.reply_text(
            "😕 В заданном диапазоне "
            "ничего не найдено.\n\n"
            f"Размер страницы Avito: "
            f"{result['html_size']:,} символов"
        )

        return

    text = (
        "🔥 НАЙДЕНО НА AVITO\n\n"
    )

    for index, item in enumerate(
        items[:10],
        1
    ):

        title = item.get(
            "title",
            "Объявление"
        )

        price = item.get(
            "price"
        )

        url = item.get(
            "url",
            ""
        )

        text += (
            f"{index}. {title}\n"
            f"💰 {price:,} ₽\n"
            f"🔗 {url}\n\n"
        )

    text += (
        f"📊 Всего найдено: "
        f"{len(items)}"
    )

    await update.message.reply_text(
        text
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # Render требует открытый HTTP-порт
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
    )

    app.run_polling()


if __name__ == "__main__":
    main()