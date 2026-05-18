import replicate
import os
import zipfile
import aiofiles
import aiohttp
from config import FLUX_TRAINER_MODEL, FLUX_TRAINER_VERSION, FLUX_MODEL, REPLICATE_API_TOKEN

# Устанавливаем токен
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


async def download_photo(url: str, path: str):
    """Скачивает фото по URL и сохраняет на диск"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async with aiofiles.open(path, "wb") as f:
                await f.write(await resp.read())


def create_zip_from_photos(photo_paths: list, zip_path: str):
    """Упаковывает фото в ZIP для отправки в Replicate"""
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i, photo_path in enumerate(photo_paths):
            zf.write(photo_path, f"photo_{i+1}.jpg")
    return zip_path


async def train_lora_model(zip_path: str, user_id: int) -> str:
    """
    Запускает обучение LoRA на Replicate.
    Возвращает ID тренировки (training_id).
    Обучение идёт ~15-25 минут в фоне.
    """
    client = replicate.Client(api_token=REPLICATE_API_TOKEN)

    with open(zip_path, "rb") as f:
        training = client.trainings.create(
            model=FLUX_TRAINER_MODEL,
            version=FLUX_TRAINER_VERSION,
            input={
                "input_images": f,
                "steps": 1000,
                "lora_rank": 16,
                "optimizer": "adamw8bit",
                "batch_size": 1,
                "resolution": "512,768,1024",
                "autocaption": True,
                "trigger_word": "TOK",  # ключевое слово для генерации
                "learning_rate": 0.0004,
            },
            destination=f"arifugli/user-{user_id}-lora",
        )

    return training.id


async def check_training_status(training_id: str) -> dict:
    """
    Проверяет статус обучения.
    Возвращает: {"status": "starting|processing|succeeded|failed", "model_url": ...}
    """
    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    training = client.trainings.get(training_id)

    result = {"status": training.status}

    if training.status == "succeeded" and training.output:
        result["model_url"] = training.output.get("weights")

    return result


async def generate_photo(model_url: str, style_prompt: str) -> list[str]:
    """
    Генерирует фото с использованием обученной LoRA.
    Возвращает список URL готовых фото.
    """
    client = replicate.Client(api_token=REPLICATE_API_TOKEN)

    output = client.run(
        FLUX_MODEL,
        input={
            "prompt": f"a photo of TOK person, {style_prompt}",
            "hf_lora": model_url,
            "lora_scale": 0.9,
            "num_outputs": 4,          # 4 фото за раз
            "aspect_ratio": "2:3",
            "output_format": "jpg",
            "guidance_scale": 3.5,
            "output_quality": 90,
            "num_inference_steps": 28,
        }
    )

    return [str(url) for url in output]
