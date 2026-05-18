import os
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import aiohttp
import aiofiles
import asyncio
import logging

logger = logging.getLogger(__name__)

# Глобальные объекты (инициализируются один раз при старте)
_face_app = None
_swapper = None
_MODEL_DIR = "models"


def init_models():
    """Инициализация моделей InsightFace (один раз при старте бота)"""
    global _face_app, _swapper

    os.makedirs(_MODEL_DIR, exist_ok=True)

    logger.info("Загружаю модели InsightFace...")

    _face_app = FaceAnalysis(name="buffalo_l", root=_MODEL_DIR)
    _face_app.prepare(ctx_id=0, det_size=(640, 640))  # ctx_id=0 для CPU

    # Скачиваем модель inswapper если нет
    swapper_path = os.path.join(_MODEL_DIR, "inswapper_128.onnx")
    if not os.path.exists(swapper_path):
        logger.info("Скачиваю модель inswapper_128.onnx...")
        import urllib.request
        url = "https://huggingface.co/countfloyd/deepfake/resolve/main/inswapper_128.onnx"
        urllib.request.urlretrieve(url, swapper_path)
        logger.info("Модель скачана!")

    _swapper = insightface.model_zoo.get_model(swapper_path, download=False)
    logger.info("Модели готовы!")


async def download_photo(url: str, path: str):
    """Скачивает фото по URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async with aiofiles.open(path, "wb") as f:
                await f.write(await resp.read())


def _do_faceswap(source_path: str, target_path: str, result_path: str) -> bool:
    """
    Синхронная функция face swap.
    source_path - фото пользователя (откуда берём лицо)
    target_path - шаблон (куда вставляем лицо)
    result_path - куда сохранить результат
    """
    global _face_app, _swapper

    if _face_app is None or _swapper is None:
        init_models()

    # Читаем изображения
    source_img = cv2.imread(source_path)
    target_img = cv2.imread(target_path)

    if source_img is None:
        raise ValueError(f"Не могу открыть фото пользователя: {source_path}")
    if target_img is None:
        raise ValueError(f"Не могу открыть шаблон: {target_path}")

    # Находим лица
    source_faces = _face_app.get(source_img)
    target_faces = _face_app.get(target_img)

    if len(source_faces) == 0:
        raise ValueError("Лицо не найдено на фото пользователя")
    if len(target_faces) == 0:
        raise ValueError("Лицо не найдено на шаблоне")

    # Берём первое лицо из каждого фото
    source_face = source_faces[0]
    result = target_img.copy()

    # Вставляем лицо во все лица на шаблоне
    for target_face in target_faces:
        result = _swapper.get(result, target_face, source_face, paste_back=True)

    # Сохраняем результат
    cv2.imwrite(result_path, result)
    return True


async def faceswap(source_path: str, target_path: str, result_path: str) -> str:
    """
    Асинхронная обёртка для face swap.
    Возвращает путь к результату.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _do_faceswap, source_path, target_path, result_path)
    return result_path
