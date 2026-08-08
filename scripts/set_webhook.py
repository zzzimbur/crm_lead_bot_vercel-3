"""
Запусти этот скрипт ОДИН РАЗ после того, как задеплоил проект на Vercel —
он говорит Telegram: "присылай новые сообщения на этот адрес".

Использование:
    python scripts/set_webhook.py

Перед запуском задай переменные окружения (или впиши прямо в терминале):
    export BOT_TOKEN="токен_от_botfather"
    export VERCEL_URL="https://твой-проект.vercel.app"
    export WEBHOOK_SECRET="любая-случайная-строка"   (необязательно, но желательно)
"""

import os
import sys

import httpx

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
VERCEL_URL = os.environ.get("VERCEL_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

if not BOT_TOKEN or not VERCEL_URL:
    print("Нужно задать BOT_TOKEN и VERCEL_URL перед запуском. Пример:")
    print('  export BOT_TOKEN="123456:AA..."')
    print('  export VERCEL_URL="https://crm-lead-bot.vercel.app"')
    sys.exit(1)

webhook_url = f"{VERCEL_URL}/api/webhook"

payload = {"url": webhook_url}
if WEBHOOK_SECRET:
    payload["secret_token"] = WEBHOOK_SECRET

resp = httpx.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json=payload,
    timeout=15,
)

print(f"Статус: {resp.status_code}")
print(resp.json())

# Дополнительно проверим, что Telegram сам думает про вебхук
info = httpx.get(
    f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=15
)
print("\nТекущая информация о вебхуке:")
print(info.json())
