import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

AMOCRM_SUBDOMAIN = os.environ.get("AMOCRM_SUBDOMAIN", "prostozapaska")
AMOCRM_BASE_URL = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru"
AMOCRM_ACCESS_TOKEN = os.environ.get("AMOCRM_ACCESS_TOKEN", "")

# Vercel Storage -> Upstash Redis подставляет эту переменную сам
# (redis:// или rediss:// строка подключения). Название переменной может
# отличаться в зависимости от того, как назовёшь базу в дашборде —
# проверь в Storage -> .env.local / Quickstart, как называется точно,
# и при необходимости поправь имя ниже.
REDIS_URL = (
    os.environ.get("REDIS_URL")
    or os.environ.get("KV_URL")
    or os.environ.get("STORAGE_URL")
    or ""
)

# Секретный путь для вебхука — чтобы никто посторонний не мог слать
# фейковые "обновления" на твой endpoint. Придумай любую случайную строку
# и укажи её и здесь (через переменную окружения), и при регистрации вебхука.
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
