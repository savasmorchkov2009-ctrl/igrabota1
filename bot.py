import asyncio
import logging
import sqlite3
import datetime
import random
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from contextlib import closing

# ======================== НАСТРОЙКИ ========================
BOT_TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"          # ⚠️ Замените на токен вашего бота
ADMIN_IDS = [5887846215, 5189651311]    # ⚠️ ID администраторов
IMAGES_PATH = "images"                # папка с фотографиями
DB_NAME = "racing_bot.db"

# ======================== ИНИЦИАЛИЗАЦИЯ БОТА ========================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)      # ← Теперь dp определён до всех декораторов

# ======================== БАЗА ДАННЫХ ========================
def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        # Пользователи
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            nickname TEXT UNIQUE,
            money INTEGER DEFAULT 1000,
            followers INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 1000,
            car_model TEXT,
            car_hp INTEGER,
            acc_100 REAL,
            acc_200 REAL,
            acc_300 REAL,
            selected_car_image TEXT,
            daily_streak INTEGER DEFAULT 0,
            last_daily DATE,
            promo_used INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )''')
        # Машины игрока
        c.execute('''CREATE TABLE IF NOT EXISTS user_cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_name TEXT,
            base_hp INTEGER,
            base_acc_100 REAL,
            base_acc_200 REAL,
            base_acc_300 REAL,
            image TEXT,
            equipped INTEGER DEFAULT 0
        )''')
        # Установленные улучшения
        c.execute('''CREATE TABLE IF NOT EXISTS upgrades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_id INTEGER,
            part_type TEXT,
            part_name TEXT,
            hp_bonus INTEGER DEFAULT 0,
            acc_100_bonus REAL DEFAULT 0,
            acc_200_bonus REAL DEFAULT 0,
            acc_300_bonus REAL DEFAULT 0
        )''')
        # Инвентарь запчастей
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            part_type TEXT,
            part_name TEXT,
            hp_bonus INTEGER,
            acc_100_bonus REAL,
            acc_200_bonus REAL,
            acc_300_bonus REAL,
            installed INTEGER DEFAULT 0
        )''')
        # Промокоды
        c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward TEXT,
            uses_left INTEGER DEFAULT 1
        )''')
        # Дуэли
        c.execute('''CREATE TABLE IF NOT EXISTS duels (
            duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER,
            opponent_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )''')
        # Боксы
        c.execute('''CREATE TABLE IF NOT EXISTS boxes (
            box_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            box_type TEXT,
            opened INTEGER DEFAULT 0,
            received_at TIMESTAMP
        )''')
        conn.commit()

# ======================== КОНСТАНТЫ ========================
STARTER_CARS = [
    {"name": "Lancer X Sportback", "hp": 240, "acc_100": 6.5, "acc_200": 18.2, "acc_300": 45.0, "image": "lancer_x.jpg"},
    {"name": "Opel Insignia OPC", "hp": 325, "acc_100": 5.8, "acc_200": 16.5, "acc_300": 41.0, "image": "opel_insignia.jpg"},
    {"name": "Cadillac CTS", "hp": 304, "acc_100": 6.2, "acc_200": 17.3, "acc_300": 43.0, "image": "cadillac_cts.jpg"}
]

EUROPE_CARS = {
    "Volkswagen": [
        {"name": "Golf GTI", "hp": 245, "acc_100": 6.4, "acc_200": 17.8, "acc_300": 44.0, "price": 15000, "image": "golf.jpg"},
        {"name": "Passat R", "hp": 280, "acc_100": 5.9, "acc_200": 16.2, "acc_300": 40.5, "price": 22000, "image": "passat.jpg"}
    ],
    "Mercedes-Benz": [
        {"name": "C-Class AMG", "hp": 380, "acc_100": 4.8, "acc_200": 13.5, "acc_300": 34.0, "price": 45000, "image": "c_class.jpg"}
    ],
    "BMW": [
        {"name": "M3", "hp": 450, "acc_100": 4.2, "acc_200": 12.0, "acc_300": 30.0, "price": 55000, "image": "m3.jpg"}
    ]
}

ASIAN_CARS = {
    "Toyota": [
        {"name": "Corolla AE86", "hp": 130, "acc_100": 8.6, "acc_200": 24.0, "acc_300": 60.0, "price": 8000, "image": "ae86.jpg"},
        {"name": "Camry TRD", "hp": 301, "acc_100": 5.8, "acc_200": 16.0, "acc_300": 40.0, "price": 28000, "image": "camry.jpg"},
        {"name": "RAV4 Prime", "hp": 302, "acc_100": 5.7, "acc_200": 15.8, "acc_300": 39.5, "price": 32000, "image": "rav4.jpg"},
        {"name": "Land Cruiser", "hp": 381, "acc_100": 6.7, "acc_200": 18.5, "acc_300": 46.0, "price": 60000, "image": "landcruiser.jpg"}
    ]
}

US_CARS = {
    "Ford": [{"name": "F-150 Raptor", "hp": 450, "acc_100": 5.2, "acc_200": 14.5, "acc_300": 36.0, "price": 50000, "image": "f150.jpg"}],
    "Chevrolet": [{"name": "Silverado", "hp": 355, "acc_100": 6.8, "acc_200": 19.0, "acc_300": 48.0, "price": 35000, "image": "silverado.jpg"}],
    "Ram": [{"name": "1500 TRX", "hp": 702, "acc_100": 4.5, "acc_200": 12.8, "acc_300": 32.0, "price": 70000, "image": "ram1500.jpg"}],
    "GMC": [{"name": "Sierra Denali", "hp": 420, "acc_100": 5.9, "acc_200": 16.5, "acc_300": 41.0, "price": 48000, "image": "sierra.jpg"}]
}

PARTS = {
    "engine": [
        {"name": "Volkswagen EA888 (1.8T)", "hp": 30, "acc_100": -0.3, "acc_200": -0.8, "acc_300": -2.0, "price": 5000, "image": "ea888.jpg"},
        {"name": "Mercedes-Benz M104", "hp": 45, "acc_100": -0.4, "acc_200": -1.0, "acc_300": -2.5, "price": 7000, "image": "m104.jpg"},
        {"name": "BMW B58", "hp": 60, "acc_100": -0.5, "acc_200": -1.2, "acc_300": -3.0, "price": 9000, "image": "b58.jpg"}
    ],
    "turbo": [
        {"name": "Garrett GT28", "hp": 50, "acc_100": -0.4, "acc_200": -1.0, "acc_300": -2.5, "price": 8000, "image": "gt28.jpg"},
        {"name": "Garrett GT30", "hp": 70, "acc_100": -0.6, "acc_200": -1.5, "acc_300": -3.5, "price": 11000, "image": "gt30.jpg"},
        {"name": "Garrett GT35", "hp": 90, "acc_100": -0.8, "acc_200": -2.0, "acc_300": -4.5, "price": 15000, "image": "gt35.jpg"},
        {"name": "Garrett GTX35", "hp": 110, "acc_100": -1.0, "acc_200": -2.5, "acc_300": -5.5, "price": 20000, "image": "gtx35.jpg"}
    ],
    "exhaust": [
        {"name": "Akrapovič Evolution", "hp": 15, "acc_100": -0.1, "acc_200": -0.3, "acc_300": -0.7, "price": 3000, "image": "akra.jpg"},
        {"name": "Remus PowerSound", "hp": 12, "acc_100": -0.1, "acc_200": -0.2, "acc_300": -0.5, "price": 2500, "image": "remus.jpg"},
        {"name": "Milltek Non-Resonated", "hp": 10, "acc_100": -0.1, "acc_200": -0.2, "acc_300": -0.5, "price": 2000, "image": "milltek.jpg"}
    ],
    "radiator": [
        {"name": "Nissens Performance", "hp": 0, "acc_100": 0.0, "acc_200": -0.1, "acc_300": -0.3, "price": 1500, "image": "nissens.jpg"},
        {"name": "Behr Hella OEM Plus", "hp": 0, "acc_100": 0.0, "acc_200": -0.1, "acc_300": -0.2, "price": 1200, "image": "behr.jpg"}
    ],
    "nitro": [
        {"name": "NOS Sniper Kit", "hp": 75, "acc_100": -0.5, "acc_200": -1.3, "acc_300": -3.0, "price": 12000, "image": "nos_sniper.jpg"},
        {"name": "NOS Cheater Kit", "hp": 100, "acc_100": -0.7, "acc_200": -1.8, "acc_300": -4.0, "price": 18000, "image": "nos_cheater.jpg"},
        {"name": "NOS Powershot Kit", "hp": 125, "acc_100": -0.9, "acc_200": -2.2, "acc_300": -5.0, "price": 25000, "image": "nos_powershot.jpg"}
    ],
    "suspension": [
        {"name": "Koni Sport (Желтые)", "hp": 0, "acc_100": -0.2, "acc_200": -0.5, "acc_300": -1.0, "price": 2000, "image": "koni.jpg"},
        {"name": "Bilstein B8 (Sport)", "hp": 0, "acc_100": -0.2, "acc_200": -0.5, "acc_300": -1.1, "price": 2200, "image": "bilstein.jpg"},
        {"name": "Öhlins Road & Track", "hp": 0, "acc_100": -0.3, "acc_200": -0.7, "acc_300": -1.5, "price": 3500, "image": "ohlins.jpg"}
    ]
}

DONATION_PACKS = {
    "novice": {"name": "Набор новичка", "price": 50, "desc": "500 монет + бокс 'Лёгкий'", "money": 500, "box": "light"},
    "racer": {"name": "Набор гонщика", "price": 150, "desc": "1500 монет + бокс 'Средний'", "money": 1500, "box": "medium"},
    "pro": {"name": "Набор профи", "price": 300, "desc": "4000 монет + бокс 'Тяжёлый'", "money": 4000, "box": "heavy"},
    "vip": {"name": "VIP набор", "price": 600, "desc": "9000 монет + бокс 'Тяжёлый' x2", "money": 9000, "box": "heavy", "boxes": 2},
    "legend": {"name": "Набор легенды", "price": 1200, "desc": "20000 монет + бокс 'Тяжёлый' x5", "money": 20000, "box": "heavy", "boxes": 5}
}

DAILY_REWARDS = {
    1: {"money": 100, "followers": 10},
    2: {"money": 150, "followers": 20},
    3: {"money": 200, "followers": 30},
    4: {"money": 250, "followers": 40},
    5: {"money": 300, "followers": 50},
    6: {"money": 350, "followers": 60},
    7: {"money": 500, "followers": 100, "box": "light"}
}

# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ БД ========================
def get_user(user_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone()

def is_banned(user_id):
    user = get_user(user_id)
    return user and user[17] == 1  # is_banned индекс 17

def register_user(user_id, username, nickname):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (user_id, username, nickname) VALUES (?, ?, ?)",
                      (user_id, username, nickname))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def update_user_car(user_id, car):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE user_cars SET equipped = 0 WHERE user_id = ?", (user_id,))
        c.execute('''INSERT INTO user_cars 
            (user_id, car_name, base_hp, base_acc_100, base_acc_200, base_acc_300, image, equipped) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)''',
            (user_id, car['name'], car['hp'], car['acc_100'], car['acc_200'], car['acc_300'], car['image']))
        c.execute('''UPDATE users SET 
            car_model = ?, car_hp = ?, acc_100 = ?, acc_200 = ?, acc_300 = ?, selected_car_image = ? 
            WHERE user_id = ?''',
            (car['name'], car['hp'], car['acc_100'], car['acc_200'], car['acc_300'], car['image'], user_id))
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

def give_box(user_id, box_type):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO boxes (user_id, box_type, received_at) VALUES (?, ?, ?)",
                  (user_id, box_type, datetime.datetime.now().isoformat()))
        conn.commit()
        return c.lastrowid

def open_box(user_id, box_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT box_type, opened FROM boxes WHERE box_id = ? AND user_id = ?", (box_id, user_id))
        row = c.fetchone()
        if not row or row[1] == 1:
            return None, "Бокс уже открыт или не найден"
        box_type = row[0]
        if box_type == "win":
            parts_pool = PARTS["exhaust"] + PARTS["radiator"] + PARTS["suspension"]
        elif box_type == "light":
            parts_pool = PARTS["exhaust"] + PARTS["radiator"] + PARTS["suspension"] + PARTS["turbo"][:2]
        elif box_type == "medium":
            parts_pool = PARTS["turbo"] + PARTS["engine"] + PARTS["nitro"][:2]
        elif box_type == "heavy":
            parts_pool = PARTS["engine"] + PARTS["turbo"] + PARTS["nitro"]
        else:
            parts_pool = list(PARTS.values())
        part = random.choice(parts_pool)
        c.execute('''INSERT INTO inventory 
            (user_id, part_type, part_name, hp_bonus, acc_100_bonus, acc_200_bonus, acc_300_bonus, installed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)''',
            (user_id, "box", part["name"], part["hp"], part["acc_100"], part["acc_200"], part["acc_300"]))
        c.execute("UPDATE boxes SET opened = 1 WHERE box_id = ?", (box_id,))
        conn.commit()
        return part, "ok"

# ======================== СОСТОЯНИЯ FSM ========================
class Registration(StatesGroup):
    waiting_nickname = State()

class Training(StatesGroup):
    choosing_car = State()
    race_ready = State()
    race_start_wait = State()

class Shop(StatesGroup):
    choosing_region = State()
    choosing_brand = State()
    choosing_model = State()
    parts_category = State()
    choosing_part = State()
    confirm_purchase = State()

class Duel(StatesGroup):
    entering_opponent = State()
    race_ready = State()
    race_start_wait = State()

class Admin(StatesGroup):
    waiting_promo_code = State()
    waiting_promo_reward = State()
    waiting_user_id = State()
    waiting_ban_reason = State()
    waiting_give_money = State()
    waiting_give_box = State()
    waiting_box_type = State()

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

# ======================== СТАРТ И РЕГИСТРАЦИЯ ========================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.answer("⛔ Вы забанены и не можете использовать бота.")
        return
    user = get_user(user_id)
    if user:
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
    if not re.match(r'^[a-zA-Z0-9]+$', nickname):
        await message.answer("Никнейм должен содержать только латинские буквы и цифры. Попробуй ещё раз:")
        return
    user_id = message.from_user.id
    username = message.from_user.username or ""
    if register_user(user_id, username, nickname):
        await state.clear()
        await message.answer(
            f"Отлично, {nickname}! Хочешь пройти обучение и получить первую машину?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, поехали!", callback_data="start_training")],
                [InlineKeyboardButton(text="⏪ Нет, потом", callback_data="skip_training")]
            ])
        )
    else:
        await message.answer("Этот никнейм уже занят. Выбери другой:")

@dp.callback_query(F.data == "skip_training")
async def skip_training(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Хорошо, можешь вернуться к обучению позже через профиль.",
                                  reply_markup=main_menu_keyboard())

# ======================== ОБУЧЕНИЕ ========================
@dp.callback_query(F.data == "start_training")
async def start_training(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Training.choosing_car)
    await state.update_data(car_index=0, cars=STARTER_CARS)
    await show_car(callback.message, state)

async def show_car(message: Message, state: FSMContext):
    data = await state.get_data()
    cars = data['cars']
    index = data['car_index']
    car = cars[index]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выбрать", callback_data=f"choose_car_{index}")
    if index < len(cars)-1:
        kb.button(text="▶️ Следующий", callback_data="next_car")
    if index > 0:
        kb.button(text="◀️ Предыдущий", callback_data="prev_car")
    kb.adjust(1,2)
    caption = (f"🚗 *{car['name']}*\n"
               f"🏎 Л.с.: {car['hp']}\n"
               f"⚡ 0-100: {car['acc_100']}с\n"
               f"⚡ 0-200: {car['acc_200']}с\n"
               f"⚡ 0-300: {car['acc_300']}с")
    photo_path = os.path.join(IMAGES_PATH, car['image'])
    if os.path.exists(photo_path):
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
    else:
        await message.answer(caption + "\n⚠️ Фото отсутствует", parse_mode="Markdown", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "next_car", Training.choosing_car)
async def next_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['car_index'] += 1
    await state.update_data(data)
    await callback.message.delete()
    await show_car(callback.message, state)

@dp.callback_query(F.data == "prev_car", Training.choosing_car)
async def prev_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['car_index'] -= 1
    await state.update_data(data)
    await callback.message.delete()
    await show_car(callback.message, state)

@dp.callback_query(lambda c: c.data and c.data.startswith("choose_car_"), Training.choosing_car)
async def choose_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    car = data['cars'][index]
    user_id = callback.from_user.id
    update_user_car(user_id, car)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        f"🎉 Поздравляю! Теперь у тебя есть {car['name']}.\n"
        f"Давай проведём первую гонку.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Участвовать в гонке", callback_data="training_race")]
        ])
    )

# ======================== ГОНКИ (ОБУЧЕНИЕ / БЫСТРАЯ) ========================
@dp.callback_query(F.data == "training_race")
async def training_race_prepare(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = get_user(callback.from_user.id)
    if not user or not user[8]:
        await callback.message.answer("Сначала выбери машину в гараже!")
        return
    await state.set_state(Training.race_ready)
    await callback.message.delete()
    await callback.message.answer(
        "🏁 *Тренировочная гонка*\n"
        "Правила: после нажатия *«Готов»* у тебя будет 5-6 секунд, чтобы нажать *«Старт»*.\n"
        "❗ Раньше — фальстарт, позже — опоздание.\n\n"
        "Готов?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готов", callback_data="race_ready")]
        ])
    )

@dp.callback_query(F.data == "race_ready", Training.race_ready)
async def race_ready(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Training.race_start_wait)
    ready_time = datetime.datetime.now()
    await state.update_data(ready_time=ready_time.timestamp())
    await callback.message.edit_text(
        "🟢 Готов! Жми *«Старт»* через 5–6 секунд.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏎 СТАРТ", callback_data="race_start")]
        ])
    )

@dp.callback_query(F.data == "race_start", Training.race_start_wait)
async def race_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    ready_time = data.get('ready_time')
    if not ready_time:
        await callback.message.answer("Ошибка: перезапусти гонку.")
        await state.clear()
        return
    now = datetime.datetime.now().timestamp()
    diff = now - ready_time
    user_id = callback.from_user.id
    if diff < 5:
        result_text = "❌ Фальстарт! Ты проиграл."
        add_loss(user_id)
        win = False
    elif 5 <= diff <= 6:
        result_text = "✅ Идеальный старт! Ты едешь к финишу."
        win = True
    else:
        result_text = "⏰ Опоздал! Проигрыш."
        add_loss(user_id)
        win = False
    await callback.message.edit_text(result_text)
    await asyncio.sleep(1.5)
    if win:
        user = get_user(user_id)
        acc_100 = user[10]
        time_on_track = 10 + (acc_100 * 0.5)
        await callback.message.answer(
            f"🚀 Ты проехал 500 м за {time_on_track:.1f} сек и победил!\n"
            f"💰 +500 монет\n📈 +{random.randint(50,100)} подписчиков"
        )
        add_money(user_id, 500)
        add_followers(user_id, random.randint(50,100))
        add_win(user_id)
        if random.random() < 0.2:
            give_box(user_id, "win")
            await callback.message.answer("🎁 Ты получил бокс за победу!")
    else:
        await callback.message.answer("💥 Попробуй ещё раз!")
    await state.clear()

# ======================== БОКСЫ ========================
@dp.message(F.text == "🎁 Мои боксы")
async def my_boxes(message: Message):
    user_id = message.from_user.id
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT box_id, box_type, opened, received_at FROM boxes WHERE user_id = ? ORDER BY received_at DESC", (user_id,))
        boxes = c.fetchall()
    if not boxes:
        await message.answer("У тебя пока нет боксов.")
        return
    text = "📦 Твои боксы:\n"
    kb = InlineKeyboardBuilder()
    for box in boxes:
        box_id, box_type, opened, rec = box
        status = "✅ Открыт" if opened else "❌ Закрыт"
        text += f"#{box_id} - {box_type}, {status}\n"
        if not opened:
            kb.button(text=f"Открыть бокс #{box_id}", callback_data=f"open_box_{box_id}")
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup() if kb.buttons else None)

@dp.callback_query(lambda c: c.data and c.data.startswith("open_box_"))
async def open_box_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    box_id = int(callback.data.split("_")[2])
    part, msg = open_box(user_id, box_id)
    if part:
        await callback.message.edit_text(
            f"🎉 Ты открыл бокс и получил:\n"
            f"🔧 {part['name']}\n"
            f"+{part['hp']} л.с., разгон: {part['acc_100']}с (0-100)\n"
            f"Запчасть добавлена в инвентарь."
        )
    else:
        await callback.message.edit_text(f"❌ {msg}")

# ======================== МАГАЗИН МАШИН ========================
@dp.message(F.text == "🛒 Магазин")
async def shop_main(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇪🇺 Европейские авто", callback_data="shop_cars_europe")
    kb.button(text="🇯🇵 Азиатские авто", callback_data="shop_cars_asia")
    kb.button(text="🇺🇸 Американские авто", callback_data="shop_cars_usa")
    kb.button(text="🔧 Комплектующие", callback_data="shop_parts")
    kb.button(text="📦 Боксы (магазин)", callback_data="shop_boxes")
    kb.adjust(2)
    await message.answer("🛒 Выбери категорию:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("shop_cars_"))
async def shop_cars_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split("_")[2]
    if region == "europe":
        brands = EUROPE_CARS
    elif region == "asia":
        brands = ASIAN_CARS
    else:
        brands = US_CARS
    await state.set_state(Shop.choosing_brand)
    await state.update_data(brands=brands, region=region)
    kb = InlineKeyboardBuilder()
    for brand in brands.keys():
        kb.button(text=brand, callback_data=f"brand_{brand}")
    kb.button(text="◀️ Назад", callback_data="back_to_shop")
    kb.adjust(2)
    await callback.message.edit_text("Выбери марку:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("brand_"), Shop.choosing_brand)
async def shop_brand_models(callback: CallbackQuery, state: FSMContext):
    brand = callback.data.split("_")[1]
    data = await state.get_data()
    brands = data['brands']
    models = brands.get(brand, [])
    await state.update_data(brand=brand, models=models, model_index=0)
    await show_car_model(callback.message, state)

async def show_car_model(message: Message, state: FSMContext):
    data = await state.get_data()
    models = data['models']
    index = data['model_index']
    car = models[index]
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Купить", callback_data=f"buy_car_{index}")
    if index < len(models)-1:
        kb.button(text="▶️ Следующая", callback_data="next_model")
    if index > 0:
        kb.button(text="◀️ Предыдущая", callback_data="prev_model")
    kb.button(text="◀️ Назад к маркам", callback_data="back_to_brands")
    kb.adjust(1,2,1)
    caption = (f"🚗 *{car['name']}*\n"
               f"🏎 Л.с.: {car['hp']}\n"
               f"⚡ 0-100: {car['acc_100']}с\n"
               f"⚡ 0-200: {car['acc_200']}с\n"
               f"⚡ 0-300: {car['acc_300']}с\n"
               f"💰 Цена: {car['price']} монет")
    photo_path = os.path.join(IMAGES_PATH, car['image'])
    if os.path.exists(photo_path):
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
    else:
        await message.answer(caption + "\n⚠️ Фото отсутствует", parse_mode="Markdown", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "next_model", Shop.choosing_brand)
async def next_model(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['model_index'] += 1
    await state.update_data(data)
    await callback.message.delete()
    await show_car_model(callback.message, state)

@dp.callback_query(F.data == "prev_model", Shop.choosing_brand)
async def prev_model(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['model_index'] -= 1
    await state.update_data(data)
    await callback.message.delete()
    await show_car_model(callback.message, state)

@dp.callback_query(F.data.startswith("buy_car_"), Shop.choosing_brand)
async def buy_car(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    car = data['models'][index]
    user_id = callback.from_user.id
    user = get_user(user_id)
    if user[3] < car['price']:
        await callback.message.answer("❌ Недостаточно средств!")
        return
    add_money(user_id, -car['price'])
    update_user_car(user_id, car)
    await callback.message.delete()
    await callback.message.answer(f"✅ Ты купил {car['name']}! Она экипирована.")
    await state.clear()

@dp.callback_query(F.data == "back_to_brands")
async def back_to_brands(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    brands = data['brands']
    kb = InlineKeyboardBuilder()
    for brand in brands.keys():
        kb.button(text=brand, callback_data=f"brand_{brand}")
    kb.button(text="◀️ Назад в магазин", callback_data="back_to_shop")
    kb.adjust(2)
    await callback.message.edit_text("Выбери марку:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await shop_main(callback.message)

# ======================== МАГАЗИН ЗАПЧАСТЕЙ ========================
@dp.callback_query(F.data == "shop_parts")
async def shop_parts_categories(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Shop.parts_category)
    kb = InlineKeyboardBuilder()
    kb.button(text="🏎 Двигатели", callback_data="partcat_engine")
    kb.button(text="💨 Турбины", callback_data="partcat_turbo")
    kb.button(text="🔊 Выхлопы", callback_data="partcat_exhaust")
    kb.button(text="❄️ Радиаторы", callback_data="partcat_radiator")
    kb.button(text="💣 Закись азота", callback_data="partcat_nitro")
    kb.button(text="🛞 Амортизаторы", callback_data="partcat_suspension")
    kb.button(text="◀️ Назад", callback_data="back_to_shop")
    kb.adjust(2)
    await callback.message.edit_text("🔧 Выбери тип запчасти:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("partcat_"), Shop.parts_category)
async def shop_parts_list(callback: CallbackQuery, state: FSMContext):
    part_type = callback.data.split("_")[1]
    parts = PARTS.get(part_type, [])
    await state.update_data(part_type=part_type, parts=parts, part_index=0)
    await show_part(callback.message, state)

async def show_part(message: Message, state: FSMContext):
    data = await state.get_data()
    parts = data['parts']
    index = data['part_index']
    part = parts[index]
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Купить", callback_data=f"buy_part_{index}")
    if index < len(parts)-1:
        kb.button(text="▶️ Следующая", callback_data="next_part")
    if index > 0:
        kb.button(text="◀️ Предыдущая", callback_data="prev_part")
    kb.button(text="◀️ Назад к категориям", callback_data="back_to_parts_cat")
    kb.adjust(1,2,1)
    caption = (f"🔧 *{part['name']}*\n"
               f"+{part['hp']} л.с.\n"
               f"Разгон: {part['acc_100']}с (0-100)\n"
               f"Цена: {part['price']} монет")
    photo_path = os.path.join(IMAGES_PATH, part['image'])
    if os.path.exists(photo_path):
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
    else:
        await message.answer(caption + "\n⚠️ Фото отсутствует", parse_mode="Markdown", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "next_part", Shop.parts_category)
async def next_part(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['part_index'] += 1
    await state.update_data(data)
    await callback.message.delete()
    await show_part(callback.message, state)

@dp.callback_query(F.data == "prev_part", Shop.parts_category)
async def prev_part(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    data['part_index'] -= 1
    await state.update_data(data)
    await callback.message.delete()
    await show_part(callback.message, state)

@dp.callback_query(F.data.startswith("buy_part_"), Shop.parts_category)
async def buy_part(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    part = data['parts'][index]
    user_id = callback.from_user.id
    user = get_user(user_id)
    if user[3] < part['price']:
        await callback.message.answer("❌ Недостаточно средств!")
        return
    add_money(user_id, -part['price'])
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO inventory 
            (user_id, part_type, part_name, hp_bonus, acc_100_bonus, acc_200_bonus, acc_300_bonus, installed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)''',
            (user_id, data['part_type'], part['name'], part['hp'], part['acc_100'], part['acc_200'], part['acc_300']))
        conn.commit()
    await callback.message.answer(f"✅ Ты купил {part['name']}! Запчасть в инвентаре.")
    await callback.message.delete()
    await show_part(callback.message, state)

@dp.callback_query(F.data == "back_to_parts_cat")
async def back_to_parts_cat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Shop.parts_category)
    await shop_parts_categories(callback, state)

# ======================== ГАРАЖ И УСТАНОВКА ЗАПЧАСТЕЙ ========================
@dp.message(F.text == "🚗 Мой гараж")
async def garage(message: Message):
    user_id = message.from_user.id
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM user_cars WHERE user_id = ? ORDER BY equipped DESC", (user_id,))
        cars = c.fetchall()
        c.execute("SELECT * FROM inventory WHERE user_id = ? AND installed = 0", (user_id,))
        parts = c.fetchall()
    text = "🚗 Твои машины:\n"
    kb = InlineKeyboardBuilder()
    for car in cars:
        equipped = "✅" if car[8] == 1 else ""
        text += f"{equipped} {car[2]} (HP: {car[3]})\n"
    text += "\n🔧 Запчасти в инвентаре:\n"
    for part in parts:
        text += f"• {part[3]} (+{part[4]} л.с.)\n"
        kb.button(text=f"Установить {part[3]}", callback_data=f"install_part_{part[0]}")
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup() if parts else None)

@dp.callback_query(lambda c: c.data and c.data.startswith("install_part_"))
async def install_part(callback: CallbackQuery):
    part_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE id = ? AND user_id = ?", (part_id, user_id))
        part = c.fetchone()
        if not part:
            await callback.answer("Запчасть не найдена")
            return
        if part[8] == 1:  # installed
            await callback.answer("Уже установлена")
            return
        c.execute("SELECT id, base_hp, base_acc_100, base_acc_200, base_acc_300 FROM user_cars WHERE user_id = ? AND equipped = 1", (user_id,))
        car = c.fetchone()
        if not car:
            await callback.answer("У тебя нет экипированной машины")
            return
        car_id = car[0]
        c.execute("SELECT * FROM upgrades WHERE user_id = ? AND car_id = ? AND part_type = ?", (user_id, car_id, part[2]))
        if c.fetchone():
            await callback.answer("Уже установлена запчасть этого типа")
            return
        c.execute('''INSERT INTO upgrades 
            (user_id, car_id, part_type, part_name, hp_bonus, acc_100_bonus, acc_200_bonus, acc_300_bonus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, car_id, part[2], part[3], part[4], part[5], part[6], part[7]))
        c.execute("UPDATE inventory SET installed = 1 WHERE id = ?", (part_id,))
        c.execute("SELECT SUM(hp_bonus), SUM(acc_100_bonus), SUM(acc_200_bonus), SUM(acc_300_bonus) FROM upgrades WHERE user_id = ? AND car_id = ?",
                  (user_id, car_id))
        sums = c.fetchone()
        total_hp = car[1] + (sums[0] or 0)
        total_acc_100 = car[2] + (sums[1] or 0)
        total_acc_200 = car[3] + (sums[2] or 0)
        total_acc_300 = car[4] + (sums[3] or 0)
        c.execute("UPDATE users SET car_hp = ?, acc_100 = ?, acc_200 = ?, acc_300 = ? WHERE user_id = ?",
                  (total_hp, total_acc_100, total_acc_200, total_acc_300, user_id))
        conn.commit()
    await callback.answer("Запчасть установлена!")
    await callback.message.edit_text(f"✅ Запчасть {part[3]} установлена на твою машину!")

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

async def send_top(callback: CallbackQuery, order_by, field_name, top_name, ascending=False):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        if ascending:
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
        "top_wins": ("wins", "победам", False),
        "top_money": ("money", "деньгам", False),
        "top_followers": ("followers", "подписчикам", False),
        "top_hp": ("car_hp", "лошадиным силам", False),
        "top_acc100": ("acc_100", "разгону 0-100", True),
        "top_acc200": ("acc_200", "разгону 0-200", True),
        "top_acc300": ("acc_300", "разгону 0-300", True)
    }
    key = callback.data
    if key in mapping:
        field, name, asc = mapping[key]
        await send_top(callback, field, field, name, asc)

# ======================== ДУЭЛИ ========================
@dp.message(F.text == "🏁 Гонка")
async def race_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Вызвать на дуэль", callback_data="duel_challenge")
    kb.button(text="🏁 Быстрая гонка (с ботом)", callback_data="quick_race")
    await message.answer("Выбери режим гонки:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "quick_race")
async def quick_race(callback: CallbackQuery, state: FSMContext):
    await training_race_prepare(callback, state)

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
    if is_banned(opponent_id):
        await message.answer("Этот пользователь забанен.")
        return
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT duel_id FROM duels WHERE challenger_id = ? AND opponent_id = ? AND status = 'pending' AND expires_at > ?",
                  (user_id, opponent_id, datetime.datetime.now().isoformat()))
        if c.fetchone():
            await message.answer("Уже есть активный вызов этому игроку.")
            return
    created = datetime.datetime.now()
    expires = created + datetime.timedelta(minutes=5)
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO duels (challenger_id, opponent_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                  (user_id, opponent_id, created.isoformat(), expires.isoformat()))
        conn.commit()
        duel_id = c.lastrowid
    await state.clear()
    await message.answer(f"⚔️ Вызов отправлен! Действителен 5 минут.")
    try:
        await bot.send_message(
            opponent_id,
            f"⚔️ Вас вызвал на дуэль {message.from_user.full_name} (@{message.from_user.username})!\n"
            f"Примите вызов в течение 5 минут.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_duel_{duel_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_duel_{duel_id}")]
            ])
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение оппоненту: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("accept_duel_"))
async def accept_duel(callback: CallbackQuery, state: FSMContext):
    duel_id = int(callback.data.split("_")[2])
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT challenger_id, opponent_id, status, expires_at FROM duels WHERE duel_id = ?", (duel_id,))
        duel = c.fetchone()
        if not duel:
            await callback.answer("Дуэль не найдена")
            return
        if duel[2] != 'pending':
            await callback.answer("Этот вызов уже обработан")
            return
        if datetime.datetime.fromisoformat(duel[3]) < datetime.datetime.now():
            await callback.answer("Срок вызова истёк")
            c.execute("UPDATE duels SET status = 'expired' WHERE duel_id = ?", (duel_id,))
            conn.commit()
            return
        c.execute("UPDATE duels SET status = 'accepted' WHERE duel_id = ?", (duel_id,))
        conn.commit()
    await callback.answer()
    await callback.message.edit_text("Дуэль принята! Готовься к гонке.")
    await start_duel_race(callback.from_user.id, duel[0], state)

async def start_duel_race(player1_id, player2_id, state: FSMContext):
    for uid in [player1_id, player2_id]:
        try:
            await bot.send_message(
                uid,
                "⚔️ Дуэль начинается!\n"
                "Через 5 секунд появится кнопка старта. У вас будет 5-6 секунд, чтобы нажать.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Готов", callback_data=f"duel_ready_{player1_id}_{player2_id}")]
                ])
            )
        except:
            pass

@dp.callback_query(lambda c: c.data and c.data.startswith("duel_ready_"))
async def duel_ready(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_")
    p1 = int(parts[2])
    p2 = int(parts[3])
    user_id = callback.from_user.id
    if user_id not in (p1, p2):
        await callback.answer("Это не твоя дуэль")
        return
    await state.set_state(Duel.race_ready)
    ready_time = datetime.datetime.now()
    await state.update_data(ready_time=ready_time.timestamp(), duel_players=(p1, p2))
    await callback.message.edit_text(
        "🟢 Жми *«Старт»* через 5–6 секунд.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏎 СТАРТ", callback_data=f"duel_start_{p1}_{p2}")]
        ])
    )
    await state.set_state(Duel.race_start_wait)  # переводим в состояние ожидания старта

@dp.callback_query(lambda c: c.data and c.data.startswith("duel_start_"), Duel.race_start_wait)
async def duel_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    ready_time = data.get('ready_time')
    if not ready_time:
        await callback.message.answer("Ошибка: перезапусти гонку.")
        await state.clear()
        return
    now = datetime.datetime.now().timestamp()
    diff = now - ready_time
    user_id = callback.from_user.id
    p1, p2 = data['duel_players']
    opponent_id = p2 if user_id == p1 else p1
    if diff < 5:
        result = "фальстарт"
        win = False
    elif 5 <= diff <= 6:
        result = "идеальный старт"
        win = True
    else:
        result = "опоздание"
        win = False
    await callback.message.edit_text(f"Твой старт: {result}")
    # Обновляем статус дуэли
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE duels SET status = 'finished' WHERE (challenger_id = ? AND opponent_id = ?) OR (challenger_id = ? AND opponent_id = ?)",
                  (p1, p2, p2, p1))
        conn.commit()
    if win:
        add_win(user_id)
        add_loss(opponent_id)
        await callback.message.answer("🏆 Ты выиграл дуэль! +1 рейтинг")
        try:
            await bot.send_message(opponent_id, "💔 Ты проиграл дуэль. -1 рейтинг")
        except:
            pass
    else:
        add_loss(user_id)
        add_win(opponent_id)
        await callback.message.answer("💔 Ты проиграл дуэль. -1 рейтинг")
        try:
            await bot.send_message(opponent_id, "🏆 Ты выиграл дуэль! +1 рейтинг")
        except:
            pass
    await state.clear()

@dp.callback_query(F.data.startswith("decline_duel_"))
async def decline_duel(callback: CallbackQuery):
    duel_id = int(callback.data.split("_")[2])
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("UPDATE duels SET status = 'declined' WHERE duel_id = ?", (duel_id,))
        conn.commit()
    await callback.answer()
    await callback.message.edit_text("❌ Вызов отклонён.")

# ======================== ЕЖЕДНЕВНАЯ НАГРАДА ========================
@dp.message(F.text == "🎁 Ежедневная награда")
async def daily_reward(message: Message):
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
        if streak > 7:
            streak = 7
        reward = DAILY_REWARDS[streak]
        add_money(user_id, reward.get("money", 0))
        add_followers(user_id, reward.get("followers", 0))
        if "box" in reward:
            give_box(user_id, reward["box"])
        c.execute("UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?", (streak, today.isoformat(), user_id))
        conn.commit()
    text = f"🎁 День {streak}\n"
    if "money" in reward:
        text += f"+{reward['money']} монет\n"
    if "followers" in reward:
        text += f"+{reward['followers']} подписчиков\n"
    if "box" in reward:
        text += f"+1 бокс ({reward['box']})\n"
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
    await message.answer("Введи награду в формате: money=500 followers=100 box=light (можно комбинировать через пробел)")

@dp.message(Admin.waiting_promo_reward, F.text)
async def promo_reward_input(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data['promo_code']
    reward_text = message.text
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO promocodes (code, reward, uses_left) VALUES (?, ?, 1)",
                  (code, reward_text))
        conn.commit()
    await state.clear()
    await message.answer(f"Промокод {code} добавлен!")

@dp.message(Command("promo"))
async def use_promo(message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Используй: /promo КОД")
        return
    code = parts[1].upper()
    user_id = message.from_user.id
    with closing(sqlite3.connect(DB_NAME)) as conn:
        c = conn.cursor()
        c.execute("SELECT promo_used FROM users WHERE user_id = ?", (user_id,))
        user_data = c.fetchone()
        if user_data and user_data[0] == 1:
            await message.answer("Ты уже использовал промокод.")
            return
        c.execute("SELECT reward, uses_left FROM promocodes WHERE code = ?", (code,))
        row = c.fetchone()
        if not row or row[1] <= 0:
            await message.answer("Недействительный промокод.")
            return
        reward_str = row[0]
        parts_reward = reward_str.split()
        for part in parts_reward:
            if "=" in part:
                key, val = part.split("=")
                if key == "money":
                    add_money(user_id, int(val))
                elif key == "followers":
                    add_followers(user_id, int(val))
                elif key == "box":
                    count = int(val) if val.isdigit() else 1
                    for _ in range(count):
                        give_box(user_id, val if isinstance(val, str) else "light")
        c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        c.execute("UPDATE users SET promo_used = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    await message.answer("✅ Промокод активирован!")

# ======================== АДМИНКА: БАН / ВЫДАЧА ========================
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

@dp.message(Command("unban"))
async def unban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Admin.waiting_user_id)
    await message.answer("Введи ID пользователя для разбана:")

@dp.message(Admin.waiting_user_id, F.text)
async def process_unban(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        with closing(sqlite3.connect(DB_NAME)) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
        await message.answer(f"Пользователь {user_id} разбанен.")
    except:
        await message.answer("Неверный ID.")
    await state.clear()

@dp.message(Command("give"))
async def give_resources(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Admin.waiting_user_id)
    await message.answer("Введи ID пользователя:")

@dp.message(Admin.waiting_user_id, F.text)
async def process_give_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user=user_id)
        await state.set_state(Admin.waiting_give_money)
        await message.answer("Введи количество монет для выдачи (или 'skip'):")
    except:
        await message.answer("Неверный ID.")
        await state.clear()

@dp.message(Admin.waiting_give_money, F.text)
async def process_give_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    user_id = data['target_user']
    if text.lower() != 'skip':
        try:
            amount = int(text)
            add_money(user_id, amount)
            await message.answer(f"Выдано {amount} монет.")
        except:
            await message.answer("Неверная сумма, пропускаем.")
    await state.set_state(Admin.waiting_give_box)
    await message.answer("Введи тип бокса для выдачи (light/medium/heavy) или 'skip':")

@dp.message(Admin.waiting_give_box, F.text)
async def process_give_box(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    data = await state.get_data()
    user_id = data['target_user']
    if text in ['light', 'medium', 'heavy']:
        give_box(user_id, text)
        await message.answer(f"Выдан бокс {text}.")
    await state.clear()
    await message.answer("Выдача завершена.")

# ======================== ДОНАТ ========================
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
    text = f"*{pack['name']}*\n{pack['desc']}\nЦена: {pack['price']} руб.\n\n"
    text += "💳 Для оплаты свяжитесь с @ADMIN_USERNAME.\n"
    text += "После подтверждения админ выдаст набор."
    await callback.message.edit_text(text, parse_mode="Markdown")

# ======================== ПРОФИЛЬ ========================
@dp.message(F.text == "⚙️ Профиль")
async def profile(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    nickname, money, followers, wins, losses, rating = user[2], user[3], user[4], user[5], user[6], user[7]
    car_model = user[8] or "нет"
    car_hp = user[9] or 0
    acc_100 = user[10] or 0
    acc_200 = user[11] or 0
    acc_300 = user[12] or 0
    text = (
        f"👤 *Никнейм:* {nickname}\n"
        f"💰 *Деньги:* {money}\n"
        f"📈 *Подписчики:* {followers}\n"
        f"🏁 *Победы:* {wins}\n"
        f"💔 *Поражения:* {losses}\n"
        f"🏆 *Рейтинг:* {rating}\n"
        f"🚗 *Текущая машина:* {car_model}\n"
        f"🏎 *Л.с.:* {car_hp}\n"
        f"⚡ *0-100:* {acc_100}с\n"
        f"⚡ *0-200:* {acc_200}с\n"
        f"⚡ *0-300:* {acc_300}с\n"
    )
    await message.answer(text, parse_mode="Markdown")

# ======================== ОБРАБОТКА ОШИБОК И ОТМЕН ========================
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logging.exception("Произошла ошибка: %s", exception)
    return True

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Действие отменено.", reply_markup=main_menu_keyboard())

@dp.message()
async def handle_unknown(message: Message):
    if not get_user(message.from_user.id):
        await message.answer("Напиши /start для регистрации.")
    else:
        await message.answer("Я не понимаю эту команду. Используй кнопки меню.", reply_markup=main_menu_keyboard())

# ======================== ЗАПУСК ========================
async def main():
    init_db()
    if not os.path.exists(IMAGES_PATH):
        os.makedirs(IMAGES_PATH)
        print(f"⚠️ Папка '{IMAGES_PATH}' создана. Поместите туда изображения.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
