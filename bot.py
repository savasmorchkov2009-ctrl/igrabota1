#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPLETE TELEGRAM RACING BOT - STABLE VERSION
Optimized for bot.host hosting
"""

import asyncio
import random
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import time
from collections import defaultdict

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
    DUEL_INVITE = 16
    DUEL_WAITING = 17
    DUEL_RACE = 18
    PARTS_CATEGORY = 19
    PARTS_LIST = 20

# ==================== УПРОЩЕННАЯ БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('racing.db', check_same_thread=False)
        self.init_database()
    
    def init_database(self):
        cursor = self.conn.cursor()
        
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Дуэли
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                bet INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Все машины
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
        
        # Запчасти
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY,
                category TEXT,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp_boost INTEGER,
                description TEXT
            )
        ''')
        
        # Установленные запчасти
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS installed_parts (
                user_id INTEGER,
                car_id INTEGER,
                part_id INTEGER,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, car_id, part_id)
            )
        ''')
        
        # Добавляем данные если их нет
        self.add_default_data(cursor)
        
        self.conn.commit()
    
    def add_default_data(self, cursor):
        # Добавляем тестовые промокоды
        promocodes = [
            ('WELCOME2024', 'money', 5000, 1000),
            ('RACINGBOT', 'money', 3000, 5000),
            ('SPEED', 'money', 2000, 1000),
            ('FOLLOWERS', 'followers', 150, 500),
            ('RICH', 'money', 10000, 100),
        ]
        
        for code, reward_type, value, max_uses in promocodes:
            expires_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT OR IGNORE INTO promocodes VALUES (?, ?, ?, ?, ?, ?)
            ''', (code, reward_type, value, max_uses, 0, expires_at))
        
        # Добавляем ВСЕ машины из списка (сокращенная версия для примера)
        all_cars = self.get_all_cars_data()
        for car in all_cars:
            cursor.execute('''
                INSERT OR IGNORE INTO cars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', car)
        
        # Добавляем запчасти
        all_parts = self.get_all_parts_data()
        for part in all_parts:
            cursor.execute('''
                INSERT OR IGNORE INTO parts VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', part)
    
    def get_all_cars_data(self):
        cars = []
        car_id = 1
        
        # Стартовые машины
        cars.extend([
            (car_id, 'Lancer X Sportback', 'Mitsubishi', 'asian', 0, 180, 8.2, 210, 'Надежный спортбек'),
            (car_id+1, 'Opel Insignia OPC', 'Opel', 'european', 0, 280, 6.0, 250, 'Мощный немецкий седан'),
            (car_id+2, 'Cadillac CTS', 'Cadillac', 'american', 0, 320, 5.8, 240, 'Американская мощь'),
        ])
        car_id += 3
        
        # Европейские машины
        european_cars = [
            ('Volkswagen Golf', 'Volkswagen', 15000, 150, 8.5, 210),
            ('Volkswagen Passat', 'Volkswagen', 20000, 190, 7.9, 230),
            ('Mercedes-Benz C-Class', 'Mercedes', 35000, 255, 6.0, 250),
            ('Mercedes-Benz E-Class', 'Mercedes', 50000, 299, 5.7, 250),
            ('BMW 5 Series', 'BMW', 45000, 248, 6.1, 250),
            ('BMW X3', 'BMW', 42000, 248, 6.0, 230),
            ('Audi A6', 'Audi', 48000, 265, 5.9, 250),
            ('Audi Q7', 'Audi', 65000, 340, 5.7, 250),
            ('Porsche Panamera', 'Porsche', 85000, 330, 5.4, 285),
            ('Porsche Macan', 'Porsche', 68000, 265, 6.2, 260),
            ('Ferrari Roma', 'Ferrari', 220000, 620, 3.4, 320),
            ('Ferrari F8 Tributo', 'Ferrari', 280000, 720, 2.9, 340),
            ('Lamborghini Huracán', 'Lamborghini', 250000, 640, 2.9, 325),
            ('Lamborghini Aventador', 'Lamborghini', 450000, 780, 2.8, 350),
            ('Bugatti Chiron', 'Bugatti', 3000000, 1500, 2.4, 420),
            ('Rolls-Royce Cullinan', 'Rolls-Royce', 350000, 571, 5.2, 250),
            ('Bentley Flying Spur', 'Bentley', 220000, 635, 3.8, 333),
            ('McLaren 720S', 'McLaren', 280000, 720, 2.9, 341),
            ('Jaguar F-PACE', 'Jaguar', 52000, 300, 5.8, 250),
            ('Volvo S60', 'Volvo', 38000, 250, 6.5, 235),
        ]
        
        for name, brand, price, hp, acc, speed in european_cars:
            cars.append((car_id, name, brand, 'european', price, hp, acc, speed, f'{brand} {name}'))
            car_id += 1
        
        # Азиатские машины
        asian_cars = [
            ('Toyota Corolla', 'Toyota', 18000, 140, 9.2, 195),
            ('Toyota Camry', 'Toyota', 25000, 203, 7.9, 230),
            ('Toyota Supra A90', 'Toyota', 55000, 340, 4.1, 250),
            ('Toyota GR86', 'Toyota', 32000, 235, 6.1, 240),
            ('Honda Civic Type R', 'Honda', 45000, 320, 5.4, 275),
            ('Honda NSX', 'Honda', 165000, 581, 2.9, 307),
            ('Nissan GT-R R35', 'Nissan', 115000, 565, 2.9, 315),
            ('Nissan 350Z', 'Nissan', 22000, 287, 5.8, 250),
            ('Mazda RX-7 FD', 'Mazda', 45000, 255, 5.3, 250),
            ('Mazda MX-5 Miata', 'Mazda', 28000, 184, 6.5, 230),
            ('Subaru Impreza WRX STI', 'Subaru', 38000, 310, 5.2, 255),
            ('Mitsubishi Lancer Evolution X', 'Mitsubishi', 35000, 303, 5.1, 250),
            ('Hyundai i30 N', 'Hyundai', 35000, 280, 5.9, 250),
            ('Kia Stinger', 'Kia', 42000, 370, 4.7, 270),
            ('Lexus LC500', 'Lexus', 95000, 477, 4.4, 270),
        ]
        
        for name, brand, price, hp, acc, speed in asian_cars:
            cars.append((car_id, name, brand, 'asian', price, hp, acc, speed, f'{brand} {name}'))
            car_id += 1
        
        # Американские машины
        american_cars = [
            ('Ford Mustang GT', 'Ford', 45000, 460, 4.0, 250),
            ('Ford F-150 Raptor', 'Ford', 65000, 450, 5.1, 180),
            ('Ford GT', 'Ford', 500000, 660, 3.0, 347),
            ('Chevrolet Corvette C8', 'Chevrolet', 65000, 495, 2.9, 312),
            ('Chevrolet Camaro ZL1', 'Chevrolet', 65000, 650, 3.5, 320),
            ('Dodge Challenger Hellcat', 'Dodge', 70000, 717, 3.6, 315),
            ('Tesla Model S Plaid', 'Tesla', 135000, 1020, 1.99, 322),
            ('Jeep Wrangler Rubicon', 'Jeep', 45000, 285, 7.5, 180),
            ('Cadillac Escalade', 'Cadillac', 90000, 420, 5.8, 210),
            ('Ram 1500 TRX', 'Ram', 80000, 702, 4.5, 190),
        ]
        
        for name, brand, price, hp, acc, speed in american_cars:
            cars.append((car_id, name, brand, 'american', price, hp, acc, speed, f'{brand} {name}'))
            car_id += 1
        
        return cars
    
    def get_all_parts_data(self):
        parts = []
        part_id = 1
        
        # Двигатели
        engines = [
            ('engine', 'Volkswagen EA888 2.0 TSI', 'Volkswagen', 5000, 50, 'Немецкий турбодвигатель'),
            ('engine', 'Toyota 2JZ-GTE 3.0 I6 TwinTurbo', 'Toyota', 15000, 120, 'Легендарный японский двигатель'),
            ('engine', 'Chevrolet LS3 6.2 V8', 'Chevrolet', 12000, 150, 'Американский V8'),
            ('engine', 'BMW B58 3.0 I6', 'BMW', 12000, 100, 'Немецкая рядная шестерка'),
            ('engine', 'Honda K20A 2.0 I4 VTEC', 'Honda', 8500, 60, 'Высокооборотный VTEC'),
        ]
        
        for category, name, brand, price, hp_boost, desc in engines:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Турбины
        turbos = [
            ('turbo', 'Garrett GT28', 'Garrett', 3000, 30, 'Турбина для быстрого отклика'),
            ('turbo', 'Garrett GT35', 'Garrett', 6000, 60, 'Мощная турбина'),
            ('turbo', 'BorgWarner EFR 6258', 'BorgWarner', 5500, 55, 'Высокоэффективная турбина'),
            ('turbo', 'Mitsubishi TD05', 'Mitsubishi', 3500, 35, 'Японская надежность'),
            ('turbo', 'HKS GT2835', 'HKS', 7200, 72, 'Тюнинговая турбина'),
        ]
        
        for category, name, brand, price, hp_boost, desc in turbos:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Выхлопы
        exhausts = [
            ('exhaust', 'Akrapovič Evolution', 'Akrapovič', 5000, 15, 'Титановый выхлоп'),
            ('exhaust', 'HKS Hi-Power', 'HKS', 3800, 14, 'Японский прямоточный выхлоп'),
            ('exhaust', 'Borla Atak', 'Borla', 3500, 13, 'Американский спортивный выхлоп'),
        ]
        
        for category, name, brand, price, hp_boost, desc in exhausts:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Радиаторы
        radiators = [
            ('radiator', 'Mishimoto M-Line', 'Mishimoto', 1800, 5, 'Улучшенное охлаждение'),
            ('radiator', 'Koyo Racing', 'Koyo', 2200, 7, 'Гоночный радиатор'),
        ]
        
        for category, name, brand, price, hp_boost, desc in radiators:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Закись азота
        nitro_kits = [
            ('nitro', 'NOS Sniper Kit', 'NOS', 5000, 100, 'Система закиси азота'),
            ('nitro', 'ZEX Nitrous Kit', 'ZEX', 4500, 90, 'Сухая система закиси'),
        ]
        
        for category, name, brand, price, hp_boost, desc in nitro_kits:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Подвеска
        suspensions = [
            ('suspension', 'KW Variant 3', 'KW', 7000, 0, 'Регулируемая подвеска'),
            ('suspension', 'Tein Flex Z', 'Tein', 4500, 0, 'Японская подвеска'),
        ]
        
        for category, name, brand, price, hp_boost, desc in suspensions:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        # Покрышки
        tires = [
            ('tires', 'Michelin Pilot Sport 4 S', 'Michelin', 2000, 10, 'Спортивные покрышки'),
            ('tires', 'Bridgestone Potenza Sport', 'Bridgestone', 1900, 9, 'Гоночные покрышки'),
        ]
        
        for category, name, brand, price, hp_boost, desc in tires:
            parts.append((part_id, category, name, brand, price, hp_boost, desc))
            part_id += 1
        
        return parts
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'user_id': row[0], 'username': row[1], 'nickname': row[2],
                'balance': row[3], 'rating': row[4], 'followers': row[5],
                'wins': row[6], 'losses': row[7], 'races_total': row[8],
                'current_car': row[9], 'is_banned': row[10]
            }
        return None
    
    def create_user(self, user_id: int, username: str, nickname: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, nickname) 
            VALUES (?, ?, ?)
        ''', (user_id, username, nickname))
        self.conn.commit()
    
    def update_user(self, user_id: int, **kwargs):
        cursor = self.conn.cursor()
        for key, value in kwargs.items():
            cursor.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
        self.conn.commit()
    
    def update_balance(self, user_id: int, amount: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def add_car_to_garage(self, user_id: int, car_id: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE garage SET is_active = 0 WHERE user_id = ?', (user_id,))
        cursor.execute('INSERT INTO garage (user_id, car_id, is_active) VALUES (?, ?, 1)', 
                      (user_id, car_id))
        cursor.execute('UPDATE users SET current_car = ? WHERE user_id = ?', (car_id, user_id))
        self.conn.commit()
    
    def get_car_info(self, car_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            }
        return None
    
    def get_cars_by_region(self, region: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE region = ? AND price > 0 ORDER BY price', (region,))
        rows = cursor.fetchall()
        
        cars = []
        for row in rows:
            cars.append({
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            })
        return cars
    
    def get_cars_by_brand(self, brand: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE brand = ? ORDER BY price', (brand,))
        rows = cursor.fetchall()
        
        cars = []
        for row in rows:
            cars.append({
                'id': row[0], 'name': row[1], 'brand': row[2], 
                'region': row[3], 'price': row[4], 'horse_power': row[5],
                'acceleration_100': row[6], 'top_speed': row[7], 'description': row[8]
            })
        return cars
    
    def get_user_garage(self, user_id: int) -> List:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.*, g.is_active 
            FROM garage g 
            JOIN cars c ON g.car_id = c.id 
            WHERE g.user_id = ?
            ORDER BY g.is_active DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def check_promocode(self, code: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code,))
        row = cursor.fetchone()
        
        if row:
            return {
                'code': row[0], 'reward_type': row[1], 'reward_value': row[2],
                'max_uses': row[3], 'used_count': row[4], 'expires_at': row[5]
            }
        return None
    
    def use_promocode(self, user_id: int, code: str) -> bool:
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?', 
                      (user_id, code))
        if cursor.fetchone():
            return False
        
        promo = self.check_promocode(code)
        if not promo or promo['used_count'] >= promo['max_uses']:
            return False
        
        if promo['reward_type'] == 'money':
            self.update_balance(user_id, promo['reward_value'])
        elif promo['reward_type'] == 'followers':
            cursor.execute('UPDATE users SET followers = followers + ? WHERE user_id = ?', 
                          (promo['reward_value'], user_id))
        
        cursor.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?', (code,))
        cursor.execute('INSERT INTO used_promocodes (user_id, code) VALUES (?, ?)', 
                      (user_id, code))
        
        self.conn.commit()
        return True
    
    def get_top_wins(self, limit: int = 10) -> List:
        cursor = self.conn.cursor()
        cursor.execute('SELECT nickname, wins, rating FROM users ORDER BY wins DESC LIMIT ?', (limit,))
        return cursor.fetchall()
    
    def get_top_rating(self, limit: int = 10) -> List:
        cursor = self.conn.cursor()
        cursor.execute('SELECT nickname, rating, wins FROM users ORDER BY rating DESC LIMIT ?', (limit,))
        return cursor.fetchall()
    
    def get_top_money(self, limit: int = 10) -> List:
        cursor = self.conn.cursor()
        cursor.execute('SELECT nickname, balance, followers FROM users ORDER BY balance DESC LIMIT ?', (limit,))
        return cursor.fetchall()
    
    def get_top_followers(self, limit: int = 10) -> List:
        cursor = self.conn.cursor()
        cursor.execute('SELECT nickname, followers, wins FROM users ORDER BY followers DESC LIMIT ?', (limit,))
        return cursor.fetchall()
    
    def get_top_hp(self, limit: int = 10) -> List:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.nickname, MAX(c.horse_power) as max_hp, u.wins
            FROM users u
            JOIN garage g ON u.user_id = g.user_id
            JOIN cars c ON g.car_id = c.id
            WHERE g.is_active = 1
            GROUP BY u.user_id
            ORDER BY max_hp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def create_duel(self, challenger_id: int, opponent_id: int, bet: int = 0) -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet, status)
            VALUES (?, ?, ?, 'pending')
        ''', (challenger_id, opponent_id, bet))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_duel(self, duel_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM duels WHERE id = ?', (duel_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0], 'challenger_id': row[1], 'opponent_id': row[2],
                'status': row[3], 'winner_id': row[4], 'bet': row[5],
                'created_at': row[6]
            }
        return None
    
    def update_duel(self, duel_id: int, **kwargs):
        cursor = self.conn.cursor()
        for key, value in kwargs.items():
            cursor.execute(f'UPDATE duels SET {key} = ? WHERE id = ?', (value, duel_id))
        self.conn.commit()
    
    def get_parts_by_category(self, category: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM parts WHERE category = ? ORDER BY price', (category,))
        rows = cursor.fetchall()
        
        parts = []
        for row in rows:
            parts.append({
                'id': row[0], 'category': row[1], 'name': row[2], 'brand': row[3],
                'price': row[4], 'hp_boost': row[5], 'description': row[6]
            })
        return parts
    
    def get_installed_parts(self, user_id: int, car_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.* 
            FROM installed_parts ip
            JOIN parts p ON ip.part_id = p.id
            WHERE ip.user_id = ? AND ip.car_id = ?
        ''', (user_id, car_id))
        rows = cursor.fetchall()
        
        parts = []
        for row in rows:
            parts.append({
                'id': row[0], 'category': row[1], 'name': row[2], 'brand': row[3],
                'price': row[4], 'hp_boost': row[5], 'description': row[6]
            })
        return parts
    
    def install_part(self, user_id: int, car_id: int, part_id: int) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO installed_parts (user_id, car_id, part_id)
                VALUES (?, ?, ?)
            ''', (user_id, car_id, part_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_total_hp_boost(self, user_id: int, car_id: int) -> int:
        parts = self.get_installed_parts(user_id, car_id)
        total_boost = sum(part['hp_boost'] for part in parts)
        return total_boost
    
    def get_active_users(self, limit: int = 50) -> List:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, nickname, rating, balance 
            FROM users 
            WHERE is_banned = 0 AND user_id NOT IN (SELECT user_id FROM users WHERE last_seen < datetime('now', '-1 day'))
            ORDER BY last_seen DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def update_last_seen(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        self.conn.commit()

# Глобальная переменная для базы данных
db = Database()

# Кэш активных дуэлей
active_duels = {}
duel_invites = {}

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name)
    db.update_last_seen(user.id)
    
    welcome_text = """
    🏁 *Добро пожаловать в Racing Bot!* 🏁

    *Готовы стать легендой уличных гонок?*
    
    🚗 *Коллекция машин:*
    • 45+ уникальных моделей
    • Европейские, Азиатские, Американские
    • От бюджетных до гиперкаров
    
    ⚙️ *Новые возможности:*
    • Дуэли с реальными игроками
    • Магазин запчастей для тюнинга
    • 5 видов топов
    • Улучшенная экономика
    
    🏆 *Соревнования:*
    • Рейтинговая система (PVP)
    • Топы: победы, рейтинг, деньги
    • Награды за победы
    
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
       - Каждая имеет уникальные характеристики
       - Выбор влияет на начальный стиль игры
    
    2. *Первая гонка (Против бота)*
       - Учимся стартовать
       - Знакомимся с механикой гонок
    
    3. *Основные возможности*
       - Магазин машин
       - Магазин запчастей
       - Дуэли с игроками
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
    
    if not car:
        return await main_menu(update, context)
    
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
    
    await update.callback_query.edit_message_text(
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
    db.update_last_seen(user_id)
    car = db.get_car_info(car_id)
    
    await query.edit_message_text(
        f"🎉 *Поздравляем!* Вы выбрали {car['name']}!\n\n"
        f"Теперь у вас есть собственная машина. Известность не за горами! 🏁\n\n"
        f"Давайте попробуем первую гонку!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(2)
    
    race_info = """
    🏎️ *ПЕРВАЯ ГОНКА: Обучение*

    *Правила старта:*
    1. Нажмите "Готов" когда будете готовы
    2. Через 5 секунд появится кнопка "Старт"
    3. Нажмите "Старт" в промежутке 5-6 секунд
    4. Если раньше 5 сек - фальстарт
    5. Если позже 6 сек - поздний старт
    
    *Важно:* Только правильный старт ведет к победе!
    
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
    
    context.user_data['race_start_time'] = time.time()
    
    await query.edit_message_text(
        "⏱️ *Ждем 5 секунд...*\n\n"
        "Приготовьтесь нажимать 'Старт' между 5 и 6 секундами!\n\n"
        "Старт через: 5...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        await query.edit_message_text(
            f"⏱️ *Ждем 5 секунд...*\n\n"
            f"Приготовьтесь нажимать 'Старт' между 5 и 6 секундами!\n\n"
            f"Старт через: {i}...",
            parse_mode=ParseMode.MARKDOWN
        )
    
    await asyncio.sleep(1)
    
    keyboard = [[InlineKeyboardButton("🏁 СТАРТ", callback_data="start_first_race")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🚦 *СТАРТ!* Нажимайте между 5 и 6 секундами!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.READY_FOR_RACE

async def start_first_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reaction_time = time.time() - context.user_data['race_start_time']
    
    # НОВАЯ СИСТЕМА: 5-6 секунд - успех
    if reaction_time < 5.0:
        reaction_text = "🚨 *Фальстарт!* Вы начали раньше времени!"
        reaction_penalty = 0.5
        is_success = False
    elif reaction_time > 6.0:
        reaction_text = "🐌 *Поздний старт!* Вы опоздали!"
        reaction_penalty = 0.3
        is_success = False
    else:
        reaction_text = "🎯 *Отличный старт!* Идеальное время!"
        reaction_penalty = -0.2
        is_success = True
    
    await query.edit_message_text(
        f"{reaction_text}\nВремя реакции: {reaction_time:.2f} сек.\n\n🏎️ Ваша машина ускоряется...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(user_data['current_car'])
    
    # Расчет времени гонки с учетом тюнинга
    hp_boost = db.get_total_hp_boost(user_id, car['id'])
    total_hp = car['horse_power'] + hp_boost
    
    base_time = 500 / (car['top_speed'] / 3.6)
    acceleration_factor = car['acceleration_100'] / (8.0 - (total_hp / 1000))
    race_time = base_time * acceleration_factor + reaction_penalty + random.uniform(0.1, 0.3)
    
    await asyncio.sleep(2)
    
    # УЛУЧШЕННАЯ ЭКОНОМИКА
    if is_success:
        reward = random.randint(2000, 5000)
        followers_gain = random.randint(50, 200)
        rating_gain = 0  # Против бота рейтинг не начисляется
        
        result_text = f"""
        🏆 *ПОБЕДА НАД БОТОМ!*

        📊 *Результаты:*
        • Время: {race_time:.2f} сек.
        • Реакция: {reaction_time:.2f} сек.
        • Машина: {car['name']}
        • Мощность: {total_hp} л.с. (с тюнингом)
        
        🎁 *Награды:*
        • 💰 +{reward} кредитов
        • 👥 +{followers_gain} подписчиков
        
        🎉 *Обучение завершено!*
        """
        
        db.update_balance(user_id, reward)
        db.update_user(user_id, followers=user_data['followers'] + followers_gain,
                      wins=user_data['wins'] + 1, races_total=user_data['races_total'] + 1)
    else:
        reward = random.randint(200, 500)  # Небольшая компенсация
        
        result_text = f"""
        🥈 *ПОРАЖЕНИЕ*

        📊 *Результаты:*
        • Время: {race_time:.2f} сек.
        • Реакция: {reaction_time:.2f} сек.
        • Причина: {reaction_text.split('!')[0]}
        
        💡 *Совет:* Тренируйтесь для улучшения реакции!
        • 💰 +{reward} кредитов (утешительный приз)
        """
        
        db.update_balance(user_id, reward)
        db.update_user(user_id, losses=user_data['losses'] + 1, 
                      races_total=user_data['races_total'] + 1)
    
    db.update_last_seen(user_id)
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        result_text,
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
    
    db.update_last_seen(user_id)
    
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
    
    db.update_last_seen(user_id)
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    hp_boost = db.get_total_hp_boost(user_id, current_car['id']) if current_car else 0
    
    menu_text = f"""
    🏠 *ГЛАВНОЕ МЕНЮ*

    👤 *{user_data['nickname']}*
    ⭐ Рейтинг: {user_data['rating']} (PVP)
    💰 Баланс: {user_data['balance']}
    👥 Подписчики: {user_data['followers']}
    🏆 Побед: {user_data['wins']} | Поражений: {user_data['losses']}
    
    🚗 *Текущая машина:* {current_car['name'] if current_car else 'Нет'}
    💪 {current_car['horse_power'] + hp_boost if current_car else 0} л.с. (+{hp_boost} тюнинг)
    
    *Выберите действие:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🏎️ Быстрая гонка", callback_data="quick_race"),
         InlineKeyboardButton("⚔️ Дуэль", callback_data="duel_menu")],
        [InlineKeyboardButton("🚗 Мой гараж", callback_data="my_garage"),
         InlineKeyboardButton("🏪 Магазин машин", callback_data="car_shop")],
        [InlineKeyboardButton("⚙️ Магазин запчастей", callback_data="parts_shop"),
         InlineKeyboardButton("🏆 Топы", callback_data="top_menu")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="enter_promo")]
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
    🏎️ *БЫСТРАЯ ГОНКА (Против бота)*

    Правила:
    • Дистанция: 1000 метров
    • Соперник: ИИ бот
    • Награда: Кредиты + Подписчики
    
    *НЕ влияет на рейтинг!*
    
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

async def duel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duel_info = """
    ⚔️ *ДУЭЛИ С ИГРОКАМИ*

    Правила дуэлей:
    • Вызов игрока по username или ID
    • Старт через 5-6 секунд (как в обучении)
    • Победа даёт рейтинг и деньги
    • Поражение отнимает рейтинг
    
    Выберите действие:
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 Список активных игроков", callback_data="active_players")],
        [InlineKeyboardButton("🎲 Случайный соперник", callback_data="random_duel")],
        [InlineKeyboardButton("📝 Вызвать по username", callback_data="duel_by_username")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        duel_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.DUEL_INVITE

async def active_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    players = db.get_active_users(20)
    
    if not players:
        await query.edit_message_text(
            "👥 *Нет активных игроков*\n\nПопробуйте позже или пригласите друзей!",
            parse_mode=ParseMode.MARKDOWN
        )
        return await duel_menu(update, context)
    
    players_text = "👥 *АКТИВНЫЕ ИГРОКИ*\n\n"
    
    for i, (user_id, nickname, rating, balance) in enumerate(players[:15], 1):
        players_text += f"{i}. *{nickname}*\n"
        players_text += f"   ⭐ {rating} | 💰 {balance}\n"
        players_text += f"   /duel_{user_id}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к дуэлям", callback_data="duel_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        players_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def random_duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    players = db.get_active_users(50)
    
    # Исключаем себя из списка
    players = [p for p in players if p[0] != user_id]
    
    if not players:
        await query.edit_message_text(
            "😔 *Не найдено подходящих соперников*\n\nПопробуйте позже!",
            parse_mode=ParseMode.MARKDOWN
        )
        return await duel_menu(update, context)
    
    opponent = random.choice(players)
    opponent_id, opponent_name, opponent_rating, _ = opponent
    
    # Создаем дуэль
    duel_id = db.create_duel(user_id, opponent_id)
    duel_invites[duel_id] = {
        'challenger_id': user_id,
        'opponent_id': opponent_id,
        'created_at': time.time()
    }
    
    await query.edit_message_text(
        f"🎯 *Вызов отправлен!*\n\n"
        f"Соперник: *{opponent_name}*\n"
        f"Рейтинг: ⭐ {opponent_rating}\n\n"
        f"Ожидание ответа...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем уведомление сопернику
    try:
        await context.bot.send_message(
            chat_id=opponent_id,
            text=f"⚔️ *ВЫЗОВ НА ДУЭЛЬ!*\n\n"
                 f"Игрок *{update.effective_user.first_name}* вызывает вас на дуэль!\n\n"
                 f"Принять вызов?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Принять", callback_data=f"accept_duel_{duel_id}"),
                 InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_duel_{duel_id}")]
            ])
        )
    except:
        await query.message.reply_text(
            "⚠️ *Не удалось отправить вызов*\n\n"
            "Соперник заблокировал бота или не активировал его.",
            parse_mode=ParseMode.MARKDOWN
        )
        db.update_duel(duel_id, status='declined')
        return await duel_menu(update, context)
    
    # Ждем ответа 60 секунд
    await asyncio.sleep(60)
    
    if duel_id in duel_invites:
        duel = db.get_duel(duel_id)
        if duel and duel['status'] == 'pending':
            db.update_duel(duel_id, status='timeout')
            del duel_invites[duel_id]
            await query.message.reply_text(
                "⏰ *Время вышло!*\n\nСоперник не ответил на вызов.",
                parse_mode=ParseMode.MARKDOWN
            )

async def duel_by_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 *ВЫЗОВ ПО USERNAME*\n\n"
        "Отправьте username игрока (например, @username или просто username)\n\n"
        "Пример: @username или username",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return States.DUEL_WAITING

async def process_duel_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().replace('@', '')
    user_id = update.effective_user.id
    
    # Поиск пользователя по username
    cursor = db.conn.cursor()
    cursor.execute('SELECT user_id, nickname, rating FROM users WHERE username = ? OR nickname = ?', 
                  (username, username))
    opponent = cursor.fetchone()
    
    if not opponent:
        await update.message.reply_text(
            "❌ *Игрок не найден*\n\n"
            "Проверьте правильность username и попробуйте снова.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await duel_menu(update, context)
    
    opponent_id, opponent_name, opponent_rating = opponent
    
    if opponent_id == user_id:
        await update.message.reply_text(
            "😅 *Нельзя вызвать самого себя!*\n\n"
            "Попробуйте вызвать другого игрока.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await duel_menu(update, context)
    
    # Создаем дуэль
    duel_id = db.create_duel(user_id, opponent_id)
    duel_invites[duel_id] = {
        'challenger_id': user_id,
        'opponent_id': opponent_id,
        'created_at': time.time()
    }
    
    await update.message.reply_text(
        f"🎯 *Вызов отправлен!*\n\n"
        f"Соперник: *{opponent_name}*\n"
        f"Рейтинг: ⭐ {opponent_rating}\n\n"
        f"Ожидание ответа...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем уведомление сопернику
    try:
        await context.bot.send_message(
            chat_id=opponent_id,
            text=f"⚔️ *ВЫЗОВ НА ДУЭЛЬ!*\n\n"
                 f"Игрок *{update.effective_user.first_name}* вызывает вас на дуэль!\n\n"
                 f"Принять вызов?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Принять", callback_data=f"accept_duel_{duel_id}"),
                 InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_duel_{duel_id}")]
            ])
        )
    except:
        await update.message.reply_text(
            "⚠️ *Не удалось отправить вызов*\n\n"
            "Соперник заблокировал бота или не активировал его.",
            parse_mode=ParseMode.MARKDOWN
        )
        db.update_duel(duel_id, status='declined')
        return await duel_menu(update, context)
    
    # Ждем ответа 60 секунд
    await asyncio.sleep(60)
    
    if duel_id in duel_invites:
        duel = db.get_duel(duel_id)
        if duel and duel['status'] == 'pending':
            db.update_duel(duel_id, status='timeout')
            del duel_invites[duel_id]
            await update.message.reply_text(
                "⏰ *Время вышло!*\n\nСоперник не ответил на вызов.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    return await main_menu(update, context)

async def handle_duel_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    duel_id = int(data.split('_')[2])
    action = data.split('_')[1]
    
    duel = db.get_duel(duel_id)
    if not duel or duel['status'] != 'pending':
        await query.edit_message_text(
            "❌ *Вызов устарел или отменен*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if action == 'decline':
        db.update_duel(duel_id, status='declined')
        await query.edit_message_text(
            "❌ *Вызов отклонен*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Уведомляем вызывающего
        try:
            await context.bot.send_message(
                chat_id=duel['challenger_id'],
                text="❌ *Ваш вызов отклонен*",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        if duel_id in duel_invites:
            del duel_invites[duel_id]
        return
    
    # Принятие дуэли
    db.update_duel(duel_id, status='accepted')
    
    # Получаем информацию об игроках
    challenger = db.get_user(duel['challenger_id'])
    opponent = db.get_user(duel['opponent_id'])
    
    challenger_car = db.get_car_info(challenger['current_car'])
    opponent_car = db.get_car_info(opponent['current_car'])
    
    challenger_hp_boost = db.get_total_hp_boost(challenger['user_id'], challenger_car['id'])
    opponent_hp_boost = db.get_total_hp_boost(opponent['user_id'], opponent_car['id'])
    
    # Подготовка к дуэли
    await query.edit_message_text(
        f"✅ *ДУЭЛЬ ПРИНЯТА!*\n\n"
        f"⚔️ *{challenger['nickname']}* vs *{opponent['nickname']}*\n\n"
        f"🚗 {challenger_car['name']} ({challenger_car['horse_power'] + challenger_hp_boost} л.с.)\n"
        f"🚗 {opponent_car['name']} ({opponent_car['horse_power'] + opponent_hp_boost} л.с.)\n\n"
        f"Готовы к гонке?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Готов", callback_data=f"duel_ready_{duel_id}")]
        ])
    )
    
    # Уведомляем вызывающего
    try:
        await context.bot.send_message(
            chat_id=duel['challenger_id'],
            text=f"✅ *Соперник принял вызов!*\n\n"
                 f"⚔️ *{challenger['nickname']}* vs *{opponent['nickname']}*\n\n"
                 f"Готовы к гонке?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Готов", callback_data=f"duel_ready_{duel_id}")]
            ])
        )
    except:
        pass
    
    if duel_id in duel_invites:
        del duel_invites[duel_id]

async def duel_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duel_id = int(query.data.split('_')[2])
    user_id = update.effective_user.id
    
    duel = db.get_duel(duel_id)
    if not duel or duel['status'] != 'accepted':
        await query.edit_message_text(
            "❌ *Дуэль отменена*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Сохраняем кто готов
    if 'ready_players' not in context.bot_data:
        context.bot_data['ready_players'] = {}
    
    if duel_id not in context.bot_data['ready_players']:
        context.bot_data['ready_players'][duel_id] = []
    
    if user_id not in context.bot_data['ready_players'][duel_id]:
        context.bot_data['ready_players'][duel_id].append(user_id)
    
    await query.edit_message_text(
        "✅ *Вы готовы!*\n\nОжидание второго игрока...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Проверяем готовы ли оба
    if len(context.bot_data['ready_players'][duel_id]) == 2:
        # Запускаем дуэль
        await start_duel_race(update, context, duel_id)

async def start_duel_race(update: Update, context: ContextTypes.DEFAULT_TYPE, duel_id: int):
    duel = db.get_duel(duel_id)
    if not duel:
        return
    
    challenger = db.get_user(duel['challenger_id'])
    opponent = db.get_user(duel['opponent_id'])
    
    # Уведомляем обаих о начале гонки
    race_info = """
    ⚔️ *ДУЭЛЬ НАЧИНАЕТСЯ!*

    Правила старта:
    • Нажмите "Готов" когда будете готовы
    • Через 5 секунд появится кнопка "Старт"
    • Нажмите "Старт" в промежутке 5-6 секунд
    • Фальстарт (<5 сек) или поздний старт (>6 сек) = проигрыш
    
    Удачи!
    """
    
    keyboard = [[InlineKeyboardButton("✅ Готов к дуэли", callback_data=f"duel_start_{duel_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем обоим игрокам
    try:
        await context.bot.send_message(
            chat_id=duel['challenger_id'],
            text=race_info,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass
    
    try:
        await context.bot.send_message(
            chat_id=duel['opponent_id'],
            text=race_info,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass
    
    # Очищаем список готовых
    if duel_id in context.bot_data.get('ready_players', {}):
        del context.bot_data['ready_players'][duel_id]

async def duel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duel_id = int(query.data.split('_')[2])
    user_id = update.effective_user.id
    
    duel = db.get_duel(duel_id)
    if not duel:
        return
    
    # Сохраняем время старта для каждого игрока
    if 'duel_start_times' not in context.bot_data:
        context.bot_data['duel_start_times'] = {}
    
    context.bot_data['duel_start_times'][duel_id] = {
        user_id: time.time()
    }
    
    await query.edit_message_text(
        "⏱️ *Ждем 5 секунд...*\n\n"
        "Приготовьтесь нажимать 'Старт' между 5 и 6 секундами!\n\n"
        "Старт через: 5...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    for i in range(4, 0, -1):
        await asyncio.sleep(1)
        try:
            await query.edit_message_text(
                f"⏱️ *Ждем 5 секунд...*\n\n"
                f"Приготовьтесь нажимать 'Старт' между 5 и 6 секундами!\n\n"
                f"Старт через: {i}...",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    await asyncio.sleep(1)
    
    keyboard = [[InlineKeyboardButton("🏁 СТАРТ ДУЭЛИ", callback_data=f"duel_race_go_{duel_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🚦 *СТАРТ!* Нажимайте между 5 и 6 секундами!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def duel_race_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duel_id = int(query.data.split('_')[3])
    user_id = update.effective_user.id
    
    duel = db.get_duel(duel_id)
    if not duel:
        return
    
    # Получаем время реакции
    start_time = context.bot_data.get('duel_start_times', {}).get(duel_id, {}).get(user_id)
    if not start_time:
        reaction_time = random.uniform(5.0, 6.0)
    else:
        reaction_time = time.time() - start_time
    
    # Определяем победителя на основе времени реакции
    # 5-6 секунд - успех, иначе проигрыш
    if 5.0 <= reaction_time <= 6.0:
        is_success = True
        reaction_text = "🎯 Отличный старт!"
    else:
        is_success = False
        if reaction_time < 5.0:
            reaction_text = "🚨 Фальстарт!"
        else:
            reaction_text = "🐌 Поздний старт!"
    
    # Сохраняем результат
    if 'duel_results' not in context.bot_data:
        context.bot_data['duel_results'] = {}
    
    if duel_id not in context.bot_data['duel_results']:
        context.bot_data['duel_results'][duel_id] = {}
    
    context.bot_data['duel_results'][duel_id][user_id] = {
        'reaction_time': reaction_time,
        'success': is_success
    }
    
    await query.edit_message_text(
        f"{reaction_text}\nВремя реакции: {reaction_time:.2f} сек.\n\n"
        f"🏎️ Машина ускоряется...\n\n"
        f"Ожидание соперника...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Проверяем оба ли игрока закончили
    results = context.bot_data['duel_results'].get(duel_id, {})
    if len(results) == 2:
        # Определяем победителя
        await determine_duel_winner(update, context, duel_id)

async def determine_duel_winner(update: Update, context: ContextTypes.DEFAULT_TYPE, duel_id: int):
    duel = db.get_duel(duel_id)
    if not duel:
        return
    
    results = context.bot_data['duel_results'].get(duel_id, {})
    
    challenger_id = duel['challenger_id']
    opponent_id = duel['opponent_id']
    
    challenger_result = results.get(challenger_id, {'success': False, 'reaction_time': 10})
    opponent_result = results.get(opponent_id, {'success': False, 'reaction_time': 10})
    
    # Определяем победителя
    if challenger_result['success'] and not opponent_result['success']:
        winner_id = challenger_id
        loser_id = opponent_id
    elif not challenger_result['success'] and opponent_result['success']:
        winner_id = opponent_id
        loser_id = challenger_id
    elif challenger_result['success'] and opponent_result['success']:
        # Оба успешно стартовали - победитель с лучшим временем
        if challenger_result['reaction_time'] < opponent_result['reaction_time']:
            winner_id = challenger_id
            loser_id = opponent_id
        else:
            winner_id = opponent_id
            loser_id = challenger_id
    else:
        # Оба проиграли - ничья
        winner_id = None
    
    # Обновляем дуэль
    if winner_id:
        db.update_duel(duel_id, status='completed', winner_id=winner_id)
        
        winner = db.get_user(winner_id)
        loser = db.get_user(loser_id)
        
        # Награды за победу в PVP
        rating_gain = 25
        money_reward = random.randint(3000, 8000)
        followers_gain = random.randint(100, 300)
        
        # Штраф за поражение
        rating_loss = 15
        money_loss = random.randint(500, 1500)
        
        # Обновляем статистику
        db.update_user(winner_id, 
                      rating=winner['rating'] + rating_gain,
                      balance=winner['balance'] + money_reward,
                      followers=winner['followers'] + followers_gain,
                      wins=winner['wins'] + 1,
                      races_total=winner['races_total'] + 1)
        
        db.update_user(loser_id,
                      rating=max(0, loser['rating'] - rating_loss),
                      balance=loser['balance'] - money_loss,
                      losses=loser['losses'] + 1,
                      races_total=loser['races_total'] + 1)
        
        result_text = f"""
        🏆 *ДУЭЛЬ ЗАВЕРШЕНА!*

        🥇 *ПОБЕДИТЕЛЬ:* {winner['nickname']}
        🥈 *ПРОИГРАВШИЙ:* {loser['nickname']}
        
        📊 *Результаты:*
        • {winner['nickname']}: {results[winner_id]['reaction_time']:.2f} сек.
        • {loser['nickname']}: {results[loser_id]['reaction_time']:.2f} сек.
        
        🎁 *Награды победителя:*
        • ⭐ +{rating_gain} рейтинга
        • 💰 +{money_reward} кредитов
        • 👥 +{followers_gain} подписчиков
        
        📉 *Потери проигравшего:*
        • ⭐ -{rating_loss} рейтинга
        • 💰 -{money_loss} кредитов
        """
    else:
        db.update_duel(duel_id, status='draw')
        
        challenger = db.get_user(challenger_id)
        opponent = db.get_user(opponent_id)
        
        # Ничья - небольшие награды обоим
        money_reward = random.randint(500, 1000)
        
        db.update_balance(challenger_id, money_reward)
        db.update_balance(opponent_id, money_reward)
        
        result_text = f"""
        🤝 *НИЧЬЯ!*

        Оба игрока совершили ошибку на старте!
        
        📊 *Результаты:*
        • {challenger['nickname']}: {results[challenger_id]['reaction_time']:.2f} сек.
        • {opponent['nickname']}: {results[opponent_id]['reaction_time']:.2f} сек.
        
        🎁 *Утешительные призы:*
        • 💰 +{money_reward} кредитов каждому
        """
    
    # Отправляем результат обоим игрокам
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=challenger_id,
            text=result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass
    
    try:
        await context.bot.send_message(
            chat_id=opponent_id,
            text=result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass
    
    # Очищаем данные дуэли
    if duel_id in context.bot_data.get('duel_start_times', {}):
        del context.bot_data['duel_start_times'][duel_id]
    if duel_id in context.bot_data.get('duel_results', {}):
        del context.bot_data['duel_results'][duel_id]

async def my_garage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    garage_cars = db.get_user_garage(user_id)
    db.update_last_seen(user_id)
    
    if not garage_cars:
        await query.edit_message_text(
            "🚗 *Ваш гараж пуст!*\nКупите свою первую машину в магазине!",
            parse_mode=ParseMode.MARKDOWN
        )
        return await main_menu(update, context)
    
    garage_text = "🚗 *ВАШ ГАРАЖ*\n\n"
    
    for i, car in enumerate(garage_cars, 1):
        status = "✅ Активна" if car[9] == 1 else "⚪ Не активна"
        hp_boost = db.get_total_hp_boost(user_id, car[0])
        total_hp = car[5] + hp_boost
        
        garage_text += f"{i}. *{car[1]}*\n"
        garage_text += f"   💪 {total_hp} л.с. ({car[5]} + {hp_boost})\n"
        garage_text += f"   ⏱️ {car[6]} сек. 0-100\n"
        garage_text += f"   {status}\n\n"
    
    # Установленные запчасти
    if garage_cars:
        active_car_id = next((car[0] for car in garage_cars if car[9] == 1), garage_cars[0][0])
        installed_parts = db.get_installed_parts(user_id, active_car_id)
        
        if installed_parts:
            garage_text += "⚙️ *Установленные запчасти:*\n"
            for part in installed_parts:
                garage_text += f"• {part['name']} (+{part['hp_boost']} л.с.)\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Сменить машину", callback_data="change_car")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
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
    db.update_last_seen(update.effective_user.id)
    
    shop_text = """
    🏪 *МАГАЗИН МАШИН*

    Выберите регион:
    
    🇪🇺 *Европейский автопром* - Немецкое качество, Итальянский стиль
    🇯🇵 *Азиатский автопром* - Японская надежность, Корейские технологии  
    🇺🇸 *Американский автопром* - Мощные маслкары, Внедорожники
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
    
    european_brands = ["Volkswagen", "Mercedes", "BMW", "Audi", "Porsche", 
                      "Ferrari", "Lamborghini", "Bugatti", "Rolls-Royce", 
                      "Bentley", "McLaren", "Jaguar", "Volvo"]
    
    keyboard = []
    for i in range(0, len(european_brands), 3):
        row = []
        for j in range(3):
            if i + j < len(european_brands):
                row.append(InlineKeyboardButton(european_brands[i+j], callback_data=f"brand_{european_brands[i+j]}"))
        keyboard.append(row)
    
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
    
    asian_brands = ["Toyota", "Honda", "Nissan", "Mazda", "Mitsubishi",
                   "Subaru", "Hyundai", "Kia", "Lexus", "Suzuki"]
    
    keyboard = []
    for i in range(0, len(asian_brands), 3):
        row = []
        for j in range(3):
            if i + j < len(asian_brands):
                row.append(InlineKeyboardButton(asian_brands[i+j], callback_data=f"brand_{asian_brands[i+j]}"))
        keyboard.append(row)
    
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
    
    american_brands = ["Ford", "Chevrolet", "Dodge", "Tesla", "Jeep",
                      "Cadillac", "Ram", "GMC", "Buick", "Lincoln"]
    
    keyboard = []
    for i in range(0, len(american_brands), 3):
        row = []
        for j in range(3):
            if i + j < len(american_brands):
                row.append(InlineKeyboardButton(american_brands[i+j], callback_data=f"brand_{american_brands[i+j]}"))
        keyboard.append(row)
    
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
    db.update_last_seen(user_id)
    
    await query.edit_message_text(
        f"🎉 *Поздравляем с покупкой!*\n\n"
        f"Вы приобрели *{car['brand']} {car['name']}*\n"
        f"💸 Списано: {car['price']} кредитов\n"
        f"💰 Ваш баланс: {user_data['balance'] - car['price']} кредитов",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(2)
    return await main_menu(update, context)

async def parts_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.update_last_seen(update.effective_user.id)
    
    parts_text = """
    ⚙️ *МАГАЗИН ЗАПЧАСТЕЙ*

    Увеличивайте мощность вашей машины с помощью тюнинга!
    
    *Доступные категории:*
    
    🚀 *Двигатели* - Значительно увеличивают мощность
    🌀 *Турбины* - Добавляют турбонаддув
    💨 *Выхлопы* - Улучшают отвод газов
    🌡️ *Радиаторы* - Улучшают охлаждение
    💥 *Закись азота* - Временный буст мощности
    🔄 *Подвеска* - Улучшают управляемость
    🛞 *Покрышки* - Улучшают сцепление
    
    Выберите категорию:
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 Двигатели", callback_data="parts_category_engine"),
         InlineKeyboardButton("🌀 Турбины", callback_data="parts_category_turbo")],
        [InlineKeyboardButton("💨 Выхлопы", callback_data="parts_category_exhaust"),
         InlineKeyboardButton("🌡️ Радиаторы", callback_data="parts_category_radiator")],
        [InlineKeyboardButton("💥 Закись азота", callback_data="parts_category_nitro"),
         InlineKeyboardButton("🔄 Подвеска", callback_data="parts_category_suspension")],
        [InlineKeyboardButton("🛞 Покрышки", callback_data="parts_category_tires"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        parts_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.PARTS_SHOP

async def show_parts_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category = query.data.split("_")[2]
    context.user_data['parts_category'] = category
    context.user_data['part_index'] = 0
    
    parts = db.get_parts_by_category(category)
    
    if not parts:
        await query.edit_message_text(
            f"🚫 Запчасти категории {category} временно отсутствуют.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await parts_shop(update, context)
    
    context.user_data['category_parts'] = parts
    return await show_part_item(update, context)

async def show_part_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = context.user_data.get('category_parts', [])
    if not parts:
        return await parts_shop(update, context)
    
    index = context.user_data.get('part_index', 0)
    part = parts[index]
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    
    category_names = {
        'engine': '🚀 Двигатель',
        'turbo': '🌀 Турбина',
        'exhaust': '💨 Выхлоп',
        'radiator': '🌡️ Радиатор',
        'nitro': '💥 Закись азота',
        'suspension': '🔄 Подвеска',
        'tires': '🛞 Покрышки'
    }
    
    part_text = f"""
    {category_names.get(part['category'], '⚙️')} *{part['name']}*
    
    🏷️ *Бренд:* {part['brand']}
    💪 *Увеличение мощности:* +{part['hp_boost']} л.с.
    
    💰 *Цена:* {part['price']} кредитов
    📝 *{part['description']}*
    
    *Для машины:* {current_car['name'] if current_car else 'Нет машины'}
    *{index + 1}/{len(parts)}*
    """
    
    keyboard = []
    nav_buttons = []
    
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="part_prev"))
    
    if not current_car:
        nav_buttons.append(InlineKeyboardButton("🚫 Нет машины", callback_data="no_car"))
    elif user_data['balance'] >= part['price']:
        nav_buttons.append(InlineKeyboardButton("🛒 Купить и установить", callback_data=f"buy_part_{part['id']}"))
    else:
        nav_buttons.append(InlineKeyboardButton("💸 Недостаточно средств", callback_data="no_money"))
    
    if index < len(parts) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="part_next"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="parts_shop")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        part_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.PARTS_LIST

async def navigate_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "part_next":
        context.user_data['part_index'] += 1
    elif query.data == "part_prev":
        context.user_data['part_index'] -= 1
    
    return await show_part_item(update, context)

async def buy_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    part_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data['current_car']:
        await query.answer("🚫 У вас нет машины!", show_alert=True)
        return
    
    # Находим запчасть
    parts = context.user_data.get('category_parts', [])
    part = next((p for p in parts if p['id'] == part_id), None)
    
    if not part:
        await query.answer("❌ Запчасть не найдена!", show_alert=True)
        return
    
    if user_data['balance'] < part['price']:
        await query.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    # Устанавливаем запчасть
    if db.install_part(user_id, user_data['current_car'], part_id):
        db.update_balance(user_id, -part['price'])
        db.update_last_seen(user_id)
        
        await query.edit_message_text(
            f"✅ *Запчасть установлена!*\n\n"
            f"Вы установили *{part['name']}* на свою машину\n"
            f"💪 +{part['hp_boost']} л.с. к мощности\n"
            f"💸 Списано: {part['price']} кредитов\n"
            f"💰 Ваш баланс: {user_data['balance'] - part['price']} кредитов",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            "❌ *Ошибка установки!*\n\n"
            "Не удалось установить запчасть.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    await asyncio.sleep(2)
    return await parts_shop(update, context)

async def top_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.update_last_seen(update.effective_user.id)
    
    top_text = """
    🏆 *ТОПЫ ИГРОКОВ*

    Выберите тип топа:
    
    ⭐ *Рейтинг* - Лучшие по PVP рейтингу
    💰 *Деньги* - Самые богатые игроки
    🏆 *Победы* - Больше всего побед
    👥 *Подписчики* - Самые популярные
    💪 *Мощность* - Самые мощные машины
    """
    
    keyboard = [
        [InlineKeyboardButton("⭐ Рейтинг", callback_data="top_rating"),
         InlineKeyboardButton("💰 Деньги", callback_data="top_money")],
        [InlineKeyboardButton("🏆 Победы", callback_data="top_wins"),
         InlineKeyboardButton("👥 Подписчики", callback_data="top_followers")],
        [InlineKeyboardButton("💪 Мощность", callback_data="top_hp"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.TOP_MENU

async def show_top_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_players = db.get_top_rating(10)
    
    top_text = "⭐ *ТОП ПО РЕЙТИНГУ (PVP)*\n\n"
    
    for i, (nickname, rating, wins) in enumerate(top_players, 1):
        top_text += f"{i}. *{nickname}*\n"
        top_text += f"   ⭐ {rating} | 🏆 {wins} побед\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к топам", callback_data="top_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_top_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_players = db.get_top_money(10)
    
    top_text = "💰 *ТОП ПО ДЕНЬГАМ*\n\n"
    
    for i, (nickname, balance, followers) in enumerate(top_players, 1):
        top_text += f"{i}. *{nickname}*\n"
        top_text += f"   💰 {balance} | 👥 {followers}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к топам", callback_data="top_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_top_wins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_players = db.get_top_wins(10)
    
    top_text = "🏆 *ТОП ПО ПОБЕДАМ*\n\n"
    
    for i, (nickname, wins, rating) in enumerate(top_players, 1):
        top_text += f"{i}. *{nickname}*\n"
        top_text += f"   🏆 {wins} побед | ⭐ {rating}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к топам", callback_data="top_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_top_followers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_players = db.get_top_followers(10)
    
    top_text = "👥 *ТОП ПО ПОДПИСЧИКАМ*\n\n"
    
    for i, (nickname, followers, wins) in enumerate(top_players, 1):
        top_text += f"{i}. *{nickname}*\n"
        top_text += f"   👥 {followers} | 🏆 {wins} побед\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к топам", callback_data="top_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_top_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_players = db.get_top_hp(10)
    
    top_text = "💪 *ТОП ПО МОЩНОСТИ МАШИН*\n\n"
    
    for i, (nickname, hp, wins) in enumerate(top_players, 1):
        top_text += f"{i}. *{nickname}*\n"
        top_text += f"   💪 {hp} л.с. | 🏆 {wins} побед\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к топам", callback_data="top_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        top_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def enter_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.update_last_seen(update.effective_user.id)
    
    await query.edit_message_text(
        "🎁 *ВВЕДИТЕ ПРОМОКОД*\n\n"
        "Отправьте промокод в чат:\n\n"
        "*Пример:* WELCOME2024\n"
        "*Активные промокоды:*\n"
        "• WELCOME2024 - 5000 кредитов\n"
        "• RACINGBOT - 3000 кредитов\n"
        "• SPEED - 2000 кредитов\n"
        "• FOLLOWERS - 150 подписчиков\n"
        "• RICH - 10000 кредитов",
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
            f"Осталось использований: {promo['max_uses'] - promo['used_count']}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "❌ *Неверный промокод!*\n\n"
            "Возможные причины:\n"
            "• Промокод не существует\n"
            "• Вы уже использовали этот промокод\n"
            "• Лимит использований исчерпан\n"
            "• Срок действия истек",
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
        
        cursor = db.conn.cursor()
        expires_at = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT OR REPLACE INTO promocodes VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, reward_type, reward_value, max_uses, 0, expires_at))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Промокод {code} добавлен!")
    
    elif cmd == "ban" and len(command) == 3:
        target_id = int(command[2])
        db.update_user(target_id, is_banned=1)
        await update.message.reply_text(f"✅ Пользователь {target_id} забанен!")
    
    elif cmd == "unban" and len(command) == 3:
        target_id = int(command[2])
        db.update_user(target_id, is_banned=0)
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен!")
    
    elif cmd == "addmoney" and len(command) == 4:
        target_id = int(command[2])
        amount = int(command[3])
        db.update_balance(target_id, amount)
        await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} кредитов!")
    
    elif cmd == "addfollowers" and len(command) == 4:
        target_id = int(command[2])
        amount = int(command[3])
        user_data = db.get_user(target_id)
        if user_data:
            db.update_user(target_id, followers=user_data['followers'] + amount)
            await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} подписчиков!")
    
    elif cmd == "stats":
        cursor = db.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
        banned_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(wins) FROM users')
        total_wins = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM duels WHERE status = "completed"')
        total_duels = cursor.fetchone()[0]
        
        stats_text = f"""
        📊 *СТАТИСТИКА БОТА*
        
        👥 Пользователи: {total_users}
        ⛔ Забанено: {banned_users}
        💰 Общий баланс: {total_balance}
        🏆 Всего побед: {total_wins}
        ⚔️ Проведено дуэлей: {total_duels}
        
        *Активные промокоды:*
        """
        
        cursor.execute('SELECT code, reward_value, max_uses, used_count FROM promocodes')
        promos = cursor.fetchall()
        
        for code, value, max_uses, used in promos:
            stats_text += f"• {code}: {used}/{max_uses} использований\n"
        
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
    2. Участвуйте в гонках против ботов (для заработка)
    3. Вызывайте игроков на дуэли (для рейтинга)
    4. Покупайте запчасти для улучшения машины
    5. Соревнуйтесь за место в топе
    
    *Особенности:*
    • Рейтинг начисляется ТОЛЬКО за победы в PVP
    • Время реакции 5-6 секунд - успешный старт
    • Запчасти увеличивают мощность машины
    • Дуэли - основной способ повышения рейтинга
    
    *Управление:*
    • Используйте кнопки под сообщениями
    • Вводите промокоды в чат
    • Для вызова на дуэль: /duel_username или через меню
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    hp_boost = db.get_total_hp_boost(user_id, current_car['id']) if current_car else 0
    
    profile_text = f"""
    👤 *ПРОФИЛЬ ИГРОКА*
    
    *Основное:*
    • Имя: {user_data['nickname']}
    • Рейтинг PVP: {user_data['rating']} ⭐
    • Баланс: {user_data['balance']} 💰
    • Подписчики: {user_data['followers']} 👥
    
    *Статистика:*
    • Побед: {user_data['wins']} 🏆
    • Поражений: {user_data['losses']} 💔
    • Всего гонок: {user_data['races_total']} 🏎️
    • Winrate PVP: {(user_data['wins'] / max(user_data['wins'] + user_data['losses'], 1) * 100):.1f}%
    
    *Текущая машина:*
    • {current_car['name'] if current_car else 'Нет машины'}
    • Мощность: {current_car['horse_power'] + hp_boost if current_car else 0} л.с. (+{hp_boost})
    • Разгон 0-100: {current_car['acceleration_100'] if current_car else 0} сек.
    
    *Достижения:*
    {get_achievements(user_data)}
    """
    
    await update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)

def get_achievements(user_data):
    achievements = []
    
    if user_data['wins'] >= 10:
        achievements.append("🏆 10 побед")
    if user_data['wins'] >= 50:
        achievements.append("🏆 50 побед")
    if user_data['rating'] >= 1500:
        achievements.append("⭐ Рейтинг 1500+")
    if user_data['balance'] >= 100000:
        achievements.append("💰 100k кредитов")
    if user_data['followers'] >= 1000:
        achievements.append("👥 1000 подписчиков")
    
    if achievements:
        return "\n".join(f"• {achievement}" for achievement in achievements)
    return "• Нет достижений"

async def handle_duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команд вида /duel_123456789"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text.startswith('/duel_'):
        try:
            opponent_id = int(text.split('_')[1])
            
            opponent = db.get_user(opponent_id)
            if not opponent:
                await update.message.reply_text("❌ Игрок не найден!")
                return
            
            if opponent_id == user_id:
                await update.message.reply_text("😅 Нельзя вызвать самого себя!")
                return
            
            # Создаем дуэль
            duel_id = db.create_duel(user_id, opponent_id)
            duel_invites[duel_id] = {
                'challenger_id': user_id,
                'opponent_id': opponent_id,
                'created_at': time.time()
            }
            
            await update.message.reply_text(
                f"🎯 *Вызов отправлен!*\n\n"
                f"Соперник: *{opponent['nickname']}*\n"
                f"Рейтинг: ⭐ {opponent['rating']}\n\n"
                f"Ожидание ответа...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Отправляем уведомление сопернику
            try:
                await context.bot.send_message(
                    chat_id=opponent_id,
                    text=f"⚔️ *ВЫЗОВ НА ДУЭЛЬ!*\n\n"
                         f"Игрок *{update.effective_user.first_name}* вызывает вас на дуэль!\n\n"
                         f"Принять вызов?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Принять", callback_data=f"accept_duel_{duel_id}"),
                         InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_duel_{duel_id}")]
                    ])
                )
            except:
                await update.message.reply_text(
                    "⚠️ *Не удалось отправить вызов*\n\n"
                    "Соперник заблокировал бота или не активировал его.",
                    parse_mode=ParseMode.MARKDOWN
                )
                db.update_duel(duel_id, status='declined')
        except ValueError:
            await update.message.reply_text("❌ Неверный формат команды. Используйте: /duel_123456789")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем ConversationHandler
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
                CallbackQueryHandler(duel_menu, pattern='^duel_menu$'),
                CallbackQueryHandler(my_garage, pattern='^my_garage$'),
                CallbackQueryHandler(car_shop, pattern='^car_shop$'),
                CallbackQueryHandler(parts_shop, pattern='^parts_shop$'),
                CallbackQueryHandler(top_menu, pattern='^top_menu$'),
                CallbackQueryHandler(enter_promo, pattern='^enter_promo$'),
                CallbackQueryHandler(admin_panel, pattern='^admin_panel$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
                CallbackQueryHandler(show_top_rating, pattern='^top_rating$'),
                CallbackQueryHandler(show_top_money, pattern='^top_money$'),
                CallbackQueryHandler(show_top_wins, pattern='^top_wins$'),
                CallbackQueryHandler(show_top_followers, pattern='^top_followers$'),
                CallbackQueryHandler(show_top_hp, pattern='^top_hp$'),
            ],
            States.DUEL_INVITE: [
                CallbackQueryHandler(active_players, pattern='^active_players$'),
                CallbackQueryHandler(random_duel, pattern='^random_duel$'),
                CallbackQueryHandler(duel_by_username, pattern='^duel_by_username$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.DUEL_WAITING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_duel_username),
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
            States.PARTS_SHOP: [
                CallbackQueryHandler(show_parts_category, pattern='^parts_category_'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.PARTS_LIST: [
                CallbackQueryHandler(navigate_parts, pattern='^part_(next|prev)$'),
                CallbackQueryHandler(buy_part, pattern='^buy_part_'),
                CallbackQueryHandler(parts_shop, pattern='^parts_shop$'),
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
    application.add_handler(MessageHandler(filters.Regex(r'^/duel_\d+'), handle_duel_command))
    
    # Обработчики дуэлей
    application.add_handler(CallbackQueryHandler(handle_duel_response, pattern='^accept_duel_'))
    application.add_handler(CallbackQueryHandler(handle_duel_response, pattern='^decline_duel_'))
    application.add_handler(CallbackQueryHandler(duel_ready, pattern='^duel_ready_'))
    application.add_handler(CallbackQueryHandler(duel_start, pattern='^duel_start_'))
    application.add_handler(CallbackQueryHandler(duel_race_go, pattern='^duel_race_go_'))
    
    # Запускаем бота
    print("=" * 60)
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎁 Промокоды: WELCOME2024, RACINGBOT, SPEED, FOLLOWERS, RICH")
    print("⚔️ Дуэли включены, время реакции: 5-6 секунд")
    print("💰 Улучшенная экономика, 5 видов топов")
    print("⚙️ Магазин запчастей, тюнинг машин")
    print("=" * 60)
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        pool_timeout=30,
        connect_timeout=30
    )

if __name__ == '__main__':
    main()
