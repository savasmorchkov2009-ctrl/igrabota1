#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sqlite3
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # Замените на ваш токен
ADMIN_IDS = [5189651311, 5887846215]  # ID администраторов
PROMO_CODE = "RACING2024"  # Промокод (можно менять)
PROMO_BONUS = 10000  # Бонус за промокод

# Настройки игры
INITIAL_BALANCE = 5000
START_REACTION_MIN = 5.0  # Минимальное время реакции (сек)
START_REACTION_MAX = 6.0  # Максимальное время реакции (сек)
RACE_DISTANCE = 500  # Дистанция гонки в метрах
RACE_REWARD_WIN = 1000  # Награда за победу
RACE_REWARD_LOSS = 200  # Награда за поражение
RATING_WIN = 10  # Рейтинг за победу
RATING_LOSS = 5  # Рейтинг за поражение

# Состояния для ConversationHandler
CHOOSING_CAR, MAIN_MENU, BUYING_CAR, SHOP_MENU, TUNING_MENU, RACE_MENU, DUEL_MENU = range(7)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== МОДЕЛИ ДАННЫХ ====================
@dataclass
class Car:
    id: int
    name: str
    brand: str
    country: str
    price: int
    horsepower: int
    acceleration_0_100: float
    top_speed: int
    photo_file_id: str = ""
    description: str = ""
    
@dataclass
class Player:
    user_id: int
    username: str
    nickname: str
    balance: int
    rating: int
    followers: int
    wins: int
    losses: int
    current_car_id: int
    created_at: str
    
@dataclass
class Part:
    id: int
    name: str
    type: str  # engine, turbo, tires, exhaust, radiator, nos, suspension
    price: int
    horsepower_boost: int
    acceleration_boost: float
    description: str

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self, db_name="racing_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        # Таблица игроков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                balance INTEGER DEFAULT 5000,
                rating INTEGER DEFAULT 1000,
                followers INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                current_car_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tutorial_completed BOOLEAN DEFAULT FALSE,
                promo_used BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица машин игрока
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                car_id INTEGER,
                horsepower INTEGER,
                acceleration_0_100 REAL,
                FOREIGN KEY (user_id) REFERENCES players (user_id)
            )
        ''')
        
        # Таблица запчастей игрока
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                part_id INTEGER,
                installed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES players (user_id)
            )
        ''')
        
        # Таблица доступных машин
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                brand TEXT,
                country TEXT,
                price INTEGER,
                horsepower INTEGER,
                acceleration_0_100 REAL,
                top_speed INTEGER,
                photo_file_id TEXT,
                description TEXT
            )
        ''')
        
        # Таблица запчастей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                price INTEGER,
                horsepower_boost INTEGER,
                acceleration_boost REAL,
                description TEXT
            )
        ''')
        
        # Таблица дуэлей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                winner_id INTEGER,
                bet_amount INTEGER,
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        self.populate_default_data()
    
    def populate_default_data(self):
        # Добавляем начальные машины для обучения
        starter_cars = [
            (1, "Lancer X Sportback", "Mitsubishi", "Japan", 0, 240, 6.1, 240, "", "Надежный спортсмен с отличной управляемостью"),
            (2, "Opel Insignia OPC", "Opel", "Germany", 0, 325, 5.9, 250, "", "Немецкая мощь и комфорт"),
            (3, "Cadillac CTS", "Cadillac", "USA", 0, 420, 5.2, 270, "", "Американская роскошь и сила")
        ]
        
        self.cursor.executemany('''
            INSERT OR IGNORE INTO cars (id, name, brand, country, price, horsepower, acceleration_0_100, top_speed, photo_file_id, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', starter_cars)
        
        # Добавляем европейские машины
        european_cars = [
            ("Volkswagen Golf", "Volkswagen", "Germany", 15000, 150, 8.2, 210, "", "Классика немецкого автопрома"),
            ("Volkswagen Passat", "Volkswagen", "Germany", 20000, 190, 7.8, 230, "", "Просторный и комфортабельный"),
            ("Mercedes-Benz C-Class", "Mercedes", "Germany", 35000, 255, 6.0, 250, "", "Роскошь и технологии"),
            ("Mercedes-Benz E-Class", "Mercedes", "Germany", 45000, 299, 5.7, 250, "", "Бизнес-класс высшего уровня"),
            ("BMW 5 Series", "BMW", "Germany", 40000, 249, 6.1, 250, "", "Водительское удовольствие"),
            ("BMW X3", "BMW", "Germany", 42000, 184, 8.3, 210, "", "Спортивный кроссовер"),
            ("Audi A6", "Audi", "Germany", 38000, 245, 6.1, 250, "", "Стиль и инновации"),
            ("Audi Q7", "Audi", "Germany", 55000, 249, 6.9, 234, "", "Премиальный внедорожник"),
            ("Porsche Panamera", "Porsche", "Germany", 85000, 330, 5.4, 270, "", "Спортивный седан"),
            ("Porsche Macan", "Porsche", "Germany", 65000, 265, 6.1, 254, "", "Компактный кроссовер"),
            ("Ferrari Roma", "Ferrari", "Italy", 250000, 620, 3.4, 320, "", "Итальянская элегантность"),
            ("Ferrari F8 Tributo", "Ferrari", "Italy", 300000, 720, 2.9, 340, "", "Трибьут технологиям"),
            ("Lamborghini Huracán", "Lamborghini", "Italy", 280000, 640, 2.9, 325, "", "Итальянский бык"),
            ("Lamborghini Aventador", "Lamborghini", "Italy", 450000, 770, 2.9, 350, "", "Флагманский суперкар"),
            ("Bugatti Chiron", "Bugatti", "France", 3000000, 1500, 2.4, 420, "", "Гиперкар легенда")
        ]
        
        for car in european_cars:
            self.cursor.execute('''
                INSERT OR IGNORE INTO cars (name, brand, country, price, horsepower, acceleration_0_100, top_speed, photo_file_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', car)
        
        # Добавляем азиатские машины
        asian_cars = [
            ("Toyota Supra", "Toyota", "Japan", 55000, 340, 4.1, 250, "", "Легенда возвращается"),
            ("Nissan Skyline GT-R R34", "Nissan", "Japan", 120000, 280, 4.9, 250, "", "Культовый японец"),
            ("Honda NSX", "Honda", "Japan", 160000, 581, 2.9, 308, "", "Японский суперкар"),
            ("Mazda RX-7", "Mazda", "Japan", 45000, 280, 5.3, 250, "", "Роторный легенда"),
            ("Subaru Impreza WRX STI", "Subaru", "Japan", 40000, 310, 5.2, 250, "", "Раллийный чемпион"),
            ("Mitsubishi Lancer Evolution", "Mitsubishi", "Japan", 35000, 303, 4.8, 250, "", "Легендарный Эволюшн"),
            ("Lexus LC", "Lexus", "Japan", 92000, 471, 4.4, 270, "", "Роскошный гран-туризмо"),
            ("Hyundai Genesis Coupe", "Hyundai", "South Korea", 30000, 350, 5.3, 240, "", "Корейский спортсмен"),
            ("Kia Stinger", "Kia", "South Korea", 35000, 370, 4.7, 270, "", "Спортивный лифтбек")
        ]
        
        for car in asian_cars:
            self.cursor.execute('''
                INSERT OR IGNORE INTO cars (name, brand, country, price, horsepower, acceleration_0_100, top_speed, photo_file_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', car)
        
        # Добавляем американские машины
        american_cars = [
            ("Ford Mustang GT", "Ford", "USA", 35000, 450, 4.3, 250, "", "Американская икона"),
            ("Chevrolet Corvette Stingray", "Chevrolet", "USA", 65000, 495, 2.9, 312, "", "Народный суперкар"),
            ("Dodge Challenger Hellcat", "Dodge", "USA", 70000, 717, 3.6, 315, "", "Американский мускул"),
            ("Tesla Model S Plaid", "Tesla", "USA", 130000, 1020, 2.1, 322, "", "Электрическая революция"),
            ("Jeep Wrangler", "Jeep", "USA", 35000, 285, 7.5, 180, "", "Внедорожная легенда"),
            ("Cadillac Escalade", "Cadillac", "USA", 85000, 420, 5.8, 180, "", "Премиальный внедорожник")
        ]
        
        for car in american_cars:
            self.cursor.execute('''
                INSERT OR IGNORE INTO cars (name, brand, country, price, horsepower, acceleration_0_100, top_speed, photo_file_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', car)
        
        # Добавляем запчасти
        parts = [
            # Двигатели
            ("Volkswagen EA888 2.0 TSI", "engine", 5000, 50, -0.3, "Мощный турбированный движок"),
            ("Toyota 2JZ-GTE", "engine", 15000, 150, -0.8, "Легендарный японский двигатель"),
            ("Chevrolet LS V8", "engine", 12000, 120, -0.5, "Американский V8"),
            
            # Турбины
            ("Garrett GT35", "turbo", 3000, 40, -0.2, "Высокопроизводительная турбина"),
            ("BorgWarner EFR 8374", "turbo", 4500, 60, -0.3, "Современная турбина с низкой инерцией"),
            
            # Покрышки
            ("Michelin Pilot Sport 4S", "tires", 1500, 0, -0.1, "Спортивные покрышки для лучшего сцепления"),
            ("Pirelli P Zero", "tires", 2000, 0, -0.15, "Высокопроизводительные летние шины"),
            
            # Выхлопы
            ("Akrapovič Evolution", "exhaust", 2500, 15, -0.05, "Легковесная титановая система"),
            ("Borla Atak", "exhaust", 1800, 10, -0.03, "Агрессивный звук выхлопа"),
            
            # Радиаторы
            ("Mishimoto M-Line", "radiator", 1200, 0, 0, "Улучшенное охлаждение двигателя"),
            
            # Закись азота
            ("NOS Sniper Kit", "nos", 8000, 100, -0.4, "Система закиси азота для кратковременного ускорения"),
            
            # Подвески
            ("KW Variant 3", "suspension", 3500, 0, -0.1, "Регулируемая спортивная подвеска")
        ]
        
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts (name, type, price, horsepower_boost, acceleration_boost, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', parts)
        
        self.conn.commit()
    
    def get_player(self, user_id: int) -> Optional[Player]:
        self.cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        row = self.cursor.fetchone()
        if row:
            return Player(
                user_id=row[0],
                username=row[1],
                nickname=row[2],
                balance=row[3],
                rating=row[4],
                followers=row[5],
                wins=row[6],
                losses=row[7],
                current_car_id=row[8],
                created_at=row[9]
            )
        return None
    
    def create_player(self, user_id: int, username: str, nickname: str):
        self.cursor.execute('''
            INSERT INTO players (user_id, username, nickname, balance, current_car_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, nickname, INITIAL_BALANCE, 1))
        self.conn.commit()
    
    def get_car(self, car_id: int) -> Optional[Car]:
        self.cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
        row = self.cursor.fetchone()
        if row:
            return Car(
                id=row[0],
                name=row[1],
                brand=row[2],
                country=row[3],
                price=row[4],
                horsepower=row[5],
                acceleration_0_100=row[6],
                top_speed=row[7],
                photo_file_id=row[8],
                description=row[9]
            )
        return None
    
    def get_cars_by_country(self, country: str) -> List[Car]:
        self.cursor.execute('SELECT * FROM cars WHERE country = ? AND price > 0 ORDER BY price', (country,))
        rows = self.cursor.fetchall()
        return [Car(*row) for row in rows]
    
    def update_player_car(self, user_id: int, car_id: int):
        self.cursor.execute('UPDATE players SET current_car_id = ? WHERE user_id = ?', (car_id, user_id))
        self.conn.commit()
    
    def update_player_balance(self, user_id: int, amount: int):
        self.cursor.execute('UPDATE players SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def get_top_players_by_wins(self, limit=10):
        self.cursor.execute('''
            SELECT nickname, username, wins, rating, followers 
            FROM players 
            ORDER BY wins DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_players_by_money(self, limit=10):
        self.cursor.execute('''
            SELECT nickname, username, balance, rating, followers 
            FROM players 
            ORDER BY balance DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_players_by_rating(self, limit=10):
        self.cursor.execute('''
            SELECT nickname, username, rating, wins, followers 
            FROM players 
            ORDER BY rating DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
db = Database()
waiting_for_duel = {}  # user_id: {'message_id': int, 'time': datetime}

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🏎️ Гонка с ботом", callback_data="race_bot")],
        [InlineKeyboardButton("⚔️ Дуэль с игроком", callback_data="duel_search")],
        [InlineKeyboardButton("🏪 Автосалон", callback_data="car_shop")],
        [InlineKeyboardButton("🔧 Магазин запчастей", callback_data="parts_shop")],
        [InlineKeyboardButton("👤 Мой гараж", callback_data="my_garage")],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="top_players")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="use_promo")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_car_choice_keyboard(car_index=0, total=3):
    keyboard = []
    if car_index > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"prev_car_{car_index}")])
    
    row = []
    row.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"select_car_{car_index}"))
    
    if car_index < total - 1:
        row.append(InlineKeyboardButton("Далее ➡️", callback_data=f"next_car_{car_index}"))
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def get_car_market_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇪🇺 Европейские", callback_data="market_europe")],
        [InlineKeyboardButton("🇯🇵 Азиатские", callback_data="market_asia")],
        [InlineKeyboardButton("🇺🇸 Американские", callback_data="market_usa")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_parts_shop_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚗 Двигатели", callback_data="parts_engine")],
        [InlineKeyboardButton("🌀 Турбины", callback_data="parts_turbo")],
        [InlineKeyboardButton("🛞 Покрышки", callback_data="parts_tires")],
        [InlineKeyboardButton("💨 Выхлопы", callback_data="parts_exhaust")],
        [InlineKeyboardButton("🔄 Подвеска", callback_data="parts_suspension")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = db.get_player(user.id)
    
    if not player:
        await update.message.reply_text(
            "🏎️ *Добро пожаловать в Racing Bot!*\n\n"
            "Введите ваш игровой никнейм (только буквы и цифры, 3-15 символов):",
            parse_mode=ParseMode.MARKDOWN
        )
        return CHOOSING_CAR
    
    if not player.tutorial_completed:
        await show_tutorial(update, context)
        return CHOOSING_CAR
    
    await show_main_menu(update, context)
    return MAIN_MENU

async def process_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text.strip()
    
    if not (3 <= len(nickname) <= 15) or not nickname.isalnum():
        await update.message.reply_text(
            "❌ Никнейм должен содержать только буквы и цифры, от 3 до 15 символов.\n"
            "Попробуйте еще раз:"
        )
        return CHOOSING_CAR
    
    db.create_player(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        nickname=nickname
    )
    
    await show_tutorial(update, context)
    return CHOOSING_CAR

async def show_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Отправляем приветственное фото (замените на ваше)
    try:
        await context.bot.send_photo(
            chat_id=user.id,
            photo="https://via.placeholder.com/400x200/0000FF/808080?text=Racing+Bot+Welcome",
            caption=(
                "🏎️ *Добро пожаловать в мир Racing Bot!*\n\n"
                "Здесь ты сможешь:\n"
                "• Выбрать и купить крутые машины\n"
                "• Тюнинговать их для лучших характеристик\n"
                "• Участвовать в гонках и дуэлях\n"
                "• Зарабатывать деньги и подписчиков\n"
                "• Подниматься в топах лучших гонщиков!\n\n"
                "Давай начнем с выбора твоей первой машины!"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await update.message.reply_text(
            "🏎️ *Добро пожаловать в мир Racing Bot!*\n\n"
            "Давай начнем с выбора твоей первой машины!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    context.user_data['car_index'] = 0
    await show_car_selection(update, context)

async def show_car_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    car_index = context.user_data.get('car_index', 0)
    cars = [1, 2, 3]  # ID начальных машин
    
    if car_index >= len(cars):
        car_index = 0
        context.user_data['car_index'] = 0
    
    car_id = cars[car_index]
    car = db.get_car(car_id)
    
    if car:
        # Здесь вы можете заменить фото на свои
        # Для примера используем заглушки
        photo_urls = [
            "https://via.placeholder.com/400x200/FF0000/FFFFFF?text=Lancer+X+Sportback",
            "https://via.placeholder.com/400x200/0000FF/FFFFFF?text=Opel+Insignia+OPC",
            "https://via.placeholder.com/400x200/008000/FFFFFF?text=Cadillac+CTS"
        ]
        
        message_text = (
            f"🚗 *{car.name}*\n\n"
            f"*Страна:* {car.country}\n"
            f"*Мощность:* {car.horsepower} л.с.\n"
            f"*Разгон 0-100:* {car.acceleration_0_100} сек\n"
            f"*Макс. скорость:* {car.top_speed} км/ч\n\n"
            f"{car.description}"
        )
        
        keyboard = get_car_choice_keyboard(car_index, len(cars))
        
        if update.callback_query:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(media=photo_urls[car_index], caption=message_text, parse_mode=ParseMode.MARKDOWN),
                reply_markup=keyboard
            )
        else:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=photo_urls[car_index],
                caption=message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )

async def select_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    car_index = int(query.data.split('_')[-1])
    cars = [1, 2, 3]
    
    if car_index < len(cars):
        selected_car_id = cars[car_index]
        db.update_player_car(user.id, selected_car_id)
        
        await query.edit_message_caption(
            caption="✅ *Отличный выбор!*\n\nТвоя первая машина готова к гонкам!\n\n"
                   "Теперь давай пройдем обучение, чтобы понять как устроены гонки.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await asyncio.sleep(2)
        await show_training_race(update, context)

async def show_training_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    
    tutorial_text = (
        "🏁 *Обучение: Как проходят гонки*\n\n"
        "1. Ты видишь информацию о гонке\n"
        "2. Нажимаешь кнопку 'Готов'\n"
        "3. Через 5-6 секунд нажимаешь 'Старт'\n"
        "4. Если нажмешь раньше - фальстарт\n"
        "5. Если позже - поздний старт\n"
        "6. Правильный старт = победа!\n\n"
        "В настоящих гонках ты будешь соревноваться с другими игроками."
    )
    
    keyboard = [[InlineKeyboardButton("✅ Понятно, начать тренировку", callback_data="start_training")]]
    
    if query:
        await query.edit_message_caption(
            caption=tutorial_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text=tutorial_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def start_training_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = db.get_player(user.id)
    car = db.get_car(player.current_car_id) if player else None
    
    race_info = (
        f"🏁 *Тренировочная гонка*\n\n"
        f"*Дистанция:* 500 метров\n"
        f"*Твоя машина:* {car.name if car else 'Неизвестно'}\n"
        f"*Мощность:* {car.horsepower if car else 0} л.с.\n\n"
        f"Нажми 'Готов' когда будешь готов стартовать!"
    )
    
    keyboard = [[InlineKeyboardButton("🎮 Готов!", callback_data="training_ready")]]
    
    await query.edit_message_caption(
        caption=race_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def training_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Случайное время реакции между 5 и 6 секундами
    reaction_time = random.uniform(START_REACTION_MIN, START_REACTION_MAX)
    context.user_data['reaction_time'] = reaction_time
    context.user_data['race_start_time'] = datetime.now().timestamp()
    
    await query.edit_message_caption(
        caption="⏱️ *Жди сигнал...*\n\nНажми 'Старт!' как только загорится зеленый!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚦 Старт!", callback_data="training_start")]])
    )
    
    # Запускаем отсчет
    context.user_data['countdown_task'] = asyncio.create_task(
        training_countdown(query.message.chat_id, query.message.message_id, context, reaction_time)
    )

async def training_countdown(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE, reaction_time: float):
    await asyncio.sleep(reaction_time)
    
    try:
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption="✅ *СЕЙЧАС!* Нажимай Старт!",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

async def training_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    
    # Отменяем отсчет если он еще идет
    if 'countdown_task' in context.user_data:
        context.user_data['countdown_task'].cancel()
    
    race_start_time = context.user_data.get('race_start_time', 0)
    reaction_time = context.user_data.get('reaction_time', 5.5)
    current_time = datetime.now().timestamp()
    player_reaction = current_time - race_start_time
    
    # Определяем результат
    time_diff = abs(player_reaction - reaction_time)
    
    if player_reaction < reaction_time - 0.5:
        result = "🚫 *Фальстарт!* Ты стартовал слишком рано!"
        success = False
    elif player_reaction > reaction_time + 0.5:
        result = "🐌 *Поздний старт!* Ты опоздал!"
        success = False
    else:
        result = "✅ *Идеальный старт!* Поздравляем!"
        success = True
    
    # Симуляция гонки
    player = db.get_player(user.id)
    car = db.get_car(player.current_car_id) if player else None
    
    if car and success:
        # Рассчитываем время заезда на основе характеристик машины
        race_time = (RACE_DISTANCE / 1000) / (car.top_speed / 3.6) * random.uniform(0.9, 1.1)
        race_time = round(race_time, 2)
        
        await query.edit_message_caption(
            caption=f"{result}\n\n🏁 *Гонка началась!*\nМашина разгоняется...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await asyncio.sleep(2)
        
        # Обновляем баланс игрока
        db.update_player_balance(user.id, 1000)
        
        await query.edit_message_caption(
            caption=(
                f"{result}\n\n"
                f"🏁 *Финиш!*\n"
                f"*Время заезда:* {race_time} секунд\n"
                f"*Дистанция:* 500 метров\n"
                f"*Награда:* +1,000 💰\n\n"
                f"🎉 *Обучение пройдено!* Теперь ты готов к настоящим гонкам!"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        
        # Отмечаем обучение как пройденное
        db.cursor.execute('UPDATE players SET tutorial_completed = TRUE WHERE user_id = ?', (user.id,))
        db.conn.commit()
    else:
        await query.edit_message_caption(
            caption=f"{result}\n\nПопробуй еще раз!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Попробовать снова", callback_data="start_training")]])
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    
    player = db.get_player(user.id)
    if not player:
        await start(update, context)
        return
    
    car = db.get_car(player.current_car_id) if player.current_car_id else None
    
    menu_text = (
        f"🏎️ *Главное меню*\n\n"
        f"👤 *Игрок:* {player.nickname}\n"
        f"💰 *Баланс:* {player.balance:,}\n"
        f"⭐ *Рейтинг:* {player.rating}\n"
        f"👥 *Подписчики:* {player.followers}\n"
        f"🏆 *Побед/Поражений:* {player.wins}/{player.losses}\n\n"
        f"🚗 *Текущая машина:* {car.name if car else 'Нет машины'}\n"
        f"⚡ *Мощность:* {car.horsepower if car else 0} л.с.\n"
    )
    
    keyboard = get_main_menu_keyboard()
    
    if query:
        await query.edit_message_caption(
            caption=menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text=menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

async def car_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    shop_text = (
        "🏪 *Автосалон*\n\n"
        "Выберите регион для просмотра машин:\n\n"
        "🇪🇺 *Европейские* - премиум и спорт\n"
        "🇯🇵 *Азиатские* - надежность и тюнинг\n"
        "🇺🇸 *Американские* - мощность и масштаб"
    )
    
    keyboard = get_car_market_keyboard()
    
    await query.edit_message_caption(
        caption=shop_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def show_market_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    market_type = query.data.split('_')[-1]
    countries = {
        'europe': 'Germany',
        'asia': 'Japan',
        'usa': 'USA'
    }
    
    country = countries.get(market_type, 'Germany')
    cars = db.get_cars_by_country(country)
    
    if not cars:
        await query.edit_message_caption(
            caption="❌ Машины этого региона временно отсутствуют",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="car_shop")]])
        )
        return
    
    context.user_data['market_cars'] = [car.id for car in cars]
    context.user_data['market_index'] = 0
    context.user_data['market_type'] = market_type
    
    await show_market_car(update, context, 0)

async def show_market_car(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    query = update.callback_query
    car_ids = context.user_data.get('market_cars', [])
    
    if not car_ids or index >= len(car_ids):
        return
    
    car_id = car_ids[index]
    car = db.get_car(car_id)
    user = update.effective_user
    player = db.get_player(user.id)
    
    if not car:
        return
    
    can_buy = player.balance >= car.price if player else False
    
    car_text = (
        f"🚗 *{car.name}*\n"
        f"*Марка:* {car.brand}\n"
        f"*Страна:* {car.country}\n"
        f"*Мощность:* {car.horsepower} л.с.\n"
        f"*Разгон 0-100:* {car.acceleration_0_100} сек\n"
        f"*Макс. скорость:* {car.top_speed} км/ч\n"
        f"*Цена:* {car.price:,} 💰\n\n"
        f"{car.description}\n\n"
    )
    
    if can_buy:
        car_text += "✅ У тебя достаточно денег для покупки!"
    else:
        car_text += f"❌ Недостаточно денег. Нужно ещё {car.price - player.balance:,} 💰"
    
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"market_prev_{index}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{index + 1}/{len(car_ids)}", callback_data="noop"))
    
    if index < len(car_ids) - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"market_next_{index}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка покупки
    if can_buy:
        keyboard.append([InlineKeyboardButton("💰 Купить", callback_data=f"buy_car_{car_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к регионам", callback_data="car_shop")])
    
    # Здесь нужно добавить фото машины
    # Для примера используем заглушку
    photo_url = f"https://via.placeholder.com/400x200/333333/FFFFFF?text={car.name.replace(' ', '+')}"
    
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(media=photo_url, caption=car_text, parse_mode=ParseMode.MARKDOWN),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await query.edit_message_caption(
            caption=car_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def buy_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    car_id = int(query.data.split('_')[-1])
    car = db.get_car(car_id)
    player = db.get_player(user.id)
    
    if not car or not player:
        await query.answer("Ошибка покупки", show_alert=True)
        return
    
    if player.balance >= car.price:
        # Списываем деньги
        db.update_player_balance(user.id, -car.price)
        # Добавляем машину игроку
        db.cursor.execute(
            'INSERT INTO player_cars (user_id, car_id, horsepower, acceleration_0_100) VALUES (?, ?, ?, ?)',
            (user.id, car.id, car.horsepower, car.acceleration_0_100)
        )
        # Устанавливаем как текущую
        db.update_player_car(user.id, car.id)
        db.conn.commit()
        
        await query.answer(f"Поздравляем! Ты купил {car.name}!", show_alert=True)
        
        # Возвращаемся к просмотру машин
        market_type = context.user_data.get('market_type', 'europe')
        await show_market_cars(update, context)
    else:
        await query.answer("Недостаточно денег!", show_alert=True)

async def parts_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    shop_text = (
        "🔧 *Магазин запчастей*\n\n"
        "Улучшай характеристики своей машины:\n\n"
        "🚗 *Двигатели* - увеличивают мощность\n"
        "🌀 *Турбины* - улучшают разгон\n"
        "🛞 *Покрышки* - лучшее сцепление\n"
        "💨 *Выхлопы* - небольшой прирост\n"
        "🔄 *Подвеска* - улучшает управляемость"
    )
    
    keyboard = get_parts_shop_keyboard()
    
    await query.edit_message_caption(
        caption=shop_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def show_top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_text = "🏆 *Топ игроков*\n\n"
    
    # Топ по деньгам
    top_money = db.get_top_players_by_money(5)
    top_text += "*💰 Самые богатые:*\n"
    for i, (nickname, username, balance, rating, followers) in enumerate(top_money, 1):
        top_text += f"{i}. {nickname} - {balance:,}\n"
    
    top_text += "\n*⭐ Топ по рейтингу:*\n"
    top_rating = db.get_top_players_by_rating(5)
    for i, (nickname, username, rating, wins, followers) in enumerate(top_rating, 1):
        top_text += f"{i}. {nickname} - {rating} RP\n"
    
    top_text += "\n*🏆 Топ по победам:*\n"
    top_wins = db.get_top_players_by_wins(5)
    for i, (nickname, username, wins, rating, followers) in enumerate(top_wins, 1):
        top_text += f"{i}. {nickname} - {wins} побед\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 По деньгам", callback_data="top_money"),
         InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating")],
        [InlineKeyboardButton("🏆 По победам", callback_data="top_wins")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_caption(
        caption=top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def use_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = db.get_player(user.id)
    
    if not player:
        return
    
    # Проверяем использовал ли уже промокод
    db.cursor.execute('SELECT promo_used FROM players WHERE user_id = ?', (user.id,))
    result = db.cursor.fetchone()
    
    if result and result[0]:
        await query.answer("Ты уже использовал промокод!", show_alert=True)
        return
    
    promo_text = (
        "🎁 *Активация промокода*\n\n"
        f"Текущий промокод: *{PROMO_CODE}*\n"
        f"Награда: *{PROMO_BONUS:,}* 💰\n\n"
        "Введи промокод в ответном сообщении:"
    )
    
    await query.edit_message_caption(
        caption=promo_text,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Ждем ввод промокода
    context.user_data['waiting_for_promo'] = True
    return MAIN_MENU

async def process_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    promo_input = update.message.text.strip().upper()
    
    if promo_input == PROMO_CODE:
        player = db.get_player(user.id)
        if player:
            # Проверяем использовал ли уже
            db.cursor.execute('SELECT promo_used FROM players WHERE user_id = ?', (user.id,))
            result = db.cursor.fetchone()
            
            if result and not result[0]:
                # Начисляем бонус
                db.update_player_balance(user.id, PROMO_BONUS)
                db.cursor.execute('UPDATE players SET promo_used = TRUE WHERE user_id = ?', (user.id,))
                db.conn.commit()
                
                await update.message.reply_text(
                    f"✅ *Промокод активирован!*\nПолучено: {PROMO_BONUS:,} 💰",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text("❌ Ты уже использовал промокод!")
        else:
            await update.message.reply_text("❌ Игрок не найден!")
    else:
        await update.message.reply_text("❌ Неверный промокод!")
    
    context.user_data['waiting_for_promo'] = False
    await show_main_menu(update, context)
    return MAIN_MENU

async def duel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = db.get_player(user.id)
    
    if not player:
        return
    
    # Проверяем есть ли ожидающие дуэль
    if waiting_for_duel:
        opponent_id = next(iter(waiting_for_duel))
        if opponent_id != user.id:
            # Начинаем дуэль
            opponent_data = waiting_for_duel.pop(opponent_id)
            await start_duel(update, context, opponent_id, opponent_data['message_id'])
            return
    
    # Если нет ожидающих, становимся в очередь
    message = await query.edit_message_caption(
        caption="⚔️ *Поиск соперника...*\n\nИщем игрока для дуэли...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    waiting_for_duel[user.id] = {
        'message_id': message.message_id,
        'time': datetime.now()
    }
    
    # Удаляем старые ожидания (больше 60 секунд)
    current_time = datetime.now()
    to_remove = []
    for opp_id, data in waiting_for_duel.items():
        if (current_time - data['time']).seconds > 60:
            to_remove.append(opp_id)
    
    for opp_id in to_remove:
        waiting_for_duel.pop(opp_id, None)

async def start_duel(update: Update, context: ContextTypes.DEFAULT_TYPE, opponent_id: int, opponent_message_id: int):
    query = update.callback_query
    user = update.effective_user
    
    # Получаем данные игроков
    player1 = db.get_player(user.id)
    player2 = db.get_player(opponent_id)
    
    if not player1 or not player2:
        return
    
    car1 = db.get_car(player1.current_car_id) if player1.current_car_id else None
    car2 = db.get_car(player2.current_car_id) if player2.current_car_id else None
    
    # Рассчитываем шансы на победу
    p1_power = car1.horsepower if car1 else 100
    p2_power = car2.horsepower if car2 else 100
    
    p1_chance = p1_power / (p1_power + p2_power)
    p2_chance = 1 - p1_chance
    
    duel_text = (
        f"⚔️ *Дуэль найдена!*\n\n"
        f"*{player1.nickname}* ({p1_power} л.с.)\n"
        f"🆚\n"
        f"*{player2.nickname}* ({p2_power} л.с.)\n\n"
        f"Шансы на победу:\n"
        f"👤 {player1.nickname}: {p1_chance*100:.1f}%\n"
        f"👤 {player2.nickname}: {p2_chance*100:.1f}%\n\n"
        f"Нажми 'Готов' когда будешь готов!"
    )
    
    keyboard = [[InlineKeyboardButton("🎮 Готов к дуэли!", callback_data="duel_ready")]]
    
    # Отправляем обоим игрокам
    await query.edit_message_caption(
        caption=duel_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    try:
        await context.bot.edit_message_caption(
            chat_id=opponent_id,
            message_id=opponent_message_id,
            caption=duel_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        pass
    
    # Сохраняем данные дуэли
    context.user_data['duel_opponent'] = opponent_id
    context.user_data['duel_opponent_message'] = opponent_message_id
    context.user_data['duel_started'] = False

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("👤 Найти игрока", callback_data="admin_find")],
        [InlineKeyboardButton("💰 Выдать деньги", callback_data="admin_give_money"),
         InlineKeyboardButton("🎁 Выдать машину", callback_data="admin_give_car")],
        [InlineKeyboardButton("🚫 Забанить", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Разбанить", callback_data="admin_unban")],
        [InlineKeyboardButton("🔄 Сменить промокод", callback_data="admin_change_promo")]
    ]
    
    await update.message.reply_text(
        "👑 *Панель администратора*\n\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== ОБРАБОТЧИКИ КОЛБЭКОВ ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "main_menu" or data == "back_to_main":
        await show_main_menu(update, context)
        return MAIN_MENU
    
    elif data.startswith("prev_car_"):
        index = int(data.split('_')[-1]) - 1
        context.user_data['car_index'] = index
        await show_car_selection(update, context)
    
    elif data.startswith("next_car_"):
        index = int(data.split('_')[-1]) + 1
        context.user_data['car_index'] = index
        await show_car_selection(update, context)
    
    elif data.startswith("select_car_"):
        await select_car(update, context)
    
    elif data == "start_training":
        await start_training_race(update, context)
    
    elif data == "training_ready":
        await training_ready(update, context)
    
    elif data == "training_start":
        await training_start(update, context)
    
    elif data == "car_shop":
        await car_shop(update, context)
    
    elif data.startswith("market_"):
        if data.startswith("market_prev_") or data.startswith("market_next_"):
            index = int(data.split('_')[-1])
            if "prev" in data:
                index -= 1
            else:
                index += 1
            context.user_data['market_index'] = index
            await show_market_car(update, context, index)
        else:
            await show_market_cars(update, context)
    
    elif data.startswith("buy_car_"):
        await buy_car(update, context)
    
    elif data == "parts_shop":
        await parts_shop(update, context)
    
    elif data == "top_players":
        await show_top_players(update, context)
    
    elif data in ["top_money", "top_rating", "top_wins"]:
        await show_top_players(update, context)  # Можно расширить для разных топов
    
    elif data == "use_promo":
        await use_promo_code(update, context)
    
    elif data == "race_bot":
        await start_training_race(update, context)
    
    elif data == "duel_search":
        await duel_search(update, context)
    
    elif data == "duel_ready":
        await training_ready(update, context)  # Используем ту же логику
    
    elif data == "my_garage":
        await show_main_menu(update, context)  # Можно расширить
    
    elif data == "noop":
        await query.answer()
    
    else:
        await query.answer("Функция в разработке!")

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
async def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_promo_code))
    
    # Обработчики колбэков
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    print("============================================================")
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print(f"🎁 Промокод: {PROMO_CODE} ({PROMO_BONUS} 💰)")
    print("⚔️ Дуэли включены")
    print("💰 Улучшенная экономика")
    print("⚙️ Магазин запчастей, тюнинг машин")
    print("============================================================")
    
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
