import os
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

import storage
import faceswap_engine
from config import TEMPLATES, TEMPLATES_DIR, TEMP_DIR, FREE_GENERATIONS

router = Router()
logger = logging.getLogger(__name__)

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message):
    storage.set_state(message.from_user.id, "idle")
    await message.answer(
        "👋 Привет! Я создам для тебя ИИ-фотосессию в любом образе!\n\n"
        "✨ Как это работает:\n"
        "1️⃣ Отправь своё чёткое фото (лицо хорошо видно)\n"
        "2️⃣ Выбери стиль из меню\n"
        "3️⃣ Получи готовое фото за 10–20 секунд! 🔥\n\n"
        f"🎁 Первые {FREE_GENERATIONS} генерации — бесплатно!\n\n"
        "📸 Нажми кнопку ниже чтобы начать:",
        reply_markup=_start_kb()
    )


def _start_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📸 Загрузить своё фото", callback_data="upload_photo")
    return b.as_markup()


# ─── Загрузка фото ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "upload_photo")
async def ask_for_photo(callback: CallbackQuery):
    storage.set_state(callback.from_user.id, "waiting_photo")
    await callback.message.answer(
        "📸 Отправь своё фото!\n\n"
        "💡 Советы:\n"
        "• Лицо чётко видно, смотришь в камеру\n"
        "• Хорошее освещение\n"
        "• Без очков и масок\n"
        "• Только ты на фото"
    )
    await callback.answer()


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    user_id = message.from_user.id

    if storage.get_user(user_id)["state"] != "waiting_photo":
        await message.answer("Сначала нажми «Загрузить своё фото» 👇", reply_markup=_start_kb())
        return

    # Скачиваем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    path = os.path.join(TEMP_DIR, f"{user_id}_face.jpg")

    await faceswap_engine.download_photo(url, path)
    storage.set_photo(user_id, path)
    storage.set_state(user_id, "idle")

    await message.answer(
        "✅ Фото принято! Выбери стиль фотосессии 👇",
        reply_markup=_styles_kb()
    )


# ─── Выбор стиля ─────────────────────────────────────────────────────────────

def _styles_kb():
    b = InlineKeyboardBuilder()
    for key, name in TEMPLATES.items():
        b.button(text=name, callback_data=f"style_{key}")
    b.adjust(2)
    return b.as_markup()


@router.callback_query(F.data.startswith("style_"))
async def handle_style(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    style_key = callback.data.replace("style_", "")
    style_name = TEMPLATES.get(style_key)

    if not style_name:
        await callback.answer("Неизвестный стиль", show_alert=True)
        return

    user_photo = storage.get_photo(user_id)
    if not user_photo:
        await callback.message.answer("Сначала загрузи своё фото 👇", reply_markup=_start_kb())
        await callback.answer()
        return

    # Проверка лимита
    gens_used = storage.get_generations_used(user_id)
    if gens_used >= FREE_GENERATIONS and not storage.is_paid(user_id):
        await callback.message.answer(
            f"🔒 Бесплатные генерации закончились ({FREE_GENERATIONS} шт.)\n\n"
            "💳 Напиши /pay чтобы продолжить."
        )
        await callback.answer()
        return

    # Проверка шаблона
    template_path = os.path.join(TEMPLATES_DIR, f"{style_key}.jpg")
    if not os.path.exists(template_path):
        await callback.answer(
            f"⚠️ Шаблон «{style_name}» ещё не загружен!",
            show_alert=True
        )
        return

    await callback.message.answer(
        f"🎨 Применяю стиль «{style_name}»...\n"
        "⏳ Подожди 10–20 секунд ✨"
    )
    await callback.answer()

    asyncio.create_task(_run_swap(user_id, user_photo, template_path, style_name, bot))


async def _run_swap(user_id: int, user_photo: str, template_path: str, style_name: str, bot: Bot):
    result_path = os.path.join(TEMP_DIR, f"{user_id}_result.jpg")
    try:
        await faceswap_engine.faceswap(user_photo, template_path, result_path)
        storage.increment_generations(user_id)

        gens_used = storage.get_generations_used(user_id)
        remaining = max(0, FREE_GENERATIONS - gens_used)

        caption = f"✨ Готово! Стиль «{style_name}»"
        if not storage.is_paid(user_id):
            if remaining > 0:
                caption += f"\n\n🎁 Осталось бесплатных: {remaining}"
            else:
                caption += "\n\n🔒 Бесплатные закончились. /pay для продолжения"

        photo_file = FSInputFile(result_path)
        await bot.send_photo(user_id, photo=photo_file, caption=caption)

        if remaining > 0 or storage.is_paid(user_id):
            await bot.send_message(user_id, "Хочешь другой стиль? 👇", reply_markup=_styles_kb())

    except ValueError as e:
        err = str(e)
        if "не найдено" in err.lower() or "not found" in err.lower():
            await bot.send_message(
                user_id,
                "😕 Не смог найти лицо на фото.\n"
                "Попробуй загрузить другое фото — лицо должно быть чётким и хорошо освещённым.",
                reply_markup=_start_kb()
            )
        else:
            logger.error(f"Swap error for {user_id}: {e}")
            await bot.send_message(user_id, "❌ Ошибка. Попробуй другой стиль.", reply_markup=_styles_kb())
    except Exception as e:
        logger.error(f"Swap error for {user_id}: {e}")
        await bot.send_message(user_id, "❌ Ошибка обработки. Попробуй ещё раз.", reply_markup=_styles_kb())


# ─── /pay ────────────────────────────────────────────────────────────────────

@router.message(Command("pay"))
async def cmd_pay(message: Message):
    await message.answer(
        "💳 Тарифы:\n\n"
        "⭐ Базовый — 20 генераций → 299₽\n"
        "🔥 Про — 60 генераций → 699₽\n"
        "👑 Безлимит — 150 генераций → 999₽\n\n"
        "📩 Для оплаты напиши мне: @твой_юзернейм"
    )


# ─── /myphoto — сменить фото ─────────────────────────────────────────────────

@router.message(Command("myphoto"))
async def cmd_myphoto(message: Message):
    storage.set_state(message.from_user.id, "waiting_photo")
    await message.answer("📸 Отправь новое фото! Лицо должно быть чётким.")


# ─── /reset ──────────────────────────────────────────────────────────────────

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    storage.reset_user(message.from_user.id)
    await message.answer("♻️ Сброшено! Нажми /start чтобы начать заново.")
