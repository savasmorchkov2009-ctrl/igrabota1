import asyncio
import logging
import sqlite3
import datetime
import random
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types.input_file import InputFile
from contextlib import closing

# ======================== НАСТРОЙКИ ========================
BOT_TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # Замените на токен вашего бота
ADMIN_IDS = [5887846215, 5189651311]  # ID администраторов (замените)

# Путь к папке с изображениями
IMAGES_PATH = "images"  # создайте папку images рядом со скриптом

# ======================== БАЗА ДАННЫХ ========================
DB_NAME = "racing_bot.db"

def init_db():
    """Создание таблиц, если их нет"""
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        # Таблица игроков
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            nickname TEXT,
            money INTEGER DEFAULT 1000,
            followers INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 1000,
            car_model TEXT,
            car_hp INTEGER,
            car_acceleration REAL,
            selected_car_image TEXT,
            daily_streak INTEGER DEFAULT 0,
            last_daily DATE,
            promo_used INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )''')
        # Таблица машин игрока
        c.execute('''CREATE TABLE IF NOT EXISTS user_cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_name TEXT,
            hp INTEGER,
            acceleration REAL,
            image TEXT,
            equipped INTEGER DEFAULT 0
        )''')
        # Таблица установленных улучшений (можно позже расширить)
        c.execute('''CREATE TABLE IF NOT EXISTS upgrades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_id INTEGER,
            part_type TEXT,
            part_name TEXT,
            hp_bonus INTEGER DEFAULT 0,
            acc_bonus REAL DEFAULT 0
        )''')
        # Таблица для промокодов
        c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward_type TEXT,
            reward_value INTEGER,
            uses_left INTEGER DEFAULT 1
        )''')
        # Таблица для вызовов на дуэль
        c.execute('''CREATE TABLE IF NOT EXISTS duels (
            duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER,
            opponent_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )''')
        # Таблица для донат-наборов
        c.execute('''CREATE TABLE IF NOT EXISTS donation_packs (
            pack_id TEXT PRIMARY KEY,
            name TEXT,
            price_rub INTEGER,
            description TEXT
        )''')
        # Таблица купленных донат-наборов (для учёта)
        c.execute('''CREATE TABLE IF NOT EXISTS user_packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pack_id TEXT,
            purchased_at TIMESTAMP
        )''')
        conn.commit()

# Заполнение таблицы машин начального выбора (обучение)
STARTER_CARS = [
    {
        "name": "Lancer X Sportback",
        "hp": 240,
        "acceleration": 6.5,
        "price": 0,
        "image": "lancer_x.jpg",
        "description": "Японский спорт-хэтчбек, полный привод, отличная управляемость."
    },
    {
        "name": "Opel Insignia OPC",
        "hp": 325,
        "acceleration": 5.8,
        "price": 0,
        "image": "opel_insignia.jpg",
        "description": "Немецкий заряженный универсал, мощный турбомотор и полный привод."
    },
    {
        "name": "Cadillac CTS",
        "hp": 304,
        "acceleration": 6.2,
        "price": 0,
        "image": "cadillac_cts.jpg",
        "description": "Американский премиум-седан, стиль и мощь V6."
    }
]

# ======================== КЛАССЫ СОСТОЯНИЙ ========================
class Registration(StatesGroup):
    waiting_nickname = State()

class Training(StatesGroup):
    choosing_car = State()
    viewing_car = State()
    race_ready = State()
    race_start_wait = State()

class Shop(StatesGroup):
    choosing_region = State()
    choosing_brand = State()
    choosing_model = State()
    parts_category = State()
    choosing_part = State()

class Duel(StatesGroup):
    entering_opponent = State()
    waiting_accept = State()
    race_ready_duel = State()
    race_start_wait_duel = State()

class Admin(StatesGroup):
    waiting_promo_code = State()
    waiting_promo_reward = State()
    waiting_user_id = State()
    waiting_ban_reason = State()
    waiting_give_money = State()

class Daily(StatesGroup):
    claim = State()

# ======================== ИНИЦИАЛИЗАЦИЯ ========================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========================
def get_user(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone()

def register_user(user_id, username, nickname):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, nickname) VALUES (?, ?, ?)",
                  (user_id, username, nickname))
        conn.commit()

def update_user_car(user_id, car):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET car_model = ?, car_hp = ?, car_acceleration = ?, selected_car_image = ? WHERE user_id = ?",
                  (car['name'], car['hp'], car['acceleration'], car['image'], user_id))
        # Добавляем машину в таблицу машин игрока
        c.execute("INSERT INTO user_cars (user_id, car_name, hp, acceleration, image, equipped) VALUES (?, ?, ?, ?, ?, 1)",
                  (user_id, car['name'], car['hp'], car['acceleration'], car['image']))
        conn.commit()

def add_money(user_id, amount):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

def add_followers(user_id, amount):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

def add_win(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET wins = wins + 1, rating = rating + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def add_loss(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET losses = losses + 1, rating = rating - 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ======================== КЛАВИАТУРЫ ========================
def main_menu_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏁 Гонка")
    kb.button(text="🚗 Мой гараж")
    kb.button(text="🏆 Топы")
    kb.button(text="🛒 Магазин")
    kb.button(text="🎁 Ежедневная награда")
    kb.button(text="⚙️ Профиль")
    kb.button(text="📦 Донат")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="cancel")
    return kb.as_markup()

# ======================== КОМАНДА СТАРТ И РЕГИСТРАЦИЯ ========================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user:
        # Пользователь уже зарегистрирован
        await message.answer(f"С возвращением, {user[2]}!", reply_markup=main_menu_keyboard())
    else:
        await state.set_state(Registration.waiting_nickname)
        await message.answer(
            "👋 Добро пожаловать в уличные гонки!\n"
            "Придумай себе никнейм (только буквы и цифры):",
            reply_markup=cancel_kb()
        )

@dp.message(Registration.waiting_nickname, F.text)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname.isalnum():
        await message.answer("Никнейм должен содержать только буквы и цифры. Попробуй ещё раз:")
        return
    user_id = message.from_user.id
    username = message.from_user.username or ""
    register_user(user_id, username, nickname)
    await state.clear()
    # Предлагаем обучение
    await message.answer(
        f"Отлично, {nickname}! Хочешь пройти обучение и получить первую машину?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, поехали!", callback_data="start_training")],
            [InlineKeyboardButton(text="⏪ Нет, потом", callback_data="skip_training")]
        ])
    )

# Пропуск обучения
@dp.callback_query(F.data == "skip_training")
async def skip_training(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Хорошо, можешь вернуться к обучению позже через профиль.",
                                  reply_markup=main_menu_keyboard())

# ======================== ОБУЧЕНИЕ: ВЫБОР МАШИНЫ ========================
@dp.callback_query(F.data == "start_training")
async def start_training(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Training.choosing_car)
    # Сохраняем индекс текущей просматриваемой машины
    await state.update_data(car_index=0, cars=STARTER_CARS)
    await show_car(callback.message, state)

async def show_car(message: Message, state: FSMContext):
    data = await state.get_data()
    cars = data['cars']
    index = data['car_index']
    car = cars[index]

    # Формируем клавиатуру
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выбрать", callback_data=f"choose_car_{index}")
    if index < len(cars)-1:
        kb.button(text="▶️ Следующий", callback_data="next_car")
    if index > 0:
        kb.button(text="◀️ Предыдущий", callback_data="prev_car")
    kb.adjust(1,2)

    # Проверяем наличие фото
    photo_path = os.path.join(IMAGES_PATH, car['image'])
    if os.path.exists(photo_path):
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=f"🚗 *{car['name']}*\n"
                    f"🏎 Лошадиные силы: {car['hp']} л.с.\n"
                    f"⚡ Разгон 0-100: {car['acceleration']} с\n"
                    f"📝 {car['description']}\n\n"
                    f"Это твоя стартовая машина. Выбери её!",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
    else:
        await message.answer(
            f"🚗 *{car['name']}*\n"
            f"🏎 Лошадиные силы: {car['hp']} л.с.\n"
            f"⚡ Разгон 0-100: {car['acceleration']} с\n"
            f"📝 {car['description']}\n\n"
            f"⚠️ Фото временно отсутствует. Выбери машину!",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )

@dp.callback_query(F.data == "next_car", Training.choosing_car)
async def next_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    index = data['car_index'] + 1
    await state.update_data(car_index=index)
    await callback.message.delete()
    await show_car(callback.message, state)

@dp.callback_query(F.data == "prev_car", Training.choosing_car)
async def prev_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    index = data['car_index'] - 1
    await state.update_data(car_index=index)
    await callback.message.delete()
    await show_car(callback.message, state)

@dp.callback_query(lambda c: c.data and c.data.startswith("choose_car_"), Training.choosing_car)
async def choose_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    cars = data['cars']
    car = cars[index]
    user_id = callback.from_user.id
    update_user_car(user_id, car)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        f"🎉 Поздравляю! Теперь у тебя есть {car['name']}.\n"
        f"Известность не за горами! Давай проведём первую гонку.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Участвовать в гонке", callback_data="training_race")]
        ])
    )

# ======================== ОБУЧЕНИЕ: ГОНКА ========================
@dp.callback_query(F.data == "training_race")
async def training_race_prepare(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = get_user(callback.from_user.id)
    car_name = user[6]  # car_model
    await state.set_state(Training.race_ready)
    await callback.message.delete()
    await callback.message.answer(
        f"🏁 *Тренировочная гонка*\n"
        f"Твоя машина: {car_name}\n"
        f"Правила: после нажатия кнопки *«Готов»* у тебя будет 5-6 секунд, чтобы нажать *«Старт»*.\n"
        f"❗ Раньше — фальстарт, позже — опоздание.\n\n"
        f"Готов?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готов", callback_data="ready_for_start")]
        ])
    )

@dp.callback_query(F.data == "ready_for_start", Training.race_ready)
async def training_race_ready(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Training.race_start_wait)
    ready_time = datetime.datetime.now()
    await state.update_data(ready_time=ready_time.timestamp())
    await callback.message.edit_text(
        "🟢 Готов! Теперь нажми *«Старт»* строго через 5-6 секунд.\n"
        "⏱ Жми в промежутке!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏎 СТАРТ", callback_data="start_pressed")]
        ])
    )

@dp.callback_query(F.data == "start_pressed", Training.race_start_wait)
async def training_race_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    ready_time = data['ready_time']
    now = datetime.datetime.now().timestamp()
    diff = now - ready_time

    if diff < 5:
        result = "❌ Фальстарт! Ты нажал раньше 5 секунд."
        success = False
    elif 5 <= diff <= 6:
        result = "✅ Отличный старт! Ты в промежутке."
        success = True
    else:
        result = "⏰ Опоздал! Более 6 секунд."
        success = False

    await callback.message.edit_text(result)
    await asyncio.sleep(1)

    if success:
        user = get_user(callback.from_user.id)
        car_hp = user[7] or 200
        # Имитация гонки
        await callback.message.answer(
            f"🚀 Твоя машина с {car_hp} л.с. мчит к финишу!\n"
            f"Ты проехал 500 м за {random.uniform(15,25):.1f} сек.\n"
            f"Ты победил в заезде!"
        )
        # Награда
        add_money(callback.from_user.id, 500)
        add_followers(callback.from_user.id, random.randint(50, 100))
        add_win(callback.from_user.id)
        await callback.message.answer(
            "💰 +500 монет\n"
            "📈 + подписчики\n"
            "🏅 Ты выиграл гонку!",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    else:
        await callback.message.answer(
            "💥 Ты проиграл старт и гонку. Не расстраивайся, попробуй ещё раз!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="training_race")]
            ])
        )
        add_loss(callback.from_user.id)
        await state.clear()  # или вернуть к выбору? Упростим: выходим

# ======================== ТОПЫ ========================
@dp.message(F.text == "🏆 Топы")
async def show_tops_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 По победам", callback_data="top_wins")
    kb.button(text="💰 По деньгам", callback_data="top_money")
    kb.button(text="📈 По подписчикам", callback_data="top_followers")
    kb.button(text="⚙️ По л.с.", callback_data="top_hp")
    kb.button(text="⚡ Разгон 0-100", callback_data="top_acc100")
    kb.button(text="⚡ Разгон 0-200", callback_data="top_acc200")
    kb.button(text="⚡ Разгон 0-300", callback_data="top_acc300")
    kb.adjust(2)
    await message.answer("🏆 Выбери категорию топа:", reply_markup=kb.as_markup())

async def send_top(callback: CallbackQuery, order_by, field_name, top_name):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        # Получаем топ-10 игроков
        if "acceleration" in order_by:
            # Для разгона – чем меньше, тем лучше
            query = f"SELECT nickname, username, {order_by} FROM users WHERE {order_by} IS NOT NULL ORDER BY {order_by} ASC LIMIT 10"
        else:
            query = f"SELECT nickname, username, {order_by} FROM users ORDER BY {order_by} DESC LIMIT 10"
        c.execute(query)
        rows = c.fetchall()

    text = f"🏆 Топ по {top_name}:\n\n"
    for i, row in enumerate(rows, 1):
        nick, user, value = row
        username = f"@{user}" if user else "—"
        text += f"{i}. {nick} ({username}) — {value}\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tops")]
    ]))

@dp.callback_query(F.data == "back_to_tops")
async def back_to_tops(callback: CallbackQuery):
    await callback.answer()
    await show_tops_menu(callback.message)

@dp.callback_query(F.data.startswith("top_"))
async def top_callback(callback: CallbackQuery):
    await callback.answer()
    mapping = {
        "top_wins": ("wins", "победам"),
        "top_money": ("money", "деньгам"),
        "top_followers": ("followers", "подписчикам"),
        "top_hp": ("car_hp", "лошадиным силам"),
        "top_acc100": ("car_acceleration", "разгону 0-100"),
        "top_acc200": ("car_acceleration", "разгону 0-200"),  # заглушка, одинаковые данные
        "top_acc300": ("car_acceleration", "разгону 0-300")
    }
    key = callback.data
    if key in mapping:
        field, name = mapping[key]
        await send_top(callback, field, field, name)

# ======================== ЕЖЕДНЕВНАЯ НАГРАДА ========================
DAILY_REWARDS = {
    1: {"money": 100, "followers": 10},
    2: {"money": 150, "followers": 20},
    3: {"money": 200, "followers": 30},
    4: {"money": 250, "followers": 40},
    5: {"money": 300, "followers": 50},
    6: {"money": 350, "followers": 60},
    7: {"money": 500, "followers": 100, "car_part": "Случайная запчасть"}  # можно расширить
}

@dp.message(F.text == "🎁 Ежедневная награда")
async def daily_reward(message: Message, state: FSMContext):
    user_id = message.from_user.id
    today = datetime.date.today()
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT daily_streak, last_daily FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        streak = row[0] or 0
        last = row[1]
        if last:
            last_date = datetime.date.fromisoformat(last)
            if last_date == today:
                await message.answer("Ты уже получал награду сегодня! Завтра будет новый день.")
                return
            elif last_date == today - datetime.timedelta(days=1):
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        # Не больше 7
        if streak > 7:
            streak = 7
        reward = DAILY_REWARDS[streak]
        # Выдаём награду
        if "money" in reward:
            c.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (reward["money"], user_id))
        if "followers" in reward:
            c.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", (reward["followers"], user_id))
        c.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?", (streak, today.isoformat(), user_id))
        conn.commit()

    text = f"🎁 День {streak}\n"
    if "money" in reward:
        text += f"+{reward['money']} монет\n"
    if "followers" in reward:
        text += f"+{reward['followers']} подписчиков\n"
    if "car_part" in reward:
        text += f"+{reward['car_part']}\n"
    await message.answer(text)

# ======================== ПРОМОКОДЫ (АДМИНКА) ========================
@dp.message(Command("addpromo"))
async def add_promo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет прав администратора.")
        return
    await state.set_state(Admin.waiting_promo_code)
    await message.answer("Введи промокод:")

@dp.message(Admin.waiting_promo_code, F.text)
async def promo_code_input(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(Admin.waiting_promo_reward)
    await message.answer("Введи награду в формате: money=500 или followers=100 (можно комбинировать через пробел)")

@dp.message(Admin.waiting_promo_reward, F.text)
async def promo_reward_input(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data['promo_code']
    reward_text = message.text
    # Упрощённо: сохраняем как есть
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO promocodes (code, reward_type, reward_value, uses_left) VALUES (?, ?, ?, 1)",
                  (code, reward_text, 0))
        conn.commit()
    await state.clear()
    await message.answer(f"Промокод {code} добавлен!")

@dp.message(F.text.startswith("/promo"))
async def use_promo(message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Используй: /promo КОД")
        return
    code = parts[1].upper()
    user_id = message.from_user.id
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        # Проверяем, использовал ли уже
        c.execute("SELECT promo_used FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone()[0] == 1:
            await message.answer("Ты уже использовал промокод.")
            return
        # Ищем код
        c.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
        row = c.fetchone()
        if not row or row[3] <= 0:
            await message.answer("Недействительный промокод.")
            return
        # Выдаём награду (упрощённо парсим строку)
        reward_str = row[1]
        # Пример: money=500 followers=100
        parts_reward = reward_str.split()
        for part in parts_reward:
            if "=" in part:
                key, val = part.split("=")
                val = int(val)
                if key == "money":
                    c.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (val, user_id))
                elif key == "followers":
                    c.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", (val, user_id))
                # можно добавить другие награды
        # Уменьшаем количество использований
        c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        c.execute("UPDATE users SET promo_used = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    await message.answer("✅ Промокод активирован!")

# ======================== АДМИНКА: БАН / ВЫДАЧА РЕСУРСОВ ========================
@dp.message(Command("ban"))
async def ban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Admin.waiting_user_id)
    await message.answer("Введи ID пользователя для бана:")

@dp.message(Admin.waiting_user_id, F.text)
async def process_ban(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        with closing(sqlite3.connect(DB_NAME)) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        await message.answer(f"Пользователь {user_id} забанен.")
    except:
        await message.answer("Неверный ID.")
    await state.clear()

@dp.message(Command("give"))
async def give_resources(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Admin.waiting_user_id)
    await state.update_data(action="give")
    await message.answer("Введи ID пользователя:")

@dp.message(Admin.waiting_user_id, F.text)
async def process_give_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user=user_id)
        await state.set_state(Admin.waiting_give_money)
        await message.answer("Введи количество монет для выдачи:")
    except:
        await message.answer("Неверный ID.")
        await state.clear()

@dp.message(Admin.waiting_give_money, F.text)
async def process_give_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        data = await state.get_data()
        user_id = data['target_user']
        add_money(user_id, amount)
        await message.answer(f"Выдано {amount} монет пользователю {user_id}.")
    except:
        await message.answer("Неверная сумма.")
    await state.clear()

# ======================== ДОНАТ (УПРОЩЁННО) ========================
DONATION_PACKS = {
    "novice1": {"name": "Набор новичка", "price": 50, "desc": "500 монет + Toyota Corolla", "money": 500, "car": "Toyota Corolla"},
    "novice2": {"name": "Набор новичка 2", "price": 100, "desc": "1000 монет + Volkswagen Golf", "money": 1000, "car": "Volkswagen Golf"},
    "novice3": {"name": "Набор новичка 3", "price": 150, "desc": "1500 монет + Ford F-Series", "money": 1500, "car": "Ford F-Series"},
    "pro1": {"name": "Продвинутый набор", "price": 300, "desc": "5000 монет + Garrett GT28", "money": 5000, "part": "Garrett GT28"},
    "pro2": {"name": "Набор тюнера", "price": 500, "desc": "10000 монет + Akrapovič Evolution", "money": 10000, "part": "Akrapovič Evolution"},
    "pro3": {"name": "Набор коллекционера", "price": 800, "desc": "20000 монет + Mercedes-Benz C-Class", "money": 20000, "car": "Mercedes-Benz C-Class"},
    "pro4": {"name": "Набор легенды", "price": 1500, "desc": "50000 монет + NOS Sniper Kit", "money": 50000, "part": "NOS Sniper Kit"},
    "pro5": {"name": "VIP набор", "price": 3000, "desc": "100000 монет + Öhlins Road & Track", "money": 100000, "part": "Öhlins Road & Track"}
}

@dp.message(F.text == "📦 Донат")
async def donation_menu(message: Message):
    kb = InlineKeyboardBuilder()
    for pack_id, pack in DONATION_PACKS.items():
        kb.button(text=f"{pack['name']} ({pack['price']} руб)", callback_data=f"donate_{pack_id}")
    kb.adjust(1)
    await message.answer("💰 Доступные наборы:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith("donate_"))
async def donate_pack_info(callback: CallbackQuery):
    pack_id = callback.data.split("_")[1]
    pack = DONATION_PACKS[pack_id]
    text = f"*{pack['name']}*\n{pack['desc']}\nЦена: {pack['price']} руб."
    # Здесь должна быть интеграция с платежной системой, но упростим
    text += "\n\n💳 Для покупки свяжитесь с администратором."
    await callback.message.edit_text(text, parse_mode="Markdown")

# ======================== ПРОФИЛЬ ========================
@dp.message(F.text == "⚙️ Профиль")
async def profile(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    nickname, money, followers, wins, losses, rating, car_model = user[2], user[3], user[4], user[5], user[6], user[7], user[8]
    text = (
        f"👤 *Никнейм:* {nickname}\n"
        f"💰 *Деньги:* {money}\n"
        f"📈 *Подписчики:* {followers}\n"
        f"🏁 *Победы:* {wins}\n"
        f"💔 *Поражения:* {losses}\n"
        f"🏆 *Рейтинг:* {rating}\n"
        f"🚗 *Текущая машина:* {car_model or 'нет'}\n"
    )
    await message.answer(text, parse_mode="Markdown")

# ======================== МАГАЗИН (ЗАГОТОВКА) ========================
# Данные марок и моделей (неполные для примера)
EUROPE_BRANDS = {
    "Volkswagen": ["Golf", "Passat"],
    "Mercedes-Benz": ["C-Class"],
    "BMW": ["M54"]
}
ASIAN_BRANDS = {
    "Toyota": ["Corolla (AE86)", "Camry", "RAV4", "Land Cruiser"]
}
US_BRANDS = {
    "Ford": ["F-Series"],
    "Chevrolet": ["Silverado"],
    "Ram": ["1500"],
    "GMC": []
}

@dp.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇪🇺 Европейский автодром", callback_data="shop_europe")
    kb.button(text="🇯🇵 Азиатский автодром", callback_data="shop_asia")
    kb.button(text="🇺🇸 Американский автодром", callback_data="shop_usa")
    kb.button(text="🔧 Комплектующие", callback_data="shop_parts")
    kb.adjust(1)
    await message.answer("🛒 Выбери категорию:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("shop_"))
async def shop_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split("_")[1]
    if region == "europe":
        brands = EUROPE_BRANDS
    elif region == "asia":
        brands = ASIAN_BRANDS
    elif region == "usa":
        brands = US_BRANDS
    elif region == "parts":
        # Меню запчастей
        await show_parts_menu(callback)
        return
    else:
        return
    await state.set_state(Shop.choosing_brand)
    await state.update_data(region=region, brands=brands)
    kb = InlineKeyboardBuilder()
    for brand in brands.keys():
        kb.button(text=brand, callback_data=f"brand_{brand}")
    kb.button(text="◀️ Назад", callback_data="back_to_shop")
    kb.adjust(2)
    await callback.message.edit_text("Выбери марку:", reply_markup=kb.as_markup())

async def show_parts_menu(callback: CallbackQuery):
    parts_categories = [
        ("Двигатели", "engines"),
        ("Турбины", "turbos"),
        ("Выхлопы", "exhausts"),
        ("Радиаторы", "radiators"),
        ("Закись азота", "nitro"),
        ("Амортизаторы", "suspension")
    ]
    kb = InlineKeyboardBuilder()
    for name, cb in parts_categories:
        kb.button(text=name, callback_data=f"partcat_{cb}")
    kb.button(text="◀️ Назад", callback_data="back_to_shop")
    kb.adjust(2)
    await callback.message.edit_text("🔧 Выбери тип запчасти:", reply_markup=kb.as_markup())

# Здесь нужно реализовать просмотр конкретных запчастей, кнопки купить и т.д.
# Из-за ограничения объёма оставляем заглушки

# ======================== ДУЭЛИ (УПРОЩЁННО) ========================
@dp.message(F.text == "🏁 Гонка")
async def duel_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Вызвать на дуэль", callback_data="duel_challenge")
    kb.button(text="🏁 Быстрая гонка (с ботом)", callback_data="quick_race")
    await message.answer("Выбери режим гонки:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "quick_race")
async def quick_race(callback: CallbackQuery):
    # Заглушка: просто гонка с ботом
    await callback.message.answer("Режим быстрой гонки в разработке.")

@dp.callback_query(F.data == "duel_challenge")
async def duel_challenge(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Duel.entering_opponent)
    await callback.message.edit_text(
        "Введи ID пользователя или @username Telegram для вызова:",
        reply_markup=cancel_kb()
    )

@dp.message(Duel.entering_opponent, F.text)
async def duel_enter_opponent(message: Message, state: FSMContext):
    target = message.text.strip()
    # Попытка найти пользователя
    opponent_id = None
    if target.isdigit():
        opponent_id = int(target)
    elif target.startswith('@'):
        username = target[1:]
        with closing(sqlite3.connect(DB_NAME)) as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if row:
                opponent_id = row[0]
    if not opponent_id:
        await message.answer("Пользователь не найден. Попробуй ещё раз.")
        return

    user_id = message.from_user.id
    if opponent_id == user_id:
        await message.answer("Нельзя вызвать самого себя.")
        return

    # Создаём вызов
    created = datetime.datetime.now()
    expires = created + datetime.timedelta(minutes=5)
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO duels (challenger_id, opponent_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                  (user_id, opponent_id, created.isoformat(), expires.isoformat()))
        conn.commit()
        duel_id = c.lastrowid

    await state.clear()
    await message.answer(f"Вызов отправлен! Действителен 5 минут.")

    # Отправляем уведомление оппоненту (если он есть в системе)
    try:
        await bot.send_message(
            opponent_id,
            f"⚔️ Вас вызвал на дуэль пользователь {message.from_user.full_name}!\n"
            f"Гонка состоится, если вы примете вызов в течение 5 минут.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_duel_{duel_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_duel_{duel_id}")]
            ])
        )
    except:
        # Оппонент не доступен (бот не может написать первым)
        pass

@dp.callback_query(lambda c: c.data and c.data.startswith("accept_duel_"))
async def accept_duel(callback: CallbackQuery, state: FSMContext):
    duel_id = int(callback.data.split("_")[2])
    # Проверка срока действия и т.д.
    # Упрощённо: запускаем гонку
    await callback.answer()
    await callback.message.edit_text("Дуэль принята! Готовься к гонке...")
    # Здесь можно перейти в состояние гонки аналогично обучению
    # Для краткости пропускаем

# ======================== ЗАПУСК БОТА ========================
async def main():
    init_db()
    # Создаём папку images, если её нет
    if not os.path.exists(IMAGES_PATH):
        os.makedirs(IMAGES_PATH)
        print(f"⚠️ Папка '{IMAGES_PATH}' создана. Поместите туда изображения с именами:")
        for car in STARTER_CARS:
            print(f"   - {car['image']}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
