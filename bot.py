import os
import json
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 437716810

WATCH_FILE = "watchlist.json"


def load_watchlist():
    if not os.path.exists(WATCH_FILE):
        return []

    try:
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_watchlist(watchlist):
    with open(WATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    await update.message.reply_text(
        "🤖 Avito Hunter запущен!\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/id — показать ID\n"
        "/watch — добавить товар в мониторинг\n"
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
            "❌ Последние два значения должны быть ценами.\n\n"
            "Пример:\n"
            "/watch видеокарта 5000 15000"
        )
        return

    query = " ".join(context.args[:-2])

    if min_price < 0 or max_price < 0:
        await update.message.reply_text("❌ Цена не может быть отрицательной.")
        return

    if min_price > max_price:
        await update.message.reply_text(
            "❌ Минимальная цена не может быть больше максимальной."
        )
        return

    watchlist = load_watchlist()

    item = {
        "query": query,
        "min_price": min_price,
        "max_price": max_price
    }

    watchlist.append(item)
    save_watchlist(watchlist)

    await update.message.reply_text(
        "🔎 Добавил в мониторинг:\n\n"
        f"Товар: {query}\n"
        f"Цена: {min_price:,}–{max_price:,} ₽\n\n"
        "Статус: 🟡 ожидает подключения поиска Avito."
    )


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
            f"   💰 {item['min_price']:,}–{item['max_price']:,} ₽\n"
            f"   🟡 Ожидает поиска\n\n"
        )

    await update.message.reply_text(text)


async def clear_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    save_watchlist([])

    await update.message.reply_text(
        "🗑 Мониторинг очищен."
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("list", list_watch))
    app.add_handler(CommandHandler("clear", clear_watch))

    app.run_polling()


if __name__ == "__main__":
    main()