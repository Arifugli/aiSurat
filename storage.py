"""
Простое хранилище состояний пользователей в памяти.
В продакшене заменить на Redis или PostgreSQL.
"""

# Структура: { user_id: { "state": ..., "photos": [...], "training_id": ..., "model_url": ... } }
users: dict = {}


def get_user(user_id: int) -> dict:
    if user_id not in users:
        users[user_id] = {
            "state": "idle",        # idle | collecting_photos | training | ready
            "photos": [],           # список путей к фото
            "training_id": None,    # ID тренировки на Replicate
            "model_url": None,      # URL обученной модели
        }
    return users[user_id]


def set_state(user_id: int, state: str):
    get_user(user_id)["state"] = state


def add_photo(user_id: int, photo_path: str):
    get_user(user_id)["photos"].append(photo_path)


def get_photos(user_id: int) -> list:
    return get_user(user_id)["photos"]


def set_training_id(user_id: int, training_id: str):
    get_user(user_id)["training_id"] = training_id


def get_training_id(user_id: int) -> str | None:
    return get_user(user_id).get("training_id")


def set_model_url(user_id: int, model_url: str):
    get_user(user_id)["model_url"] = model_url
    get_user(user_id)["state"] = "ready"


def get_model_url(user_id: int) -> str | None:
    return get_user(user_id).get("model_url")


def reset_user(user_id: int):
    users[user_id] = {
        "state": "idle",
        "photos": [],
        "training_id": None,
        "model_url": None,
    }
