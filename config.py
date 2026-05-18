import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Стили — имена файлов в папке templates/
TEMPLATES = {
    "studio_black": "🖤 Студия — тёмный фон",
    "studio_white": "🤍 Студия — светлый фон",
    "fashion_red":  "👗 Фэшн образ",
    "snow":         "❄️ Зимняя съёмка",
    "beach":        "🏖️ Пляж",
    "night_neon":   "🌃 Ночной неон",
    "flowers":      "🌸 Цветочный образ",
    "bw_portrait":  "🖤 Ч/Б портрет",
}

# Бесплатных генераций на пользователя
FREE_GENERATIONS = 2

TEMPLATES_DIR = "templates"
TEMP_DIR = "temp_photos"
