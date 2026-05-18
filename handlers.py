import os
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

import storage
import replicate_api
from config import MIN_PHOTOS, MAX_PHOTOS, STYLES

router = Router()
logger = logging.getLogger(__name__)

# Папка для временных фото
PHOTOS_DIR = "temp_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = storage.get_user(message.from_user.id)
    storage.set_state(message.from_user.id, "idle")

    await message.answer(
        "👋 Привет! Я создам для тебя ИИ-фотосессию в любом образе!\n\n"
        "✨ Как это работает:\n"
        "1️⃣ Ты отправляешь мне 10–20 своих фото\n"
        "2️⃣ Я обучаю персональную ИИ-модель (~20 мин)\n"
        "3️⃣ Выбираешь стиль — и получаешь фотосессию!\n\n"
        "📸 Нажми кнопку ниже, чтобы начать!",
        reply_markup=_start_keyboard()
    )


def _start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Начать загрузку фото", callback_data="start_upload")
    return builder.as_markup()


# ─── Начало загрузки фото ─────────────────────────────────────────────────────

@router.callback_query(F.data == "start_upload")
async def start_upload(callback: CallbackQuery):
    user_id = callback.from_user.id
    storage.set_state(user_id, "collecting_photos")
    storage.get_user(user_id)["photos"] = []  # сброс

    await callback.message.answer(
        f"🖼 Отлично! Отправь мне от {MIN_PHOTOS} до {MAX_PHOTOS} своих фото.\n\n"
        "📌 Советы для лучшего результата:\n"
        "• Разные ракурсы (фас, профиль, полуоборот)\n"
        "• Разное освещение\n"
        "• Без других людей на фото\n"
        "• Чёткие, не размытые снимки\n\n"
        "Начинай отправлять! 👇"
    )
    await callback.answer()


# ─── Приём фото ──────────────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if user["state"] != "collecting_photos":
        await message.answer("Нажми /start чтобы начать заново.")
        return

    photos = storage.get_photos(user_id)

    if len(photos) >= MAX_PHOTOS:
        await message.answer(f"У тебя уже {MAX_PHOTOS} фото — этого достаточно! Нажми кнопку ниже.")
        return

    # Скачиваем фото (берём самое большое)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    save_path = os.path.join(PHOTOS_DIR, f"{user_id}_{len(photos)+1}.jpg")
    await replicate_api.download_photo(file_url, save_path)
    storage.add_photo(user_id, save_path)

    count = len(storage.get_photos(user_id))

    if count < MIN_PHOTOS:
        remaining = MIN_PHOTOS - count
        await message.answer(f"✅ Фото {count} принято! Ещё {remaining} для начала обучения.")
    elif count == MIN_PHOTOS:
        await message.answer(
            f"✅ {count} фото получено — минимум достигнут!\n"
            f"Можешь отправить ещё до {MAX_PHOTOS} фото для лучшего результата, "
            f"или сразу начать обучение 👇",
            reply_markup=_train_keyboard()
        )
    elif count < MAX_PHOTOS:
        await message.answer(
            f"✅ Фото {count} принято! ({MAX_PHOTOS - count} ещё можно добавить)",
            reply_markup=_train_keyboard()
        )


def _train_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Начать обучение модели!", callback_data="start_training")
    return builder.as_markup()


# ─── Запуск обучения ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "start_training")
async def start_training(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    photos = storage.get_photos(user_id)

    if len(photos) < MIN_PHOTOS:
        await callback.answer(f"Нужно минимум {MIN_PHOTOS} фото!", show_alert=True)
        return

    await callback.message.answer(
        "⏳ Начинаю обучение твоей персональной ИИ-модели...\n\n"
        "🕐 Это займёт около 15–25 минут.\n"
        "Я пришлю уведомление, как только всё будет готово!\n\n"
        "Можешь пока закрыть чат — бот сам напишет тебе 😊"
    )
    await callback.answer()

    storage.set_state(user_id, "training")

    # Упаковываем фото в ZIP
    zip_path = os.path.join(PHOTOS_DIR, f"{user_id}_photos.zip")
    replicate_api.create_zip_from_photos(photos, zip_path)

    # Запускаем обучение в фоне
    asyncio.create_task(_run_training(user_id, zip_path, bot))


async def _run_training(user_id: int, zip_path: str, bot: Bot):
    """Фоновая задача: обучение и уведомление"""
    try:
        training_id = await replicate_api.train_lora_model(zip_path, user_id)
        storage.set_training_id(user_id, training_id)

        # Ждём завершения (проверяем каждые 30 сек)
        while True:
            await asyncio.sleep(30)
            status = await replicate_api.check_training_status(training_id)

            if status["status"] == "succeeded":
                model_url = status.get("model_url")
                storage.set_model_url(user_id, model_url)

                await bot.send_message(
                    user_id,
                    "🎉 Твоя персональная модель готова!\n\n"
                    "Теперь выбери стиль фотосессии 👇",
                    reply_markup=_styles_keyboard()
                )
                break

            elif status["status"] == "failed":
                storage.set_state(user_id, "idle")
                await bot.send_message(
                    user_id,
                    "❌ Что-то пошло не так при обучении.\n"
                    "Попробуй снова: /start"
                )
                break

    except Exception as e:
        logger.error(f"Training error for user {user_id}: {e}")
        await bot.send_message(user_id, "❌ Ошибка. Попробуй снова: /start")


# ─── Выбор стиля ─────────────────────────────────────────────────────────────

def _styles_keyboard():
    builder = InlineKeyboardBuilder()
    for key, style in STYLES.items():
        builder.button(text=style["name"], callback_data=f"style_{key}")
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("styles"))
async def cmd_styles(message: Message):
    user_id = message.from_user.id
    if not storage.get_model_url(user_id):
        await message.answer("Сначала нужно обучить модель. Нажми /start")
        return
    await message.answer("Выбери стиль фотосессии 👇", reply_markup=_styles_keyboard())


@router.callback_query(F.data.startswith("style_"))
async def handle_style(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    style_key = callback.data.replace("style_", "")
    style = STYLES.get(style_key)

    if not style:
        await callback.answer("Неизвестный стиль", show_alert=True)
        return

    model_url = storage.get_model_url(user_id)
    if not model_url:
        await callback.answer("Модель ещё не готова!", show_alert=True)
        return

    await callback.message.answer(
        f"🎨 Генерирую фото в стиле «{style['name']}»...\n"
        "⏳ Подожди ~30 секунд"
    )
    await callback.answer()

    # Генерация в фоне
    asyncio.create_task(_run_generation(user_id, model_url, style, bot))


async def _run_generation(user_id: int, model_url: str, style: dict, bot: Bot):
    """Фоновая задача: генерация фото"""
    try:
        photo_urls = await replicate_api.generate_photo(model_url, style["prompt"])

        await bot.send_message(user_id, f"✨ Готово! Вот твои фото в стиле «{style['name']}»:")

        for url in photo_urls:
            await bot.send_photo(user_id, url)

        await bot.send_message(
            user_id,
            "Хочешь ещё стиль? 👇",
            reply_markup=_styles_keyboard()
        )

    except Exception as e:
        logger.error(f"Generation error for user {user_id}: {e}")
        await bot.send_message(user_id, "❌ Ошибка генерации. Попробуй другой стиль.")


# ─── /reset ──────────────────────────────────────────────────────────────────

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    storage.reset_user(message.from_user.id)
    await message.answer("♻️ Сброшено. Нажми /start чтобы начать заново.")
