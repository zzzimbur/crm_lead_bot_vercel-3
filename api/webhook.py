"""
Точка входа для Vercel. Telegram будет стучаться сюда POST-запросом
при каждом новом сообщении/событии (это и есть webhook).

Файл лежит в /api/webhook.py — Vercel автоматически публикует его
как endpoint https://твой-домен.vercel.app/api/webhook
"""

import asyncio
import json
import sys
import os
from http.server import BaseHTTPRequestHandler

# Позволяет импортировать пакет app/ из соседней папки
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import Update

from app.bot_core import build_bot, build_dispatcher
from app.config import WEBHOOK_SECRET


async def _process_update(update_data: dict) -> None:
    # См. пояснение в yclients-версии: бот/диспетчер создаются заново
    # на каждый вызов, чтобы избежать "Event loop is closed" — Bot был бы
    # привязан к event loop предыдущего asyncio.run(), который уже закрыт.
    bot = build_bot()
    dp = build_dispatcher()
    try:
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()
        storage = dp.storage
        if hasattr(storage, "redis"):
            await storage.redis.aclose()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Проверка секрета — Telegram присылает его в заголовке, если
        # секрет был указан при регистрации вебхука (см. scripts/set_webhook.py)
        if WEBHOOK_SECRET:
            received_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if received_secret != WEBHOOK_SECRET:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            update_data = json.loads(body)
            asyncio.run(_process_update(update_data))
        except Exception as e:
            # Логируем, но всё равно отвечаем 200 — иначе Telegram будет
            # повторно слать то же самое обновление до бесконечности.
            print(f"Ошибка обработки апдейта: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_GET(self):
        # Просто чтобы можно было открыть URL в браузере и убедиться,
        # что функция вообще жива (не для Telegram, для тебя).
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Webhook жив. Telegram шлёт сюда POST-запросы.".encode("utf-8"))
