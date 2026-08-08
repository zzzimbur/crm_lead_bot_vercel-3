"""
Минимальный клиент для amoCRM API v4.
Делает то, что нужно для демо-кейса:
  1. Ищет/создаёт контакт по имени + телефону
  2. Создаёт сделку (лид) и привязывает к ней контакт
  3. Добавляет примечание с текстом заявки из Telegram

Документация: https://www.amocrm.ru/developers/content/crm_platform/leads-api
"""

import logging
from typing import Optional

import httpx

from app.config import AMOCRM_BASE_URL, AMOCRM_ACCESS_TOKEN

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


class AmoCRMError(Exception):
    pass


async def _request(method: str, path: str, **kwargs) -> dict:
    url = f"{AMOCRM_BASE_URL}{path}"
    # Таймаут увеличен: на некоторых машинах первый handshake до amoCRM
    # занимает 15-20+ секунд (медленный DNS resolve через asyncio на macOS),
    # хотя сам сервер отвечает быстро.
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.request(method, url, headers=HEADERS, **kwargs)

    if resp.status_code == 401:
        raise AmoCRMError(
            "amoCRM вернул 401 Unauthorized — долгосрочный токен истёк или неверный. "
            "Сгенерируй новый в настройках интеграции."
        )
    if resp.status_code >= 400:
        raise AmoCRMError(f"amoCRM API ошибка {resp.status_code}: {resp.text}")

    if resp.status_code == 204 or not resp.content:
        return {}
    return resp.json()


async def create_contact(name: str, phone: Optional[str] = None) -> int:
    """Создаёт контакт в amoCRM, возвращает его ID."""
    payload = [
        {
            "name": name,
            "custom_fields_values": (
                [
                    {
                        "field_code": "PHONE",
                        "values": [{"value": phone, "enum_code": "WORK"}],
                    }
                ]
                if phone
                else None
            ),
        }
    ]
    data = await _request("POST", "/api/v4/contacts", json=payload)
    contact_id = data["_embedded"]["contacts"][0]["id"]
    logger.info("Создан контакт amoCRM id=%s", contact_id)
    return contact_id


async def create_lead(
    name: str,
    contact_id: int,
    note_text: str,
    price: int = 0,
) -> int:
    """Создаёт сделку, привязывает контакт, возвращает ID сделки."""
    payload = [
        {
            "name": name,
            "price": price,
            "_embedded": {"contacts": [{"id": contact_id}]},
        }
    ]
    data = await _request("POST", "/api/v4/leads", json=payload)
    lead_id = data["_embedded"]["leads"][0]["id"]
    logger.info("Создана сделка amoCRM id=%s", lead_id)

    await add_note_to_lead(lead_id, note_text)
    return lead_id


async def add_note_to_lead(lead_id: int, text: str) -> None:
    payload = [
        {
            "note_type": "common",
            "params": {"text": text},
        }
    ]
    await _request("POST", f"/api/v4/leads/{lead_id}/notes", json=payload)


async def push_telegram_lead(
    full_name: str,
    username: Optional[str],
    phone: Optional[str],
    raw_message: str,
) -> int:
    """
    Высокоуровневая функция: из данных заявки из Telegram
    создаёт контакт + сделку + примечание в amoCRM.
    Возвращает ID созданной сделки.
    """
    contact_id = await create_contact(name=full_name, phone=phone)

    note = (
        f"Заявка из Telegram-бота\n"
        f"Username: @{username}" if username else "Username: не указан"
    )
    note += f"\nТекст заявки: {raw_message}"

    lead_name = f"Заявка из Telegram — {full_name}"
    lead_id = await create_lead(name=lead_name, contact_id=contact_id, note_text=note)
    return lead_id
