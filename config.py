import os

# Токен бота (один, объединённый)
BOT_TOKEN = "8781867816:AAHTUiftksAirLCllqFoALgeCUAJ0nNEkP0"

# ID группы и топика (для работы в топике)
GROUP_ID = -1003300908374
TOPIC_ID = 3830

# Администраторы
MASTER_ADMIN_ID = 639212691
ADMIN_IDS = [MASTER_ADMIN_ID]  # Список будет пополняться из Excel

# Пути к файлам
DATA_DIR = "data"
EXCEL_FILE = os.path.join(DATA_DIR, "База для приложения.xlsx")
PRICES_DB = os.path.join(DATA_DIR, "prices.db")

# Настройки пагинации
ITEMS_PER_PAGE = 10

# Настройки кэширования (для Excel)
CACHE_TTL = 300

# Алиас для совместимости
TOKEN = BOT_TOKEN
