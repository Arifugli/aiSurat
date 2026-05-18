import os
from dotenv import load_dotenv

load_dotenv()

# Токены (хранятся в .env файле)
BOT_TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Настройки сбора фото
MIN_PHOTOS = 10
MAX_PHOTOS = 20

# Стили для генерации
STYLES = {
    "studio": {
        "name": "📸 Студийный портрет",
        "prompt": "professional studio portrait photo, soft lighting, clean background, high quality, photorealistic"
    },
    "outdoor": {
        "name": "🌿 На природе",
        "prompt": "outdoor lifestyle photo, natural light, park or forest background, candid style, photorealistic"
    },
    "fashion": {
        "name": "👗 Фэшн",
        "prompt": "high fashion editorial photo, dramatic lighting, elegant outfit, magazine style, photorealistic"
    },
    "beach": {
        "name": "🏖️ Пляж",
        "prompt": "beach photo, sunny day, ocean background, summer vibes, natural lighting, photorealistic"
    },
    "night": {
        "name": "🌃 Ночной город",
        "prompt": "night city portrait, neon lights, bokeh background, cinematic style, photorealistic"
    },
    "bw": {
        "name": "🖤 Чёрно-белое",
        "prompt": "black and white portrait photo, professional photography, high contrast, artistic, photorealistic"
    },
}

# Replicate модель для обучения LoRA
FLUX_TRAINER_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_TRAINER_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"

# Replicate модель для генерации
FLUX_MODEL = "black-forest-labs/flux-dev-lora"
