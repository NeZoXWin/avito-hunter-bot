import os
import asyncio
import logging
import threading
from urllib.parse import quote

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from playwright.async_api import async_playwright


BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# RENDER WEB SERVER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Avito Hunter is running!"


@web_app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", "10000"))

    web_app.run(
        host="0.0.0.0",
        port=port
    )


# =========================
# AVITO URL
# =========================

def build_avito_url(
    query: str,
    min_price: int,
    max_price: int
) -> str:

    return (
        "https://www.avito.ru/omsk"
        f"?q={quote(query)}"
        f"&pmin={min_price}"
        f"&pmax={max_price}"
    )


# =========================
# PLAYWRIGHT
# =========================

async def parse_avito(
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
        "Opening Avito: %s",
        url
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            },

            locale="ru-RU",

            timezone_id="Europe/Moscow",

            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 "
                "Safari/537.36"
            ),

            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9"
            }
        )

        page = await context.new_page()

        try:

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            status = (
                response.status
                if response
                else 0
            )

            logging.info(
                "Avito HTTP status: %s",
                status
            )

            await page.wait_for_timeout(5000)

            title = await page.title()

            logging.info(
                "Avito title: %s",
                title
            )

            body_text = await page.locator(
                "body"
            ).inner_text()

            lower_text = body_text.lower()

            blocked_words = [
                "доступ ограничен",
                "слишком много запросов",
                "captcha",
                "капча",
                "проверка браузера",
                "access denied",
            ]

            block_reason = None

            for word in blocked_words:

                if word in lower_text:

                    block_reason = word
                    break

            if status in (403, 429):

                block_reason = (
                    block_reason
                    or f"HTTP {status}"
                )

            if block_reason:

                logging.warning(
                    "Avito block detected: %s",
                    block_reason
                )

                return {
                    "status": status,
                    "blocked": True,
                    "block_reason": block_reason,
                    "items": []
                }

            items_locator = page.locator(
                '[data-marker="item"]'
            )

            count = await items_locator.count()

            logging.info(
                "Avito cards found: %s",
                count
            )

            results = []

            for i in range(
                min(count, 20)
            ):

                item = items_locator.nth(i)

                try:

                    title_locator = item.locator(
                        '[itemprop="name"], '
                        '[data-marker="item-title"], '
                        'h3'
                    ).first

                    title_text = ""

                    if await title_locator.count():

                        title_text = (
                            await title_locator.inner_text()
                        ).strip()

                    price_locator = item.locator(
                        '[itemprop="price"], '
                        '[data-marker="item-price"]'
                    ).first

                    price_text = ""

                    if await price_locator.count():

                        price_text = (
                            await price_locator.inner_text()
                        ).strip()

                        if not price_text:

                            price_text = (
                                await price_locator.get_attribute(
                                    "content"
                                )
                                or ""
                            )

                    link_locator = item.locator(
                        "a[href]"
                    ).first

                    link = ""

                    if await link_locator.count():

                        href = (
                            await link_locator.get_attribute(
                                "href"
                            )
                        )

                        if href:

                            if href.startswith("http"):
                                link = href

                            else:
                                link = (
                                    "https://www.avito.ru"
                                    + href
                                )

                    if title_text:

                        results.append(
                            {
                                "title": title_text,
                                "price": price_text,
                                "url": link
                            }
                        )

                except Exception as e:

                    logging.warning(
                        "Card parse error: %s",
                        e
                    )

            return {
                "status": status,
                "blocked": False,
                "block_reason": "",
                "items": results
            }

        finally:

            await browser.close()


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
        "/avito_test\n"
        "/test\n"
        "/id\n\n"
        "Пример:\n"
        "/search видеокарта 5000 15000"
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
        "✅ Telegram работает\n"
        "✅ Render работает\n"
        "✅ Playwright подключён"
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
# /AVITO_TEST
# =========================

async def avito_test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🌐 Запускаю Chromium...\n"
        "⏳ Проверяю Avito..."
    )

    try:

        result = await parse_avito(
            "видеокарта",
            5000,
            15000
        )

        if result["blocked"]:

            await update.message.reply_text(
                "❌ Avito заблокировал запрос.\n\n"
                f"HTTP: {result['status']}\n"
                f"Причина: {result['block_reason']}"
            )

            return

        await update.message.reply_text(
            "✅ Playwright получил Avito!\n\n"
            f"HTTP: {result['status']}\n"
            f"Карточек: {len(result['items'])}"
        )

    except Exception as e:

        logging.exception(
            "Playwright test error"
        )

        await update.message.reply_text(
            "❌ Ошибка Playwright:\n\n"
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
            "❌ Формат:\n\n"
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
        "⏳ Загружаю страницу..."
    )

    try:

        result = await parse_avito(
            query,
            min_price,
            max_price
        )

        if result["blocked"]:

            await update.message.reply_text(
                "❌ Avito заблокировал запрос.\n\n"
                f"HTTP: {result['status']}\n"
                f"Причина: {result['block_reason']}"
            )

            return

        items = result["items"]

        if not items:

            await update.message.reply_text(
                "😕 Объявления не найдены.\n\n"
                f"HTTP: {result['status']}\n"
                "Карточек: 0"
            )

            return

        parts = [
            f"🔎 Найдено объявлений: {len(items)}\n"
        ]

        for index, item in enumerate(
            items[:10],
            start=1
        ):

            text = (
                f"{index}. {item['title']}\n"
                f"💰 {item['price']}\n"
            )

            if item["url"]:

                text += (
                    f"🔗 {item['url']}\n"
                )

            parts.append(text)

        message = "\n".join(parts)

        if len(message) > 4000:

            message = (
                message[:3900]
                + "\n..."
            )

        await update.message.reply_text(
            message,
            disable_web_page_preview=True
        )

    except Exception as e:

        logging.exception(
            "Search error"
        )

        await update.message.reply_text(
            "❌ Ошибка поиска:\n\n"
            f"{type(e).__name__}: {e}"
        )


# =========================
# MAIN
# =========================

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
        CommandHandler("test", test)
    )

    telegram_app.add_handler(
        CommandHandler("id", get_id)
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

    telegram_app.run_polling()


if __name__ == "__main__":
    main()