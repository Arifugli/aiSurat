users: dict = {}


def get_user(user_id: int) -> dict:
    if user_id not in users:
        users[user_id] = {
            "state": "idle",
            "photo_path": None,
            "generations_used": 0,
            "is_paid": False,
        }
    return users[user_id]


def set_state(user_id: int, state: str):
    get_user(user_id)["state"] = state

def set_photo(user_id: int, path: str):
    get_user(user_id)["photo_path"] = path

def get_photo(user_id: int):
    return get_user(user_id).get("photo_path")

def increment_generations(user_id: int):
    get_user(user_id)["generations_used"] += 1

def get_generations_used(user_id: int) -> int:
    return get_user(user_id).get("generations_used", 0)

def set_paid(user_id: int):
    get_user(user_id)["is_paid"] = True

def is_paid(user_id: int) -> bool:
    return get_user(user_id).get("is_paid", False)

def reset_user(user_id: int):
    users[user_id] = {
        "state": "idle",
        "photo_path": None,
        "generations_used": 0,
        "is_paid": False,
    }
