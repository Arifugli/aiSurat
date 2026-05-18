# 📸 ИИ Фотосессия Бот

Telegram-бот для генерации персональных ИИ-фотосессий на базе Flux LoRA.

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Создай Telegram бота
1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Напиши `/newbot`
3. Следуй инструкциям, получи токен вида `123456:ABC-DEF...`

### 3. Получи Replicate API токен
1. Зарегистрируйся на [replicate.com](https://replicate.com)
2. Перейди в Account → API tokens
3. Нажми "Create token"

### 4. Создай файл .env
```bash
cp .env.example .env
```
Открой `.env` и вставь свои токены:
```
BOT_TOKEN=123456:ABC-DEF...
REPLICATE_API_TOKEN=r8_xxxx...
```

### 5. Настрой Replicate (важно!)
В файле `replicate_api.py` замени строку:
```python
destination=f"your-replicate-username/user-{user_id}-lora",
```
На своё имя пользователя Replicate:
```python
destination=f"твой_username/user-{user_id}-lora",
```

### 6. Запуск
```bash
python bot.py
```

---

## 📁 Структура проекта

```
photo_bot/
├── bot.py            # Точка входа, запуск бота
├── handlers.py       # Обработчики сообщений и кнопок
├── replicate_api.py  # Работа с Replicate AI
├── storage.py        # Хранение состояний пользователей
├── config.py         # Настройки и стили
├── requirements.txt  # Зависимости
└── .env              # Секретные токены (не коммитить в git!)
```

## 🔄 Флоу пользователя

1. `/start` → Приветствие
2. Нажимает «Начать загрузку фото»
3. Отправляет 10–20 своих фото
4. Нажимает «Начать обучение» → ждёт ~20 мин
5. Получает уведомление о готовности
6. Выбирает стиль → получает 4 фото

## 💰 Стоимость на Replicate

- Обучение LoRA: ~$0.30–0.50 за одного пользователя
- Генерация 4 фото: ~$0.05–0.10
- Первые $5 бесплатно при регистрации

## 🛠 Следующие шаги (после прототипа)

- [ ] Добавить платежи (Telegram Stars / ЮKassa)
- [ ] Перенести хранилище на PostgreSQL + Redis
- [ ] Добавить очередь задач (Celery)
- [ ] Деплой на VPS (DigitalOcean / Hetzner)
- [ ] Добавить кастомные промпты от пользователя
