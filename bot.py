import logging
import sqlite3
import random
import time
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация бота
TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # Замените на ваш токен
ADMINS = [5189651311, 5887846215]  # ID администраторов
DATABASE_NAME = "racing_bot.db"

# Состояния
REGISTER_NAME, MAIN_MENU, CHOOSING_CAR, TRAINING, RACING, SHOP_MENU, GARAGE, TUNING, MARKET, EUROPEAN_MARKET, ASIAN_MARKET, AMERICAN_MARKET, PARTS_SHOP, ENGINES, TURBOS, EXHAUSTS, RADIATORS, NITROUS, SHOCK_ABSORBERS, TIRES, DUEL, WAITING_DUEL, PROFILE, INSTALL_PARTS, TOP_MENU, PROMOCODE = range(26)

# Класс для работы с базой данных
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER DEFAULT 10000,
                rating INTEGER DEFAULT 1000,
                followers INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_races INTEGER DEFAULT 0,
                current_car_id INTEGER,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_race_time TIMESTAMP,
                is_banned BOOLEAN DEFAULT FALSE,
                registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица машин
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT,
                model TEXT,
                region TEXT,
                base_hp INTEGER,
                base_acceleration_0_100 REAL,
                base_top_speed INTEGER,
                price INTEGER,
                image_name TEXT,
                category TEXT DEFAULT 'regular'
            )
        ''')
        
        # Таблица автомобилей пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                car_id INTEGER,
                bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT FALSE,
                tuning_hp INTEGER DEFAULT 0,
                tuning_acceleration REAL DEFAULT 0,
                tuning_top_speed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (car_id) REFERENCES cars(id)
            )
        ''')
        
        # Таблица запчастей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                description TEXT,
                hp_boost INTEGER,
                acceleration_boost REAL,
                top_speed_boost INTEGER,
                price INTEGER
            )
        ''')
        
        # Таблица установленных запчастей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                part_id INTEGER,
                car_id INTEGER,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (part_id) REFERENCES parts(id),
                FOREIGN KEY (car_id) REFERENCES cars(id)
            )
        ''')
        
        # Таблица гонок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS races (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                opponent_id INTEGER,
                race_type TEXT,
                result TEXT,
                distance INTEGER,
                time REAL,
                reaction_time REAL,
                earned_money INTEGER,
                earned_followers INTEGER,
                earned_rating INTEGER,
                race_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица промокодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                reward_type TEXT,
                reward_value INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица использованных промокодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS used_promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promocode_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (promocode_id) REFERENCES promocodes(id)
            )
        ''')
        
        # Таблица дуэлей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                status TEXT DEFAULT 'pending',
                distance INTEGER DEFAULT 500,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                winner_id INTEGER,
                bet_amount INTEGER DEFAULT 0,
                FOREIGN KEY (challenger_id) REFERENCES users(user_id),
                FOREIGN KEY (opponent_id) REFERENCES users(user_id),
                FOREIGN KEY (winner_id) REFERENCES users(user_id)
            )
        ''')
        
        self.conn.commit()
        self.init_data()
    
    def init_data(self):
        cursor = self.conn.cursor()
        
        # Проверяем, есть ли данные
        cursor.execute("SELECT COUNT(*) as count FROM cars")
        if cursor.fetchone()["count"] > 0:
            return
        
        # Добавляем начальные машины для обучения
        training_cars = [
            ("Mitsubishi", "Lancer X Sportback", "asian", 168, 8.5, 210, 15000, "lancer_x.jpg"),
            ("Opel", "Insignia OPC", "european", 280, 6.0, 250, 35000, "opel_insignia.jpg"),
            ("Cadillac", "CTS", "american", 321, 5.6, 240, 45000, "cadillac_cts.jpg")
        ]
        
        cursor.executemany('''
            INSERT INTO cars (brand, model, region, base_hp, base_acceleration_0_100, 
                            base_top_speed, price, image_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', training_cars)
        
        # Добавляем промокоды
        promocodes = [
            ("WELCOME2024", "money", 5000),
            ("RACINGBOT", "followers", 100),
            ("SPEED", "money", 3000),
            ("FOLLOWERS", "followers", 50),
            ("RICH", "money", 10000),
        ]
        
        cursor.executemany('''
            INSERT INTO promocodes (code, reward_type, reward_value)
            VALUES (?, ?, ?)
        ''', promocodes)
        
        self.conn.commit()
    
    # Методы пользователей
    def get_user(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    
    def create_user(self, user_id: int, username: str, first_name: str, nickname: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, nickname, balance)
                VALUES (?, ?, ?, ?, 10000)
            ''', (user_id, username, first_name, nickname))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def check_nickname(self, nickname: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE nickname = ?", (nickname,))
        return cursor.fetchone()["count"] == 0
    
    # Другие методы базы данных...
    def update_user_balance(self, user_id: int, amount: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def get_user_cars(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT uc.*, c.* 
            FROM user_cars uc
            JOIN cars c ON uc.car_id = c.id
            WHERE uc.user_id = ?
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_active_car(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT uc.*, c.* 
            FROM user_cars uc
            JOIN cars c ON uc.car_id = c.id
            WHERE uc.user_id = ? AND uc.is_active = 1
        ''', (user_id,))
        return cursor.fetchone()
    
    def buy_car(self, user_id: int, car_id: int):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_balance = cursor.fetchone()["balance"]
        
        cursor.execute("SELECT price FROM cars WHERE id = ?", (car_id,))
        car_price = cursor.fetchone()["price"]
        
        if user_balance >= car_price:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (car_price, user_id))
            
            cursor.execute('''
                INSERT INTO user_cars (user_id, car_id, is_active)
                VALUES (?, ?, 0)
            ''', (user_id, car_id))
            
            cursor.execute("SELECT COUNT(*) as count FROM user_cars WHERE user_id = ?", (user_id,))
            car_count = cursor.fetchone()["count"]
            
            if car_count == 1:
                cursor.execute('''
                    UPDATE user_cars SET is_active = 1 
                    WHERE user_id = ? AND car_id = ?
                ''', (user_id, car_id))
            
            self.conn.commit()
            return True
        return False
    
    def set_active_car(self, user_id: int, car_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE user_cars SET is_active = 0 
            WHERE user_id = ?
        ''', (user_id,))
        
        cursor.execute('''
            UPDATE user_cars SET is_active = 1 
            WHERE user_id = ? AND car_id = ?
        ''', (user_id, car_id))
        
        cursor.execute('''
            UPDATE users SET current_car_id = ? 
            WHERE user_id = ?
        ''', (car_id, user_id))
        
        self.conn.commit()
    
    def use_promocode(self, user_id: int, code: str):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM promocodes 
            WHERE code = ? AND is_active = 1
        ''', (code,))
        promocode = cursor.fetchone()
        
        if not promocode:
            return None
        
        cursor.execute('''
            SELECT * FROM used_promocodes up
            JOIN promocodes p ON up.promocode_id = p.id
            WHERE up.user_id = ? AND p.code = ?
        ''', (user_id, code))
        
        if cursor.fetchone():
            return None
        
        if promocode["reward_type"] == "money":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                         (promocode["reward_value"], user_id))
        elif promocode["reward_type"] == "followers":
            cursor.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", 
                         (promocode["reward_value"], user_id))
        
        cursor.execute('''
            INSERT INTO used_promocodes (user_id, promocode_id)
            VALUES (?, ?)
        ''', (user_id, promocode["id"]))
        
        self.conn.commit()
        return promocode["reward_type"], promocode["reward_value"]
    
    def get_top_money(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT nickname, balance 
            FROM users 
            WHERE is_banned = 0
            ORDER BY balance DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_rating(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT nickname, rating 
            FROM users 
            WHERE is_banned = 0
            ORDER BY rating DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_followers(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT nickname, followers 
            FROM users 
            WHERE is_banned = 0
            ORDER BY followers DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

# Глобальная переменная базы данных
db = Database()

# Клавиатуры
def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Гараж", callback_data="garage"),
         InlineKeyboardButton("🏎 Гонки", callback_data="racing")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton("⚙️ Тюнинг", callback_data="tuning")],
        [InlineKeyboardButton("🏆 Топы", callback_data="top"),
         InlineKeyboardButton("💰 Рынок", callback_data="market")],
        [InlineKeyboardButton("👑 Профиль", callback_data="profile"),
         InlineKeyboardButton("⚔️ Дуэль", callback_data="duel")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="promocode")]
    ])

def get_training_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Начать обучение", callback_data="start_training")],
        [InlineKeyboardButton("⏩ Пропустить", callback_data="skip_training")]
    ])

def get_car_selection_keyboard(car_index, total_cars):
    keyboard = []
    buttons = []
    
    if car_index > 0:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"car_{car_index-1}"))
    
    buttons.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"select_car_{car_index}"))
    
    if car_index < total_cars - 1:
        buttons.append(InlineKeyboardButton("Далее ▶️", callback_data=f"car_{car_index+1}"))
    
    keyboard.append(buttons)
    return InlineKeyboardMarkup(keyboard)

def get_race_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 ГОТОВ!", callback_data="ready_to_race")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])

def get_shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇪🇺 Европейский", callback_data="european_market")],
        [InlineKeyboardButton("🇯🇵 Азиатский", callback_data="asian_market")],
        [InlineKeyboardButton("🇺🇸 Американский", callback_data="american_market")],
        [InlineKeyboardButton("🛠 Запчасти", callback_data="parts_shop")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])

def get_top_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 По деньгам", callback_data="top_money")],
        [InlineKeyboardButton("⭐️ По рейтингу", callback_data="top_rating")],
        [InlineKeyboardButton("👥 По подписчикам", callback_data="top_followers")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Проверяем, зарегистрирован ли пользователь
    existing_user = db.get_user(user_id)
    
    if existing_user:
        # Пользователь уже зарегистрирован
        await update.message.reply_text(
            f"Добро пожаловать обратно, {existing_user['nickname']}!",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    
    # Новый пользователь - просим ввести ник
    await update.message.reply_text(
        "🏁 Добро пожаловать в Racing Bot!\n\n"
        "Пожалуйста, введите свой игровой ник (3-15 символов):"
    )
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nickname = update.message.text.strip()
    
    # Проверяем длину ника
    if len(nickname) < 3 or len(nickname) > 15:
        await update.message.reply_text(
            "❌ Ник должен содержать от 3 до 15 символов.\n"
            "Пожалуйста, введите другой ник:"
        )
        return REGISTER_NAME
    
    # Проверяем уникальность ника
    if not db.check_nickname(nickname):
        await update.message.reply_text(
            "❌ Этот ник уже занят.\n"
            "Пожалуйста, выберите другой ник:"
        )
        return REGISTER_NAME
    
    # Создаем пользователя
    success = db.create_user(user.id, user.username, user.first_name, nickname)
    
    if not success:
        await update.message.reply_text(
            "❌ Ошибка при регистрации. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Отправляем приветственное сообщение
    welcome_text = (
        f"🎉 Отлично, {nickname}! Ты успешно зарегистрирован!\n\n"
        f"💰 Начальный баланс: $10,000\n"
        f"⭐️ Начальный рейтинг: 1000\n\n"
        f"📚 Рекомендуем пройти обучение, чтобы освоить основы игры."
    )
    
    # Пытаемся отправить фото
    try:
        await update.message.reply_photo(
            photo=open("welcome.jpg", "rb") if os.path.exists("welcome.jpg") else None,
            caption=welcome_text,
            reply_markup=get_training_keyboard()
        )
    except:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_training_keyboard()
        )
    
    return TRAINING

async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    training_text = (
        "🎮 ОБУЧЕНИЕ\n\n"
        "1. Выберите свою первую машину из трех вариантов\n"
        "2. Участвуйте в гонках, чтобы зарабатывать деньги\n"
        "3. Покупайте новые машины и улучшайте их\n"
        "4. Соревнуйтесь с другими игроками в дуэлях\n"
        "5. Поднимайтесь в топах и станьте легендой!\n\n"
        "Давайте начнем с выбора первой машины!"
    )
    
    await query.edit_message_text(
        text=training_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🚗 Выбрать машину", callback_data="choose_first_car")
        ]])
    )
    return TRAINING

async def choose_first_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Машины для обучения
    training_cars = [
        {
            "name": "Mitsubishi Lancer X Sportback",
            "hp": 168,
            "acceleration": 8.5,
            "top_speed": 210,
            "price": 15000,
            "image": "lancer_x.jpg"
        },
        {
            "name": "Opel Insignia OPC",
            "hp": 280,
            "acceleration": 6.0,
            "top_speed": 250,
            "price": 35000,
            "image": "opel_insignia.jpg"
        },
        {
            "name": "Cadillac CTS",
            "hp": 321,
            "acceleration": 5.6,
            "top_speed": 240,
            "price": 45000,
            "image": "cadillac_cts.jpg"
        }
    ]
    
    context.user_data["training_cars"] = training_cars
    context.user_data["car_index"] = 0
    
    car = training_cars[0]
    car_text = (
        f"🚗 {car['name']}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['hp']} л.с.\n"
        f"• Разгон 0-100: {car['acceleration']} сек\n"
        f"• Макс. скорость: {car['top_speed']} км/ч\n"
        f"• Цена: ${car['price']:,}\n\n"
        f"Выберите эту машину или посмотрите другие варианты."
    )
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=get_car_selection_keyboard(0, 3)
    )
    return CHOOSING_CAR

async def show_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    car_index = int(data.split("_")[1])
    
    if "training_cars" not in context.user_data:
        return await choose_first_car(update, context)
    
    training_cars = context.user_data["training_cars"]
    context.user_data["car_index"] = car_index
    
    car = training_cars[car_index]
    car_text = (
        f"🚗 {car['name']}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['hp']} л.с.\n"
        f"• Разгон 0-100: {car['acceleration']} сек\n"
        f"• Макс. скорость: {car['top_speed']} км/ч\n"
        f"• Цена: ${car['price']:,}\n\n"
        f"Выберите эту машину или посмотрите другие варианты."
    )
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=get_car_selection_keyboard(car_index, 3)
    )
    return CHOOSING_CAR

async def select_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    car_index = context.user_data.get("car_index", 0)
    
    # Покупаем первую машину (бесплатно)
    car_id = car_index + 1  # ID 1, 2, 3
    db.buy_car(user_id, car_id)
    db.set_active_car(user_id, car_id)
    
    await query.edit_message_text(
        text="🎉 Поздравляем! Вы выбрали свою первую машину!\n\n"
             "Теперь вы готовы к своим первым гонкам!\n"
             "Попробуйте участвовать в гонках против бота, "
             "чтобы понять механику и заработать первые деньги.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏎 Начать первую гонку", callback_data="first_race")
        ]])
    )
    return RACING

async def first_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    race_info = (
        "🏁 ПЕРВАЯ ГОНКА\n\n"
        "Дистанция: 500 метров\n"
        "Соперник: Бот-новичок\n"
        "Награда за победу: $500-2000\n"
        "Подписчики: +10-50\n\n"
        "Механика гонки:\n"
        "1. Нажмите 'ГОТОВ!'\n"
        "2. Через 5 секунд начнется обратный отсчет\n"
        "3. Нажмите 'СТАРТ!' в интервале 5-6 секунд\n"
        "4. Машина проедет 500 метров\n"
        "5. Получите награду за победу!\n\n"
        "Внимание! Если нажмете раньше 5 сек - фальстарт!\n"
        "Если позже 6 сек - поздний старт!"
    )
    
    await query.edit_message_text(
        text=race_info,
        reply_markup=get_race_keyboard()
    )
    return RACING

async def ready_to_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    context.user_data["race_start_time"] = time.time()
    
    await query.edit_message_text(
        text="⏱ Ожидание старта...\n"
             "Нажмите 'СТАРТ!' через 5 секунд!\n\n"
             "Таймер: 5...",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏁 СТАРТ!", callback_data="race_start")
        ]])
    )
    
    # Запускаем обратный отсчет
    asyncio.create_task(countdown_timer(update, context))
    
    return RACING

async def countdown_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id if query else update.effective_user.id
    
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=query.message.message_id if query else update.message.message_id,
                text=f"⏱ Ожидание старта...\n"
                     f"Нажмите 'СТАРТ!' через 5 секунд!\n\n"
                     f"Таймер: {i}...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏁 СТАРТ!", callback_data="race_start")
                ]])
            )
        except:
            pass

async def race_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    start_time = context.user_data.get("race_start_time", 0)
    current_time = time.time()
    reaction_time = current_time - start_time
    
    if reaction_time < 5.0:
        await query.edit_message_text(
            text="❌ ФАЛЬСТАРТ!\n"
                 "Вы нажали слишком рано!\n"
                 "Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Повторить", callback_data="first_race")
            ]])
        )
        return RACING
    elif reaction_time > 6.0:
        await query.edit_message_text(
            text="⚠️ ПОЗДНИЙ СТАРТ!\n"
                 "Вы задержались на старте!\n"
                 "Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Повторить", callback_data="first_race")
            ]])
        )
        return RACING
    
    # Успешный старт
    await query.edit_message_text(
        text="✅ ИДЕАЛЬНЫЙ СТАРТ!\n"
             f"⏱ Реакция: {reaction_time:.2f} сек\n\n"
             "Машина разгоняется...",
        reply_markup=InlineKeyboardMarkup([[]])
    )
    
    # Имитация гонки
    await asyncio.sleep(3)
    
    # Результаты гонки
    reward_money = random.randint(500, 2000)
    reward_followers = random.randint(10, 50)
    
    # Обновляем баланс пользователя
    db.update_user_balance(user_id, reward_money)
    
    await query.edit_message_text(
        text=f"🏁 ФИНИШ!\n"
             f"💰 Выигрыш: ${reward_money}\n"
             f"👥 Подписчики: +{reward_followers}\n\n"
             f"Поздравляем с первой победой!",
        reply_markup=get_main_menu_keyboard()
    )
    
    return MAIN_MENU

async def skip_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user:
        profile_text = (
            f"👤 {user['nickname']}\n"
            f"💰 Баланс: ${user['balance']:,}\n"
            f"⭐️ Рейтинг: {user['rating']}\n"
            f"👥 Подписчики: {user['followers']:,}\n"
            f"🏆 Победы: {user['wins']} / {user['total_races']}\n\n"
            f"Выберите действие:"
        )
        
        await query.edit_message_text(
            text=profile_text,
            reply_markup=get_main_menu_keyboard()
        )
    
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user:
        profile_text = (
            f"👤 {user['nickname']}\n"
            f"💰 Баланс: ${user['balance']:,}\n"
            f"⭐️ Рейтинг: {user['rating']}\n"
            f"👥 Подписчики: {user['followers']:,}\n"
            f"🏆 Победы: {user['wins']} / {user['total_races']}\n\n"
            f"Выберите действие:"
        )
        
        await query.edit_message_text(
            text=profile_text,
            reply_markup=get_main_menu_keyboard()
        )
    
    return MAIN_MENU

async def garage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_cars = db.get_user_cars(user_id)
    
    if not user_cars:
        await query.edit_message_text(
            text="🚫 У вас пока нет машин!\n"
                 "Купите первую машину в магазине.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return GARAGE
    
    car_text = "🚗 ВАШ ГАРАЖ:\n\n"
    
    for idx, car in enumerate(user_cars, 1):
        status = "✅ АКТИВНА" if car["is_active"] else "❌ Не активна"
        car_text += (
            f"{idx}. {car['brand']} {car['model']} {status}\n"
            f"   🐎 {car['base_hp'] + car['tuning_hp']} л.с.\n"
            f"   ⚡️ {car['base_acceleration_0_100'] + car['tuning_acceleration']:.1f} сек\n"
            f"   🚀 {car['base_top_speed'] + car['tuning_top_speed']} км/ч\n\n"
        )
    
    keyboard = []
    for car in user_cars:
        if not car["is_active"]:
            keyboard.append([
                InlineKeyboardButton(
                    f"🚗 Выбрать {car['brand']} {car['model']}",
                    callback_data=f"activate_car_{car['id']}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        InlineKeyboardButton("🛒 Магазин", callback_data="shop")
    ])
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return GARAGE

async def activate_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    car_id = int(data.split("_")[2])
    
    db.set_active_car(user_id, car_id)
    
    await query.edit_message_text(
        text="✅ Машина активирована!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад в гараж", callback_data="garage"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
    )
    
    return GARAGE

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🛒 МАГАЗИН\n\n"
             "Выберите категорию:",
        reply_markup=get_shop_keyboard()
    )
    
    return SHOP_MENU

async def european_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Создаем тестовые машины
    cars = [
        {"id": 4, "brand": "Volkswagen", "model": "Golf GTI", "price": 35000, "hp": 245, "acceleration": 6.2, "top_speed": 250},
        {"id": 5, "brand": "BMW", "model": "M3", "price": 75000, "hp": 510, "acceleration": 3.9, "top_speed": 290},
        {"id": 6, "brand": "Mercedes", "model": "C63 AMG", "price": 80000, "hp": 510, "acceleration": 3.9, "top_speed": 290},
    ]
    
    context.user_data["market_cars"] = cars
    context.user_data["market_index"] = 0
    
    car = cars[0]
    car_text = (
        f"🇪🇺 ЕВРОПЕЙСКИЙ АВТОПРОМ\n\n"
        f"🚗 {car['brand']} {car['model']}\n"
        f"💰 Цена: ${car['price']:,}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['hp']} л.с.\n"
        f"• Разгон 0-100: {car['acceleration']} сек\n"
        f"• Макс. скорость: {car['top_speed']} км/ч"
    )
    
    keyboard = []
    if len(cars) > 1:
        keyboard.append([
            InlineKeyboardButton("Далее ▶️", callback_data="market_next")
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Купить", callback_data=f"buy_car_{car['id']}"),
        InlineKeyboardButton("🔙 Назад", callback_data="shop")
    ])
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return EUROPEAN_MARKET

async def market_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current_index = context.user_data.get("market_index", 0)
    cars = context.user_data.get("market_cars", [])
    
    if data == "market_next" and current_index < len(cars) - 1:
        current_index += 1
    elif data == "market_prev" and current_index > 0:
        current_index -= 1
    
    context.user_data["market_index"] = current_index
    
    car = cars[current_index]
    car_text = (
        f"🚗 {car['brand']} {car['model']}\n"
        f"💰 Цена: ${car['price']:,}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['hp']} л.с.\n"
        f"• Разгон 0-100: {car['acceleration']} сек\n"
        f"• Макс. скорость: {car['top_speed']} км/ч"
    )
    
    keyboard = []
    row = []
    
    if current_index > 0:
        row.append(InlineKeyboardButton("◀️ Назад", callback_data="market_prev"))
    
    if current_index < len(cars) - 1:
        if row:
            row.append(InlineKeyboardButton("Далее ▶️", callback_data="market_next"))
        else:
            row.append(InlineKeyboardButton("Далее ▶️", callback_data="market_next"))
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("✅ Купить", callback_data=f"buy_car_{car['id']}"),
        InlineKeyboardButton("🔙 Назад", callback_data="shop")
    ])
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return EUROPEAN_MARKET

async def buy_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    car_id = int(data.split("_")[2])
    
    # Используем тестовые ID машин
    success = db.buy_car(user_id, car_id)
    
    if success:
        await query.edit_message_text(
            text="✅ Машина успешно куплена!\n"
                 "Вы можете активировать ее в гараже.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚗 Гараж", callback_data="garage"),
                InlineKeyboardButton("🛒 Продолжить покупки", callback_data="shop")
            ]])
        )
    else:
        await query.edit_message_text(
            text="❌ Недостаточно средств!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏎 Заработать деньги", callback_data="racing"),
                InlineKeyboardButton("🔙 Назад", callback_data="shop")
            ]])
        )
    
    return SHOP_MENU

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    active_car = db.get_active_car(user_id)
    
    if not user:
        return await main_menu(update, context)
    
    profile_text = (
        f"👤 ПРОФИЛЬ ИГРОКА\n\n"
        f"📛 Ник: {user['nickname']}\n"
        f"💰 Баланс: ${user['balance']:,}\n"
        f"⭐️ Рейтинг: {user['rating']}\n"
        f"👥 Подписчики: {user['followers']:,}\n"
        f"🏆 Победы: {user['wins']} из {user['total_races']}\n"
        f"📈 Уровень: {user['level']}\n"
        f"🎮 Опыт: {user['experience']}/1000\n"
    )
    
    if active_car:
        profile_text += (
            f"\n🚗 Текущая машина:\n"
            f"• {active_car['brand']} {active_car['model']}\n"
            f"• {active_car['base_hp'] + active_car['tuning_hp']} л.с.\n"
            f"• {active_car['base_acceleration_0_100'] + active_car['tuning_acceleration']:.1f} сек до 100 км/ч\n"
            f"• {active_car['base_top_speed'] + active_car['tuning_top_speed']} км/ч макс. скорость"
        )
    
    await query.edit_message_text(
        text=profile_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
    )
    
    return PROFILE

async def racing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    race_text = (
        "🏎 ГОНКИ\n\n"
        "Выберите тип гонки:\n\n"
        "1. 🎮 Тренировка (против бота)\n"
        "   • Награда: $500-2000\n"
        "   • Подписчики: +10-50\n"
        "   • Без риска\n\n"
        "2. ⚔️ Дуэль (против игрока)\n"
        "   • Награда: $1000-5000\n"
        "   • Подписчики: +50-200\n"
        "   • Рейтинг: +-20\n\n"
        "3. 🏆 Турнир (скоро)\n"
        "   • Крупные награды\n"
        "   • Уникальные машины\n"
        "   • Повышение рейтинга"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Тренировка", callback_data="training_race")],
        [InlineKeyboardButton("⚔️ Дуэль", callback_data="duel")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=race_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return RACING

async def training_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    race_info = (
        "🎮 ТРЕНИРОВОЧНАЯ ГОНКА\n\n"
        "Дистанция: 500 метров\n"
        "Соперник: Бот-новичок\n"
        "Награда за победу: $500-2000\n"
        "Подписчики: +10-50\n\n"
        "Механика гонки:\n"
        "1. Нажмите 'ГОТОВ!'\n"
        "2. Через 5 секунд начнется обратный отсчет\n"
        "3. Нажмите 'СТАРТ!' в интервале 5-6 секунд\n"
        "4. Машина проедет 500 метров\n"
        "5. Получите награду за победу!\n\n"
        "Внимание! Если нажмете раньше 5 сек - фальстарт!\n"
        "Если позже 6 сек - поздний старт!"
    )
    
    await query.edit_message_text(
        text=race_info,
        reply_markup=get_race_keyboard()
    )
    
    return RACING

async def top_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🏆 ТОП ИГРОКОВ\n\n"
             "Выберите категорию:",
        reply_markup=get_top_keyboard()
    )
    
    return TOP_MENU

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "top_money":
        top_name = "💰 ТОП ПО ДЕНЬГАМ"
        top_data = db.get_top_money(10)
    elif data == "top_rating":
        top_name = "⭐️ ТОП ПО РЕЙТИНГУ"
        top_data = db.get_top_rating(10)
    elif data == "top_followers":
        top_name = "👥 ТОП ПО ПОДПИСЧИКАМ"
        top_data = db.get_top_followers(10)
    else:
        return await top_menu(update, context)
    
    if not top_data:
        await query.edit_message_text(
            text=f"🚫 {top_name} пока пуст.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="top")
            ]])
        )
        return TOP_MENU
    
    top_text = f"{top_name}\n\n"
    
    for idx, item in enumerate(top_data, 1):
        value = item.get('balance', item.get('rating', item.get('followers', 0)))
        top_text += f"{idx}. {item['nickname']} - {value:,}\n"
    
    keyboard = [
        [InlineKeyboardButton("🏆 Другие топы", callback_data="top")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=top_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return TOP_MENU

async def promocode_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🎁 АКТИВАЦИЯ ПРОМОКОДА\n\n"
             "Введите промокод:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
        ]])
    )
    
    return PROMOCODE

async def activate_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    result = db.use_promocode(user_id, code)
    
    if result:
        reward_type, value = result
        reward_text = {
            "money": f"💰 {value:,} денег",
            "followers": f"👥 {value:,} подписчиков"
        }.get(reward_type, "награда")
        
        await update.message.reply_text(
            f"✅ Промокод активирован!\n"
            f"Вы получили: {reward_text}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Неверный промокод или он уже использован.",
            reply_markup=get_main_menu_keyboard()
        )
    
    return MAIN_MENU

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="💰 РЫНОК\n\n"
             "Выберите категорию:",
        reply_markup=get_shop_keyboard()
    )
    
    return MARKET

async def tuning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    active_car = db.get_active_car(user_id)
    
    if not active_car:
        await query.edit_message_text(
            text="🚫 У вас нет активной машины!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚗 Гараж", callback_data="garage"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return TUNING
    
    car_text = (
        f"⚙️ ТЮНИНГ: {active_car['brand']} {active_car['model']}\n\n"
        f"📊 Текущие характеристики:\n"
        f"• Лошадиные силы: {active_car['base_hp']} + {active_car['tuning_hp']} = "
        f"{active_car['base_hp'] + active_car['tuning_hp']} л.с.\n"
        f"• Разгон 0-100: {active_car['base_acceleration_0_100']} + {active_car['tuning_acceleration']:.1f} = "
        f"{active_car['base_acceleration_0_100'] + active_car['tuning_acceleration']:.1f} сек\n"
        f"• Макс. скорость: {active_car['base_top_speed']} + {active_car['tuning_top_speed']} = "
        f"{active_car['base_top_speed'] + active_car['tuning_top_speed']} км/ч\n\n"
        f"В разработке... скоро появится!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return TUNING

async def duel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duel_text = "⚔️ ДУЭЛИ\n\n" \
                "В разработке... скоро появится!\n\n" \
                "Скоро вы сможете вызывать других игроков на дуэли " \
                "и соревноваться за рейтинг!"
    
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=duel_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return DUEL

# Админ команды
async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /ban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        cursor = db.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Пользователь {target_id} забанен.")
    except:
        await update.message.reply_text("❌ Ошибка при бане пользователя.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /unban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        cursor = db.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен.")
    except:
        await update.message.reply_text("❌ Ошибка при разбане пользователя.")

async def admin_add_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /addmoney <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        
        db.update_user_balance(target_id, amount)
        
        await update.message.reply_text(f"✅ Пользователю {target_id} добавлено ${amount:,}.")
    except:
        await update.message.reply_text("❌ Ошибка при добавлении денег.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]
    
    stats_text = (
        "📊 СТАТИСТИКА БОТА\n\n"
        f"👥 Всего пользователей: {total_users:,}"
    )
    
    await update.message.reply_text(stats_text)

# Обработка неизвестных команд
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Неизвестная команда. Используйте /start для начала игры."
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операция отменена. Используйте /start для начала игры."
    )
    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", admin_ban))
    application.add_handler(CommandHandler("unban", admin_unban))
    application.add_handler(CommandHandler("addmoney", admin_add_money))
    application.add_handler(CommandHandler("stats", admin_stats))
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(garage, pattern="^garage$"),
                CallbackQueryHandler(racing, pattern="^racing$"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
                CallbackQueryHandler(tuning, pattern="^tuning$"),
                CallbackQueryHandler(top_menu, pattern="^top$"),
                CallbackQueryHandler(market_menu, pattern="^market$"),
                CallbackQueryHandler(profile, pattern="^profile$"),
                CallbackQueryHandler(duel_menu, pattern="^duel$"),
                CallbackQueryHandler(promocode_menu, pattern="^promocode$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            TRAINING: [
                CallbackQueryHandler(start_training, pattern="^start_training$"),
                CallbackQueryHandler(skip_training, pattern="^skip_training$"),
                CallbackQueryHandler(choose_first_car, pattern="^choose_first_car$"),
            ],
            CHOOSING_CAR: [
                CallbackQueryHandler(show_car, pattern=r"^car_\d+$"),
                CallbackQueryHandler(select_car, pattern=r"^select_car_\d+$"),
            ],
            RACING: [
                CallbackQueryHandler(first_race, pattern="^first_race$"),
                CallbackQueryHandler(training_race, pattern="^training_race$"),
                CallbackQueryHandler(ready_to_race, pattern="^ready_to_race$"),
                CallbackQueryHandler(race_start, pattern="^race_start$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            SHOP_MENU: [
                CallbackQueryHandler(european_market, pattern="^european_market$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            MARKET: [
                CallbackQueryHandler(european_market, pattern="^european_market$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            EUROPEAN_MARKET: [
                CallbackQueryHandler(market_navigation, pattern="^market_"),
                CallbackQueryHandler(buy_car, pattern=r"^buy_car_\d+$"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            GARAGE: [
                CallbackQueryHandler(activate_car, pattern=r"^activate_car_\d+$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
            ],
            TUNING: [
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            DUEL: [
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            PROFILE: [
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            TOP_MENU: [
                CallbackQueryHandler(show_top, pattern="^top_"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            PROMOCODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, activate_promocode),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Запуск бота
    print("=" * 60)
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMINS}")
    print("🎁 Промокоды: WELCOME2024, RACINGBOT, SPEED, FOLLOWERS, RICH")
    print("⚔️ Дуэли: В разработке")
    print("💰 Экономика: Улучшенная")
    print("=" * 60)
    
    application.run_polling()

if __name__ == '__main__':
    main()
