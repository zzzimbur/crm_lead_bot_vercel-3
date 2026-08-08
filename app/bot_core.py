"""
Логика бота, общая для всех вызовов serverless-функции.
Отличие от polling-версии: FSM-состояния хранятся в Redis (Upstash),
потому что между вызовами функции на Vercel память не сохраняется —
каждый запрос может обработать "новый" процесс.
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from redis.asyncio import Redis

from app.config import BOT_TOKEN, REDIS_URL
from app.amocrm import push_telegram_lead, AmoCRMError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadForm(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_message = State()


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер 📱", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Это демо-бот квалификации заявок с прямой интеграцией в amoCRM.\n\n"
        "Заполните короткую форму — заявка автоматически попадёт в CRM как новая сделка "
        "с привязанным контактом, без ручного ввода менеджером.\n\n"
        "Как вас зовут?",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(LeadForm.waiting_name)


async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await message.answer(
        "Отлично. Теперь отправьте номер телефона (можно кнопкой ниже, либо текстом).",
        reply_markup=phone_keyboard(),
    )
    await state.set_state(LeadForm.waiting_phone)


async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await message.answer(
        "Принято. Опишите в двух словах, что вас интересует "
        "(например: «нужен бот для записи клиентов»).",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(LeadForm.waiting_message)


async def process_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    name = data.get("name", "Без имени")
    phone = data.get("phone")
    await message.answer("Секунду, создаю сделку в CRM...")

    try:
        lead_id = await push_telegram_lead(
            full_name=name,
            username=message.from_user.username,
            phone=phone,
            raw_message=message.text,
        )
        await message.answer(
            f"Готово ✅\n"
            f"Заявка создана в amoCRM как сделка #{lead_id}.\n"
            f"Менеджер увидит её в воронке и свяжется с вами."
        )
    except AmoCRMError as e:
        logger.error("Ошибка amoCRM: %s", e)
        await message.answer(
            "Заявку принял, но при записи в CRM произошла ошибка. "
            "Мы уже разбираемся, менеджер свяжется вручную."
        )
    finally:
        await state.clear()


def build_dispatcher() -> Dispatcher:
    if not REDIS_URL:
        raise RuntimeError(
            "REDIS_URL не задан. Подключи Upstash Redis во вкладке Storage "
            "на Vercel и убедись, что переменная окружения проброшена в проект."
        )
    redis = Redis.from_url(REDIS_URL)
    storage = RedisStorage(redis=redis)

    dp = Dispatcher(storage=storage)
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(process_name, LeadForm.waiting_name)
    dp.message.register(process_phone, LeadForm.waiting_phone)
    dp.message.register(process_message, LeadForm.waiting_message)
    return dp


def build_bot() -> Bot:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения Vercel.")
    return Bot(token=BOT_TOKEN)
