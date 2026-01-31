#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPLETE WORKING TELEGRAM RACING BOT
Optimized for bot.host hosting
"""

import asyncio
import random
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.constants import ParseMode

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН
ADMIN_IDS = [5189651311, 5887846215]  # Добавьте ваши Telegram ID

# Состояния диалога
class States(Enum):
    START = 1
    TRAINING = 2
    CHOOSE_CAR = 3
    FIRST_RACE = 4
    READY_FOR_RACE = 5
    MAIN_MENU = 6
    GARAGE = 7
    CAR_SHOP = 8
    PARTS_SHOP = 9
    TOP_MENU = 10
    PROMO_CODE = 11
    ADMIN_PANEL = 12
    CAR_REGION = 13
    CAR_BRAND = 14
    CAR_MODEL = 15

# ==================== УПРОЩЕННАЯ БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect('racing.db', check_same_thread=False, timeout=10)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                balance INTEGER DEFAULT 10000,
                rating INTEGER DEFAULT 1000,
                followers INTEGER DEFAULT 100,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                races_total INTEGER DEFAULT 0,
                current_car INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Гараж пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS garage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                car_id INTEGER,
                is_active INTEGER DEFAULT 0,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Промокоды
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_value INTEGER,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP
            )
        ''')
        
        # Использованные промокоды
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS used_promocodes (
                user_id INTEGER,
                code TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, code)
            )
        ''')
        
        # Машины
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                region TEXT,
                price INTEGER,
                horse_power INTEGER,
                acceleration_100 REAL,
                top_speed INTEGER,
                description TEXT
            )
        ''')
        
        # Добавляем основные машины если их нет
        self.add_default_cars(cursor)
        
        # Добавляем промокоды если их нет
        self.add_default_promocodes(cursor)
        
        conn.commit()
        conn.close()
    
    def add_default_cars(self, cursor):
        # Стартовые машины
        starter_cars = [
            (1, 'Lancer X Sportback', 'Mitsubishi', 'asian', 0, 180, 8.2, 210, 'Надежный спортбек для начинающих'),
            (2, 'Opel Insignia OPC', 'Opel', 'european', 0, 280, 6.0, 250, 'Мощный немецкий седан'),
            (3, 'Cadillac CTS', 'Cadillac', 'american', 0, 320, 5.8, 240, 'Американская мощь и комфорт')
        ]
        
        # Европейские машины
        european_cars = [
            (4, 'Volkswagen Golf', 'Volkswagen', 'european', 15000, 150, 8.5, 210, 'Иконка хетчбеков'),
            (5, 'Mercedes-Benz C-Class', 'Mercedes', 'european', 35000, 255, 6.0, 250, 'Престиж и комфорт'),
            (6, 'BMW 5 Series', 'BMW', 'european', 45000, 248, 6.1, 250, 'Водительское удовольствие'),
            (7, 'Audi A6', 'Audi', 'european', 48000, 265, 5.9, 250, 'Современные технологии'),
            (8, 'Porsche Panamera', 'Porsche', 'european', 85000, 330, 5.4, 285, 'Спортивный седан'),
        ]
        
        # Азиатские машины
        asian_cars = [
            (9, 'Toyota Corolla', 'Toyota', 'asian', 18000, 140, 9.2, 195, 'Самый продаваемый автомобиль'),
            (10, 'Toyota Supra A90', 'Toyota', 'asian', 55000, 340, 4.1, 250, 'Возрожденная легенда'),
            (11, 'Honda Civic Type R', 'Honda', 'asian', 45000, 320, 5.4, 275, 'Переднеприводный чемпион'),
            (12, 'Nissan GT-R R35', 'Nissan', 'asian', 115000, 565, 2.9, 315, 'Годзилла'),
            (13, 'Mazda RX-7 FD', 'Mazda', 'asian', 45000, 255, 5.3, 250, 'Роторная легенда'),
        ]
        
        # Американские машины
        american_cars = [
            (14, 'Ford Mustang GT', 'Ford', 'american', 45000, 460, 4.0, 250, 'Американская икона'),
            (15, 'Chevrolet Corvette C8', 'Chevrolet', 'american', 65000, 495, 2.9, 312, 'Среднемоторная революция'),
            (16, 'Dodge Challenger Hellcat', 'Dodge', 'american', 70000, 717, 3.6, 315, 'Современный маслкар'),
            (17, 'Tesla Model S Plaid', 'Tesla', 'american', 135000, 1020, 1.99, 322, 'Электрический рекордсмен'),
            (18, 'Jeep Wrangler Rubicon', 'Jeep', 'american', 45000, 285, 7.5, 180, 'Легенда бездорожья'),
        ]
        
        all_cars = starter_cars + european_cars + asian_cars + american_cars
        
        for car in all_cars:
            cursor.execute('''
                INSERT OR IGNORE INTO cars VALUES (?,?,?,?,?,?,?,?,?)
            ''', car)
    
    def add_default_promocodes(self, cursor):
        promocodes = [
            ('WELCOME2024', 'money', 5000, 1000),
            ('RACINGBOT', 'money', 1000, 5000),
            ('SPEED', 'money', 2000, 1000),
            ('FOLLOWERS', 'followers', 100, 500),
        ]
        
        for code, reward_type, value, max_uses in promocodes:
            expires_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT OR IGNORE INTO promocodes 
                (code, reward_type, reward_value, max_uses, expires_at) 
                VALUES (?, ?, ?, ?, ?)
            ''', (code, reward_type, value, max_uses, expires_at))
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0], 'username': row[1], 'nickname': row[2],
                'balance': row[3], 'rating': row[4], 'followers': row[5],
                'wins': row[6], 'losses': row[7], 'races_total': row[8],
                'current_car': row[9], 'is_banned': row[10]
            }
        return None
    
    def create_user(self, user_id, username, nickname):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, nickname) 
            VALUES (?, ?, ?)
        ''', (user_id, username, nickname))
        conn.commit()
        conn.close()
    
    def update_balance(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()
        conn.close()
    
    def add_car_to_garage(self, user_id, car_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Деактивируем все машины пользователя
        cursor.execute('UPDATE garage SET is_active = 0 WHERE user_id = ?', (user_id,))
        
        # Добавляем новую машину
        cursor.execute('INSERT INTO garage (user_id, car_id, is_active) VALUES (?, ?, 1)', (user_id, car_id))
        
        # Обновляем текущую машину у пользователя
        cursor.execute('UPDATE users SET current_car = ? WHERE user_id = ?', (car_id, user_id))
        
        conn.commit()
        conn.close()
    
    def get_car_info(self, car_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            }
        return None
    
    def get_cars_by_region(self, region):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE region = ? ORDER BY price', (region,))
        rows = cursor.fetchall()
        conn.close()
        
        cars = []
        for row in rows:
            cars.append({
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            })
        return cars
    
    def get_cars_by_brand(self, brand):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE brand = ? ORDER BY price', (brand,))
        rows = cursor.fetchall()
        conn.close()
        
        cars = []
        for row in rows:
            cars.append({
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            })
        return cars
    
    def get_user_garage(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, g.is_active 
            FROM garage g 
            JOIN cars c ON g.car_id = c.id 
            WHERE g.user_id = ?
            ORDER BY g.is_active DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def check_promocode(self, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'code': row[0], 'reward_type': row[1], 'reward_value': row[2],
                'max_uses': row[3], 'used_count': row[4], 'expires_at': row[5]
            }
        return None
    
    def use_promocode(self, user_id, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверяем использовал ли уже
        cursor.execute('SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?', (user_id, code))
        if cursor.fetchone():
            conn.close()
            return False
        
        # Получаем промокод
        promo = self.check_promocode(code)
        if not promo or promo['used_count'] >= promo['max_uses']:
            conn.close()
            return False
        
        # Применяем награду
        if promo['reward_type'] == 'money':
            self.update_balance(user_id, promo['reward_value'])
        elif promo['reward_type'] == 'followers':
            cursor.execute('UPDATE users SET followers = followers + ? WHERE user_id = ?', 
                          (promo['reward_value'], user_id))
        
        # Увеличиваем счетчик использований
        cursor.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?', (code,))
        
        # Записываем использование
        cursor.execute('INSERT INTO used_promocodes (user_id, code) VALUES (?, ?)', (user_id, code))
        
        conn.commit()
        conn.close()
        return True
    
    def get_top_wins(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, wins FROM users ORDER BY wins DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_top_hp(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.nickname, MAX(c.horse_power) as max_hp
            FROM users u
            JOIN garage g ON u.user_id = g.user_id
            JOIN cars c ON g.car_id = c.id
            WHERE g.is_active = 1
            GROUP BY u.user_id
            ORDER BY max_hp DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_top_followers(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, followers FROM users ORDER BY followers DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def add_promocode_admin(self, code, reward_type, reward_value, max_uses):
        conn = self.get_connection()
        cursor = conn.cursor()
        expires_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT OR REPLACE INTO promocodes 
            (code, reward_type, reward_value, max_uses, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (code.upper(), reward_type, reward_value, max_uses, expires_at))
        conn.commit()
        conn.close()

# Инициализация базы данных
db = Database()

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        db.create_user(user.id, user.username, user.first_name)
        user_data = db.get_user(user.id)
    
    if user_data and user_data['is_banned']:
        await update.message.reply_text("⛔ Вы заблокированы в системе!")
        return
    
    welcome_text = """
    🏁 *Добро пожаловать в Racing Bot!* 🏁

    *Готовы стать легендой уличных гонок?*
    
    🚗 *Коллекция машин:*
    • Европейские, Азиатские, Американские
    • От бюджетных до гиперкаров
    
    ⚙️ *Возможности:*
    • Участвуйте в гонках
    • Зарабатывайте деньги
    • Покупайте новые машины
    • Соревнуйтесь в топах
    
    Хотите пройти обучение?
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Пройти обучение", callback_data="training_start")],
        [InlineKeyboardButton("🚀 Начать игру", callback_data="skip_training")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.START

async def training_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    training_text = """
    🎮 *ОБУЧЕНИЕ: Основы игры*

    1. *Выбор первой машины*
       - Вам доступны 3 стартовые машины
       - Выбор влияет на начальный стиль игры
    
    2. *Первая гонка*
       - Учимся стартовать
       - Знакомимся с механикой гонок
    
    3. *Основные возможности*
       - Магазин машин
       - Рейтинги и топы
       - Промокоды
    
    Готовы выбрать первую машину?
    """
    
    keyboard = [[InlineKeyboardButton("🚗 Выбрать машину", callback_data="choose_car_training")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        training_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.TRAINING

async def choose_car_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['car_index'] = 0
    return await show_training_car(update, context)

async def show_training_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    car_index = context.user_data.get('car_index', 0)
    cars = [1, 2, 3]  # ID стартовых машин
    
    car_id = cars[car_index]
    car = db.get_car_info(car_id)
    
    car_text = f"""
    🚗 *{car['name']}*
    
    📊 *Характеристики:*
    • Мощность: {car['horse_power']} л.с.
    • Разгон 0-100: {car['acceleration_100']} сек.
    • Макс. скорость: {car['top_speed']} км/ч
    
    📝 *{car['description']}*
    
    *{car_index + 1}/3*
    """
    
    keyboard = []
    nav_buttons = []
    
    if car_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"car_prev_{car_index}"))
    
    nav_buttons.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"select_car_{car_id}"))
    
    if car_index < 2:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"car_next_{car_index}"))
    
    keyboard.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_text(
        car_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CHOOSE_CAR

async def car_navigation_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if "car_next" in data:
        context.user_data['car_index'] = int(data.split("_")[2]) + 1
    elif "car_prev" in data:
        context.user_data['car_index'] = int(data.split("_")[2]) - 1
    
    return await show_training_car(update, context)

async def select_training_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    car_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id
    
    db.add_car_to_garage(user_id, car_id)
    car = db.get_car_info(car_id)
    
    await query.edit_message_text(
        f"🎉 *Поздравляем!* Вы выбрали {car['name']}!\n\n"
        f"Теперь у вас есть собственная машина. Известность не за горами! 🏁\n\n"
        f"Давайте попробуем первую гонку!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(3)
    
    race_info = """
    🏎️ *ПЕРВАЯ ГОНКА: Обучение*

    *Правила старта:*
    1. Нажмите "Готов" когда будете готовы
    2. Через 5 секунд появится кнопка "Старт"
    3. Нажмите "Старт" как можно ближе к 5 секундам
    
    *Важно:* Время реакции влияет на результат!
    
    Нажмите "Готов", когда будете готовы начать.
    """
    
    keyboard = [[InlineKeyboardButton("✅ Готов", callback_data="ready_first_race")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        race_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.FIRST_RACE

async def ready_first_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⏱️ *Ждем 5 секунд...*\n\n"
        "Приготовьтесь нажимать 'Старт' ровно через 5 секунд!\n\n"
        "Старт через: 5...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data['race_start_time'] = datetime.now()
    
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        await query.edit_message_text(
            f"⏱️ *Ждем 5 секунд...*\n\n"
            f"Приготовьтесь нажимать 'Старт' ровно через 5 секунд!\n\n"
            f"Старт через: {i}...",
            parse_mode=ParseMode.MARKDOWN
        )
    
    await asyncio.sleep(1)
    
    keyboard = [[InlineKeyboardButton("🏁 СТАРТ", callback_data="start_first_race")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🚦 *СТАРТ!* Нажимайте СЕЙЧАС!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.READY_FOR_RACE

async def start_first_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reaction_time = (datetime.now() - context.user_data['race_start_time']).total_seconds()
    
    if reaction_time < 4.8:
        reaction_text = "🚨 *Фальстарт!* Вы начали раньше времени!"
        reaction_penalty = 0.3
    elif reaction_time > 5.5:
        reaction_text = "🐌 *Задержка старта!* Вы опоздали!"
        reaction_penalty = 0.2
    elif 4.9 <= reaction_time <= 5.1:
        reaction_text = "🎯 *Идеальный старт!* Отличная реакция!"
        reaction_penalty = -0.1
    else:
        reaction_text = "👍 *Нормальный старт* Можно было лучше"
        reaction_penalty = 0.0
    
    await query.edit_message_text(
        f"{reaction_text}\nВремя реакции: {reaction_time:.2f} сек.\n\n🏎️ Ваша машина ускоряется...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(user_data['current_car'])
    
    base_time = 500 / (car['top_speed'] / 3.6)
    acceleration_factor = car['acceleration_100'] / 8.0
    race_time = base_time * acceleration_factor + reaction_penalty + random.uniform(0.1, 0.3)
    
    await asyncio.sleep(2)
    
    reward = random.randint(1000, 3000)
    followers_gain = random.randint(20, 100)
    rating_gain = random.randint(5, 20)
    
    db.update_balance(user_id, reward)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET followers = followers + ?, 
            wins = wins + 1,
            races_total = races_total + 1,
            rating = rating + ?
        WHERE user_id = ?
    ''', (followers_gain, rating_gain, user_id))
    conn.commit()
    conn.close()
    
    results_text = f"""
    🏁 *ГОНКА ЗАВЕРШЕНА!*

    📊 *Результаты:*
    • Время: {race_time:.2f} сек.
    • Реакция: {reaction_time:.2f} сек.
    • Машина: {car['name']}
    
    🎁 *Награды:*
    • 💰 +{reward} кредитов
    • 👥 +{followers_gain} подписчиков
    • ⭐ +{rating_gain} рейтинга
    
    🎉 *Обучение завершено!*
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        results_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.MAIN_MENU

async def skip_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data['current_car']:
        db.add_car_to_garage(user_id, 1)
    
    await query.edit_message_text(
        "🎮 *Обучение пропущено!*\nПереходим в главное меню...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return await main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        return await start(update, context)
    
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    
    menu_text = f"""
    🏠 *ГЛАВНОЕ МЕНЮ*

    👤 *{user_data['nickname']}*
    ⭐ Рейтинг: {user_data['rating']}
    💰 Баланс: {user_data['balance']}
    👥 Подписчики: {user_data['followers']}
    🏆 Побед: {user_data['wins']} | Поражений: {user_data['losses']}
    
    🚗 *Текущая машина:* {current_car['name'] if current_car else 'Нет'}
    💪 {current_car['horse_power'] if current_car else 0} л.с.
    
    *Выберите действие:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🏎️ Быстрая гонка", callback_data="quick_race")],
        [InlineKeyboardButton("🚗 Мой гараж", callback_data="my_garage")],
        [InlineKeyboardButton("🏪 Магазин машин", callback_data="car_shop")],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="top_menu")],
        [InlineKeyboardButton("🎁 Ввести промокод", callback_data="enter_promo")],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    return States.MAIN_MENU

async def quick_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data['current_car']:
        await query.edit_message_text(
            "🚫 У вас нет машины! Сначала купите машину в магазине.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await main_menu(update, context)
    
    race_info = """
    🏎️ *БЫСТРАЯ ГОНКА*

    Правила:
    • Дистанция: 1000 метров
    • Соперник: Рандомный игрок из базы
    • Награда: Кредиты + Подписчики + Рейтинг
    
    Готовы к гонке?
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Начать гонку", callback_data="start_quick_race")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        race_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.MAIN_MENU

async def my_garage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    garage_cars = db.get_user_garage(user_id)
    
    if not garage_cars:
        await query.edit_message_text(
            "🚗 *Ваш гараж пуст!*\nКупите свою первую машину в магазине!",
            parse_mode=ParseMode.MARKDOWN
        )
        return await main_menu(update, context)
    
    garage_text = "🚗 *ВАШ ГАРАЖ*\n\n"
    
    for i, car in enumerate(garage_cars, 1):
        status = "✅ Активна" if car[9] == 1 else "⚪ Не активна"
        garage_text += f"{i}. *{car[1]}*\n"
        garage_text += f"   💪 {car[5]} л.с. | ⏱️ {car[6]} сек.\n"
        garage_text += f"   {status}\n\n"
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        garage_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.GARAGE

async def car_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    shop_text = """
    🏪 *МАГАЗИН МАШИН*

    Выберите регион:
    
    🇪🇺 *Европейский автопром*
    🇯🇵 *Азиатский автопром*  
    🇺🇸 *Американский автопром*
    """
    
    keyboard = [
        [InlineKeyboardButton("🇪🇺 Европейский", callback_data="shop_european")],
        [InlineKeyboardButton("🇯🇵 Азиатский", callback_data="shop_asian")],
        [InlineKeyboardButton("🇺🇸 Американский", callback_data="shop_american")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        shop_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CAR_SHOP

async def shop_european(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    european_brands = ["Volkswagen", "Mercedes", "BMW", "Audi", "Porsche"]
    
    keyboard = []
    for brand in european_brands:
        keyboard.append([InlineKeyboardButton(brand, callback_data=f"brand_{brand}")])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🇪🇺 *ЕВРОПЕЙСКИЕ МАРКИ*\nВыберите марку:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CAR_BRAND

async def shop_asian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    asian_brands = ["Toyota", "Honda", "Nissan", "Mazda", "Mitsubishi"]
    
    keyboard = []
    for brand in asian_brands:
        keyboard.append([InlineKeyboardButton(brand, callback_data=f"brand_{brand}")])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🇯🇵 *АЗИАТСКИЕ МАРКИ*\nВыберите марку:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CAR_BRAND

async def shop_american(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    american_brands = ["Ford", "Chevrolet", "Dodge", "Tesla", "Jeep"]
    
    keyboard = []
    for brand in american_brands:
        keyboard.append([InlineKeyboardButton(brand, callback_data=f"brand_{brand}")])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🇺🇸 *АМЕРИКАНСКИЕ МАРКИ*\nВыберите марку:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CAR_BRAND

async def show_brand_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    brand = query.data.split("_")[1]
    context.user_data['current_brand'] = brand
    context.user_data['model_index'] = 0
    
    cars = db.get_cars_by_brand(brand)
    
    if not cars:
        await query.edit_message_text(
            f"🚫 Машины марки {brand} временно отсутствуют.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await car_shop(update, context)
    
    context.user_data['brand_cars'] = cars
    return await show_car_model(update, context)

async def show_car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cars = context.user_data.get('brand_cars', [])
    if not cars:
        return await car_shop(update, context)
    
    index = context.user_data.get('model_index', 0)
    car = cars[index]
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    car_text = f"""
    🚗 *{car['brand']} {car['name']}*
    
    📊 *Характеристики:*
    • Мощность: {car['horse_power']} л.с.
    • Разгон 0-100: {car['acceleration_100']} сек.
    • Макс. скорость: {car['top_speed']} км/ч
    
    💰 *Цена:* {car['price']} кредитов
    📝 *{car['description']}*
    
    *{index + 1}/{len(cars)}*
    """
    
    keyboard = []
    nav_buttons = []
    
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="model_prev"))
    
    if user_data['balance'] >= car['price']:
        nav_buttons.append(InlineKeyboardButton("🛒 Купить", callback_data=f"buy_car_{car['id']}"))
    else:
        nav_buttons.append(InlineKeyboardButton("💸 Недостаточно средств", callback_data="no_money"))
    
    if index < len(cars) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="model_next"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🏪 Назад в магазин", callback_data="car_shop")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        car_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.CAR_MODEL

async def navigate_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "model_next":
        context.user_data['model_index'] += 1
    elif query.data == "model_prev":
        context.user_data['model_index'] -= 1
    
    return await show_car_model(update, context)

async def buy_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    car_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(car_id)
    
    if user_data['balance'] < car['price']:
        await query.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    db.update_balance(user_id, -car['price'])
    db.add_car_to_garage(user_id, car_id)
    
    await query.edit_message_text(
        f"🎉 *Поздравляем с покупкой!*\n\n"
        f"Вы приобрели *{car['brand']} {car['name']}*\n"
        f"💸 Списано: {car['price']} кредитов\n"
        f"💰 Ваш баланс: {user_data['balance'] - car['price']} кредитов",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(3)
    return await main_menu(update, context)

async def top_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_wins = db.get_top_wins(10)
    top_hp = db.get_top_hp(10)
    top_followers = db.get_top_followers(10)
    
    top_text = "🏆 *ТОП ИГРОКОВ*\n\n"
    
    top_text += "*Топ по победам:*\n"
    for i, (nickname, wins) in enumerate(top_wins, 1):
        top_text += f"{i}. {nickname}: {wins} побед\n"
    
    top_text += "\n*Топ по мощности машин:*\n"
    for i, (nickname, hp) in enumerate(top_hp, 1):
        top_text += f"{i}. {nickname}: {hp} л.с.\n"
    
    top_text += "\n*Топ по подписчикам:*\n"
    for i, (nickname, followers) in enumerate(top_followers, 1):
        top_text += f"{i}. {nickname}: {followers} подписчиков\n"
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.TOP_MENU

async def enter_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎁 *ВВЕДИТЕ ПРОМОКОД*\n\n"
        "Отправьте промокод в чат:\n\n"
        "*Пример:* WELCOME2024\n"
        "*Активные промокоды:*\n"
        "• WELCOME2024 - 5000 кредитов\n"
        "• RACINGBOT - 1000 кредитов\n"
        "• SPEED - 2000 кредитов",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return States.PROMO_CODE

async def process_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo_code = update.message.text.upper().strip()
    user_id = update.effective_user.id
    
    if db.use_promocode(user_id, promo_code):
        promo = db.check_promocode(promo_code)
        reward_text = f"{promo['reward_value']} кредитов" if promo['reward_type'] == 'money' else f"{promo['reward_value']} подписчиков"
        
        await update.message.reply_text(
            f"🎉 *Промокод активирован!*\n\n"
            f"Награда: {reward_text}\n"
            f"Осталось использований: {promo['max_uses'] - promo['used_count'] - 1}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "❌ *Неверный промокод!*\n\n"
            "Возможные причины:\n"
            "• Промокод не существует\n"
            "• Вы уже использовали этот промокод\n"
            "• Лимит использований исчерпан",
            parse_mode=ParseMode.MARKDOWN
        )
    
    return await main_menu(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.callback_query.answer("⛔ Доступ запрещен!", show_alert=True)
        return
    
    query = update.callback_query
    await query.answer()
    
    admin_text = """
    👑 *АДМИН ПАНЕЛЬ*

    *Доступные команды:*
    
    /addpromo CODE TYPE VALUE USES - Добавить промокод
    Пример: /addpromo TEST money 1000 100
    
    /ban USER_ID - Забанить пользователя
    /unban USER_ID - Разбанить пользователя
    
    /addmoney USER_ID AMOUNT - Выдать деньги
    /addfollowers USER_ID AMOUNT - Выдать подписчиков
    
    /stats - Статистика бота
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        admin_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.ADMIN_PANEL

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    command = update.message.text.split()
    
    if len(command) < 2:
        await update.message.reply_text(
            "👑 *АДМИН КОМАНДЫ*\n\n"
            "/addpromo CODE TYPE VALUE USES - Добавить промокод\n"
            "/ban USER_ID - Забанить\n"
            "/unban USER_ID - Разбанить\n"
            "/addmoney USER_ID AMOUNT - Выдать деньги\n"
            "/addfollowers USER_ID AMOUNT - Выдать подписчиков\n"
            "/stats - Статистика",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    cmd = command[1]
    
    if cmd == "addpromo" and len(command) == 6:
        code = command[2].upper()
        reward_type = command[3]
        reward_value = int(command[4])
        max_uses = int(command[5])
        
        db.add_promocode_admin(code, reward_type, reward_value, max_uses)
        await update.message.reply_text(f"✅ Промокод {code} добавлен!")
    
    elif cmd == "ban" and len(command) == 3:
        target_id = int(command[2])
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (target_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Пользователь {target_id} забанен!")
    
    elif cmd == "unban" and len(command) == 3:
        target_id = int(command[2])
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (target_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен!")
    
    elif cmd == "addmoney" and len(command) == 4:
        target_id = int(command[2])
        amount = int(command[3])
        db.update_balance(target_id, amount)
        await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} кредитов!")
    
    elif cmd == "addfollowers" and len(command) == 4:
        target_id = int(command[2])
        amount = int(command[3])
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET followers = followers + ? WHERE user_id = ?', 
                      (amount, target_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} подписчиков!")
    
    elif cmd == "stats":
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
        banned_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(wins) FROM users')
        total_wins = cursor.fetchone()[0] or 0
        
        conn.close()
        
        stats_text = f"""
        📊 *СТАТИСТИКА БОТА*
        
        👥 Пользователи: {total_users}
        ⛔ Забанено: {banned_users}
        💰 Общий баланс: {total_balance}
        🏆 Всего побед: {total_wins}
        """
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    🆘 *ПОМОЩЬ ПО БОТУ*

    *Основные команды:*
    /start - Начать игру
    /menu - Главное меню
    /help - Эта справка
    /profile - Ваш профиль
    
    *Как играть:*
    1. Выберите/купите машину
    2. Участвуйте в гонках
    3. Зарабатывайте деньги
    4. Покупайте новые машины
    5. Соревнуйтесь за место в топе
    
    *Управление:*
    • Используйте кнопки под сообщениями
    • Вводите промокоды в чат
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    
    profile_text = f"""
    👤 *ПРОФИЛЬ ИГРОКА*
    
    *Основное:*
    • Имя: {user_data['nickname']}
    • Рейтинг: {user_data['rating']} ⭐
    • Баланс: {user_data['balance']} 💰
    • Подписчики: {user_data['followers']} 👥
    
    *Статистика:*
    • Побед: {user_data['wins']} 🏆
    • Поражений: {user_data['losses']} 💔
    • Всего гонок: {user_data['races_total']} 🏎️
    
    *Текущая машина:*
    • {current_car['name'] if current_car else 'Нет машины'}
    • Мощность: {current_car['horse_power'] if current_car else 0} л.с.
    """
    
    await update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.START: [
                CallbackQueryHandler(training_start, pattern='^training_start$'),
                CallbackQueryHandler(skip_training, pattern='^skip_training$'),
            ],
            States.TRAINING: [
                CallbackQueryHandler(choose_car_training, pattern='^choose_car_training$'),
            ],
            States.CHOOSE_CAR: [
                CallbackQueryHandler(car_navigation_training, pattern='^car_(next|prev)_'),
                CallbackQueryHandler(select_training_car, pattern='^select_car_'),
            ],
            States.FIRST_RACE: [
                CallbackQueryHandler(ready_first_race, pattern='^ready_first_race$'),
            ],
            States.READY_FOR_RACE: [
                CallbackQueryHandler(start_first_race, pattern='^start_first_race$'),
            ],
            States.MAIN_MENU: [
                CallbackQueryHandler(quick_race, pattern='^quick_race$'),
                CallbackQueryHandler(my_garage, pattern='^my_garage$'),
                CallbackQueryHandler(car_shop, pattern='^car_shop$'),
                CallbackQueryHandler(top_menu, pattern='^top_menu$'),
                CallbackQueryHandler(enter_promo, pattern='^enter_promo$'),
                CallbackQueryHandler(admin_panel, pattern='^admin_panel$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.CAR_SHOP: [
                CallbackQueryHandler(shop_european, pattern='^shop_european$'),
                CallbackQueryHandler(shop_asian, pattern='^shop_asian$'),
                CallbackQueryHandler(shop_american, pattern='^shop_american$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.CAR_BRAND: [
                CallbackQueryHandler(show_brand_models, pattern='^brand_'),
                CallbackQueryHandler(car_shop, pattern='^car_shop$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.CAR_MODEL: [
                CallbackQueryHandler(navigate_models, pattern='^model_(next|prev)$'),
                CallbackQueryHandler(buy_car, pattern='^buy_car_'),
                CallbackQueryHandler(car_shop, pattern='^car_shop$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_promo),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Добавляем обработчики команд
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('menu', main_menu))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('stats', admin_command))
    
    # Запускаем бота
    print("=" * 50)
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎁 Промокоды: WELCOME2024, RACINGBOT, SPEED")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
