#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPLETE TELEGRAM RACING BOT - FIXED VERSION
All cars, parts, and features included
"""

import asyncio
import json
import random
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, 
                     ReplyKeyboardMarkup, KeyboardButton, InputFile)
from telegram.ext import (Application, CommandHandler, MessageHandler, 
                         CallbackQueryHandler, ContextTypes, ConversationHandler,
                         filters)
from telegram.constants import ParseMode

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # Замените на ваш токен
# Список администраторов (добавьте свои ID)
ADMIN_IDS = [5189651311, 5887846215]  # Замените на реальные ID

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
    PARTS_CATEGORY = 16
    PARTS_LIST = 17
    BUY_CONFIRM = 18
    RACE_WAITING = 19
    RACE_START = 20

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.init_database()
        self.init_all_data()
    
    def get_connection(self):
        return sqlite3.connect('racing.db', check_same_thread=False)
    
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Гараж пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS garage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                car_id INTEGER,
                engine_id INTEGER DEFAULT 1,
                turbo_id INTEGER DEFAULT 1,
                exhaust_id INTEGER DEFAULT 1,
                radiator_id INTEGER DEFAULT 1,
                nitro_id INTEGER DEFAULT 1,
                suspension_id INTEGER DEFAULT 1,
                tires_id INTEGER DEFAULT 1,
                color TEXT DEFAULT 'Стандартный',
                is_active INTEGER DEFAULT 0,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Промокоды
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                reward_type TEXT,
                reward_value INTEGER,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Сообщения админу
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def init_all_data(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Создаем все таблицы с машинами и запчастями
        self.create_cars_tables(cursor)
        self.create_parts_tables(cursor)
        
        conn.commit()
        conn.close()
    
    def create_cars_tables(self, cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars_all (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                region TEXT,
                category TEXT,
                price INTEGER,
                horse_power INTEGER,
                acceleration_100 REAL,
                acceleration_200 REAL,
                acceleration_300 REAL,
                top_speed INTEGER,
                weight INTEGER,
                year INTEGER,
                image_path TEXT,
                description TEXT
            )
        ''')
        
        # Вставляем все машины
        self.insert_all_cars(cursor)
    
    def create_parts_tables(self, cursor):
        # Двигатели
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_engines (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                region TEXT,
                price INTEGER,
                hp_boost INTEGER,
                weight_change INTEGER,
                reliability INTEGER,
                fuel_consumption REAL,
                image_path TEXT
            )
        ''')
        
        # Турбины - ИСПРАВЛЕНО: 9 колонок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_turbos (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp_boost INTEGER,
                boost_pressure REAL,
                spool_time REAL,
                durability INTEGER,
                image_path TEXT
            )
        ''')
        
        # Выхлопы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_exhausts (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp_boost INTEGER,
                weight_saving INTEGER,
                sound_level INTEGER,
                material TEXT,
                image_path TEXT
            )
        ''')
        
        # Радиаторы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_radiators (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                cooling_boost INTEGER,
                weight INTEGER,
                size TEXT,
                material TEXT,
                image_path TEXT
            )
        ''')
        
        # Закись азота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_nitro (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp_boost INTEGER,
                duration_seconds INTEGER,
                refill_cost INTEGER,
                safety_level INTEGER,
                image_path TEXT
            )
        ''')
        
        # Подвеска
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_suspension (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                handling_boost INTEGER,
                comfort_change INTEGER,
                height_adjustable INTEGER,
                type TEXT,
                image_path TEXT
            )
        ''')
        
        # Покрышки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_tires (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                grip_boost INTEGER,
                wear_resistance INTEGER,
                wet_performance INTEGER,
                type TEXT,
                image_path TEXT
            )
        ''')
        
        # Вставляем все запчасти
        self.insert_all_parts(cursor)
    
    def insert_all_cars(self, cursor):
        # Стартовые машины
        starter_cars = [
            (1, 'Lancer X Sportback', 'Mitsubishi', 'asian', 'starter', 0, 180, 8.2, 16.5, 28.1, 210, 1450, 2007, 'cars/lancer_x.jpg', 'Надежный спортбек для начинающих'),
            (2, 'Opel Insignia OPC', 'Opel', 'european', 'starter', 0, 280, 6.0, 13.2, 22.4, 250, 1680, 2013, 'cars/opel_insignia.jpg', 'Мощный немецкий седан'),
            (3, 'Cadillac CTS', 'Cadillac', 'american', 'starter', 0, 320, 5.8, 12.8, 21.5, 240, 1750, 2008, 'cars/cadillac_cts.jpg', 'Американская мощь и комфорт')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', starter_cars)
        
        # Европейские машины (сокращенный список для примера)
        european_cars = [
            # Volkswagen
            (4, 'Volkswagen Golf', 'Volkswagen', 'european', 'hatchback', 15000, 150, 8.5, 18.2, 32.0, 210, 1280, 2020, 'cars/vw_golf.jpg', 'Иконка хетчбеков'),
            (5, 'Volkswagen Passat', 'Volkswagen', 'european', 'sedan', 20000, 190, 7.9, 16.8, 29.5, 230, 1480, 2019, 'cars/vw_passat.jpg', 'Просторный семейный седан'),
            # Mercedes-Benz
            (6, 'Mercedes-Benz C-Class', 'Mercedes-Benz', 'european', 'sedan', 35000, 255, 6.0, 13.5, 23.8, 250, 1650, 2021, 'cars/mercedes_c.jpg', 'Престиж и комфорт'),
            # BMW
            (7, 'BMW 5 Series', 'BMW', 'european', 'sedan', 45000, 248, 6.1, 13.8, 24.2, 250, 1670, 2021, 'cars/bmw_5.jpg', 'Водительское удовольствие'),
            # Audi
            (8, 'Audi A6', 'Audi', 'european', 'sedan', 48000, 265, 5.9, 13.3, 23.5, 250, 1710, 2021, 'cars/audi_a6.jpg', 'Современные технологии'),
            # Porsche
            (9, 'Porsche Panamera', 'Porsche', 'european', 'sedan', 85000, 330, 5.4, 11.9, 20.5, 285, 1870, 2022, 'cars/porsche_panamera.jpg', 'Спортивный седан'),
            # Ferrari
            (10, 'Ferrari Roma', 'Ferrari', 'european', 'coupe', 220000, 620, 3.4, 7.2, 12.8, 320, 1570, 2021, 'cars/ferrari_roma.jpg', 'Итальянская грация'),
            # Lamborghini
            (11, 'Lamborghini Huracán', 'Lamborghini', 'european', 'supercar', 250000, 640, 2.9, 6.4, 11.2, 325, 1420, 2022, 'cars/lambo_huracan.jpg', 'Испанский бык'),
            # Bugatti
            (12, 'Bugatti Chiron', 'Bugatti', 'european', 'hypercar', 3000000, 1500, 2.4, 4.9, 8.0, 420, 1990, 2022, 'cars/bugatti_chiron.jpg', 'Рекордсмен скорости'),
            # Rolls-Royce
            (13, 'Rolls-Royce Cullinan', 'Rolls-Royce', 'european', 'suv', 350000, 571, 5.2, 11.3, 19.8, 250, 2660, 2023, 'cars/rr_cullinan.jpg', 'Вершина роскоши'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', european_cars)
        
        # Азиатские машины (сокращенный список)
        asian_cars = [
            # Toyota
            (100, 'Toyota Corolla', 'Toyota', 'asian', 'sedan', 18000, 140, 9.2, 20.0, 35.2, 195, 1330, 2022, 'cars/toyota_corolla.jpg', 'Самый продаваемый автомобиль'),
            (101, 'Toyota Camry', 'Toyota', 'asian', 'sedan', 25000, 203, 7.9, 17.3, 30.5, 230, 1550, 2022, 'cars/toyota_camry.jpg', 'Надежный бизнес-седан'),
            (102, 'Toyota Supra A90', 'Toyota', 'asian', 'coupe', 55000, 340, 4.1, 9.0, 15.8, 250, 1540, 2022, 'cars/toyota_supra.jpg', 'Возрожденная легенда'),
            # Honda
            (103, 'Honda Civic Type R', 'Honda', 'asian', 'hatchback', 45000, 320, 5.4, 11.9, 20.9, 275, 1420, 2022, 'cars/honda_civic_r.jpg', 'Переднеприводный чемпион'),
            # Nissan
            (104, 'Nissan GT-R R35', 'Nissan', 'asian', 'supercar', 115000, 565, 2.9, 6.4, 11.2, 315, 1780, 2022, 'cars/nissan_gtr.jpg', 'Годзилла'),
            # Mazda
            (105, 'Mazda RX-7 FD', 'Mazda', 'asian', 'coupe', 45000, 255, 5.3, 11.7, 20.5, 250, 1260, 2002, 'cars/mazda_rx7.jpg', 'Роторная легенда'),
            # Subaru
            (106, 'Subaru Impreza WRX STI', 'Subaru', 'asian', 'sedan', 38000, 310, 5.2, 11.4, 20.0, 255, 1540, 2021, 'cars/subaru_sti.jpg', 'Раллийный чемпион'),
            # Mitsubishi
            (107, 'Mitsubishi Lancer Evolution X', 'Mitsubishi', 'asian', 'sedan', 35000, 303, 5.1, 11.2, 19.7, 250, 1610, 2015, 'cars/mitsubishi_evo.jpg', 'Последний Эво'),
            # Lexus
            (108, 'Lexus LC500', 'Lexus', 'asian', 'coupe', 95000, 477, 4.4, 9.7, 17.0, 270, 1930, 2022, 'cars/lexus_lc.jpg', 'Гранд-турер'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', asian_cars)
        
        # Американские машины (сокращенный список)
        american_cars = [
            # Ford
            (200, 'Ford Mustang GT', 'Ford', 'american', 'coupe', 45000, 460, 4.0, 8.8, 15.4, 250, 1730, 2022, 'cars/ford_mustang.jpg', 'Американская икона'),
            (201, 'Ford F-150 Raptor', 'Ford', 'american', 'pickup', 65000, 450, 5.1, 11.2, 19.7, 180, 2600, 2022, 'cars/ford_raptor.jpg', 'Внедорожный пикап'),
            # Chevrolet
            (202, 'Chevrolet Corvette C8', 'Chevrolet', 'american', 'supercar', 65000, 495, 2.9, 6.4, 11.2, 312, 1648, 2022, 'cars/chevrolet_corvette.jpg', 'Среднемоторная революция'),
            # Dodge
            (203, 'Dodge Challenger Hellcat', 'Dodge', 'american', 'coupe', 70000, 717, 3.6, 7.9, 13.9, 315, 2040, 2022, 'cars/dodge_challenger.jpg', 'Современный маслкар'),
            # Tesla
            (204, 'Tesla Model S Plaid', 'Tesla', 'american', 'sedan', 135000, 1020, 1.99, 4.3, 7.5, 322, 2190, 2022, 'cars/tesla_model_s.jpg', 'Электрический рекордсмен'),
            # Jeep
            (205, 'Jeep Wrangler Rubicon', 'Jeep', 'american', 'suv', 45000, 285, 7.5, 16.5, None, 180, 2040, 2022, 'cars/jeep_wrangler.jpg', 'Легенда бездорожья'),
            # Cadillac
            (206, 'Cadillac Escalade', 'Cadillac', 'american', 'suv', 90000, 420, 5.8, 12.8, 22.5, 210, 2580, 2022, 'cars/cadillac_escalade.jpg', 'Премиум внедорожник'),
            # RAM
            (207, 'Ram 1500 TRX', 'Ram', 'american', 'pickup', 80000, 702, 4.5, 9.9, 17.4, 190, 2710, 2022, 'cars/ram_trx.jpg', 'Самый мощный пикап'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', american_cars)
    
    def insert_all_parts(self, cursor):
        # Двигатели (только несколько примеров)
        engines = [
            (1, 'Volkswagen EA888 2.0 TSI', 'Volkswagen', 'european', 5000, 50, -10, 85, 8.2, 'parts/engine_vw.jpg'),
            (2, 'Toyota 2JZ-GTE 3.0 I6 TwinTurbo', 'Toyota', 'asian', 15000, 120, 20, 95, 12.5, 'parts/engine_2jz.jpg'),
            (3, 'Chevrolet LS3 6.2 V8', 'Chevrolet', 'american', 12000, 150, 30, 92, 14.5, 'parts/engine_ls3.jpg'),
            (4, 'BMW B58 3.0 I6', 'BMW', 'european', 12000, 100, -5, 88, 9.8, 'parts/engine_bmw.jpg'),
            (5, 'Honda K20A 2.0 I4 VTEC', 'Honda', 'asian', 8500, 60, -8, 90, 9.8, 'parts/engine_k20.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_engines VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', engines)
        
        # Турбины - ИСПРАВЛЕНО: все кортежи имеют 9 значений
        turbos = [
            (1, 'Garrett GT28', 'Garrett', 3000, 30, 1.2, 2800, 85, 'parts/turbo_gt28.jpg'),
            (2, 'Garrett GT30', 'Garrett', 4500, 45, 1.5, 3200, 82, 'parts/turbo_gt30.jpg'),
            (3, 'Garrett GT35', 'Garrett', 6000, 60, 1.8, 3800, 78, 'parts/turbo_gt35.jpg'),
            (4, 'Garrett GTX35', 'Garrett', 7500, 75, 2.0, 3500, 80, 'parts/turbo_gtx35.jpg'),
            (5, 'BorgWarner EFR 6258', 'BorgWarner', 5500, 55, 1.6, 2600, 86, 'parts/turbo_efr6258.jpg'),
            (6, 'BorgWarner K04', 'BorgWarner', 2800, 28, 1.1, 2500, 88, 'parts/turbo_k04.jpg'),
            (7, 'Mitsubishi TD04', 'Mitsubishi', 2500, 25, 1.0, 2400, 87, 'parts/turbo_td04.jpg'),
            (8, 'Mitsubishi TD05', 'Mitsubishi', 3500, 35, 1.3, 2600, 85, 'parts/turbo_td05.jpg'),
            (9, 'Precision Turbo 6266', 'Precision', 8500, 85, 2.2, 3300, 78, 'parts/turbo_pt6266.jpg'),
            (10, 'Turbosmart Kompact', 'Turbosmart', 1800, 18, 0.8, 2200, 89, 'parts/turbo_kompact.jpg'),
            (11, 'GReddy TD05', 'GReddy', 3800, 38, 1.4, 2600, 85, 'parts/turbo_greddy_td05.jpg'),
            (12, 'HKS GT2835', 'HKS', 7200, 72, 2.1, 3000, 81, 'parts/turbo_gt2835.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_turbos VALUES (?,?,?,?,?,?,?,?,?)
        ''', turbos)
        
        # Выхлопы
        exhausts = [
            (1, 'Akrapovič Evolution', 'Akrapovič', 5000, 15, 8, 95, 'Титан', 'parts/exhaust_akra.jpg'),
            (2, 'Remus PowerSound', 'Remus', 2800, 10, 5, 85, 'Нержавеющая сталь', 'parts/exhaust_remus.jpg'),
            (3, 'HKS Hi-Power', 'HKS', 3800, 14, 8, 88, 'Нержавеющая сталь', 'parts/exhaust_hks.jpg'),
            (4, 'Borla Atak', 'Borla', 3500, 13, 7, 92, 'Титан', 'parts/exhaust_borla.jpg'),
            (5, 'GReddy Power Extreme', 'GReddy', 3200, 11, 6, 85, 'Нержавеющая сталь', 'parts/exhaust_greddy.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_exhausts VALUES (?,?,?,?,?,?,?,?)
        ''', exhausts)
        
        # Радиаторы
        radiators = [
            (1, 'Nissens Performance', 'Nissens', 800, 25, 8, 'Стандарт', 'Алюминий', 'parts/radiator_nissens.jpg'),
            (2, 'Behr Hella OEM Plus', 'Behr', 1200, 30, 10, 'Увеличенный', 'Алюминий', 'parts/radiator_behr.jpg'),
            (3, 'Koyo Racing VH Series', 'Koyo', 2200, 45, 15, 'Гоночный', 'Алюминий', 'parts/radiator_koyo.jpg'),
            (4, 'Mishimoto M-Line', 'Mishimoto', 1800, 40, 14, 'Увеличенный', 'Алюминий', 'parts/radiator_mishimoto.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_radiators VALUES (?,?,?,?,?,?,?,?)
        ''', radiators)
        
        # Закись азота
        nitro_kits = [
            (1, 'NOS Sniper Kit', 'NOS', 5000, 100, 15, 500, 85, 'parts/nitro_nos.jpg'),
            (2, 'ZEX Nitrous Kit Dry', 'ZEX', 4500, 90, 12, 450, 87, 'parts/nitro_zex.jpg'),
            (3, 'Nitrous Express EFI Kit', 'Nitrous Express', 7000, 140, 18, 650, 82, 'parts/nitro_ne.jpg'),
            (4, 'Holley NOS Plate Kit', 'Holley', 7200, 145, 20, 680, 81, 'parts/nitro_holley.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_nitro VALUES (?,?,?,?,?,?,?,?,?)
        ''', nitro_kits)
        
        # Подвеска
        suspensions = [
            (1, 'Koni Sport Желтые', 'Koni', 3000, 15, -2, 1, 'Монотрубная', 'parts/suspension_koni.jpg'),
            (2, 'Bilstein B8 Sport', 'Bilstein', 3500, 18, -1, 1, 'Монотрубная', 'parts/suspension_bilstein.jpg'),
            (3, 'KW Variant 3', 'KW', 7000, 22, 0, 1, 'Койловеры', 'parts/suspension_kw.jpg'),
            (4, 'Tein Flex Z', 'Tein', 4500, 16, -3, 1, 'Койловеры', 'parts/suspension_tein.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_suspension VALUES (?,?,?,?,?,?,?,?,?)
        ''', suspensions)
        
        # Покрышки
        tires = [
            (1, 'Michelin Pilot Sport 4 S', 'Michelin', 2000, 20, 85, 90, 'Летние', 'parts/tires_michelin.jpg'),
            (2, 'Goodyear Eagle F1 Asymmetric 6', 'Goodyear', 1800, 18, 80, 88, 'Летние', 'parts/tires_goodyear.jpg'),
            (3, 'Bridgestone Potenza Sport', 'Bridgestone', 1900, 19, 82, 89, 'Летние', 'parts/tires_bridgestone.jpg'),
            (4, 'Pirelli P Zero PZ4', 'Pirelli', 2100, 21, 83, 91, 'Летние', 'parts/tires_pirelli.jpg'),
            (5, 'Nokian Hakkapeliitta 10', 'Nokian', 2200, 15, 90, 70, 'Зимние', 'parts/tires_nokian.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_tires VALUES (?,?,?,?,?,?,?,?,?)
        ''', tires)
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'nickname': user[2],
                'balance': user[3],
                'rating': user[4],
                'followers': user[5],
                'wins': user[6],
                'losses': user[7],
                'races_total': user[8],
                'current_car': user[9],
                'is_banned': user[10]
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
        cursor.execute('''
            INSERT INTO garage (user_id, car_id, is_active)
            VALUES (?, ?, 1)
        ''', (user_id, car_id))
        
        # Обновляем текущую машину у пользователя
        cursor.execute('UPDATE users SET current_car = ? WHERE user_id = ?', (car_id, user_id))
        
        conn.commit()
        conn.close()
    
    def get_car_info(self, car_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars_all WHERE id = ?', (car_id,))
        car = cursor.fetchone()
        conn.close()
        
        if car:
            return {
                'id': car[0],
                'name': car[1],
                'brand': car[2],
                'region': car[3],
                'category': car[4],
                'price': car[5],
                'horse_power': car[6],
                'acceleration_100': car[7],
                'acceleration_200': car[8],
                'acceleration_300': car[9],
                'top_speed': car[10],
                'weight': car[11],
                'year': car[12],
                'image_path': car[13],
                'description': car[14]
            }
        return None
    
    def get_user_garage(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, g.is_active 
            FROM garage g 
            JOIN cars_all c ON g.car_id = c.id 
            WHERE g.user_id = ?
            ORDER BY g.is_active DESC
        ''', (user_id,))
        cars = cursor.fetchall()
        conn.close()
        
        return cars
    
    def check_promocode(self, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code,))
        promo = cursor.fetchone()
        conn.close()
        
        if promo:
            return {
                'id': promo[0],
                'code': promo[1],
                'reward_type': promo[2],
                'reward_value': promo[3],
                'max_uses': promo[4],
                'used_count': promo[5],
                'expires_at': promo[6]
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
    
    def add_promocode(self, code, reward_type, reward_value, max_uses, expires_days=30):
        conn = self.get_connection()
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(days=expires_days)
        cursor.execute('''
            INSERT OR REPLACE INTO promocodes 
            (code, reward_type, reward_value, max_uses, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, reward_type, reward_value, max_uses, expires_at))
        conn.commit()
        conn.close()
    
    def get_top_wins(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, wins FROM users ORDER BY wins DESC LIMIT ?', (limit,))
        top = cursor.fetchall()
        conn.close()
        return top
    
    def get_top_hp(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.nickname, MAX(c.horse_power) as max_hp
            FROM users u
            JOIN garage g ON u.user_id = g.user_id
            JOIN cars_all c ON g.car_id = c.id
            WHERE g.is_active = 1
            GROUP BY u.user_id
            ORDER BY max_hp DESC
            LIMIT ?
        ''', (limit,))
        top = cursor.fetchall()
        conn.close()
        return top
    
    def get_top_followers(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, followers FROM users ORDER BY followers DESC LIMIT ?', (limit,))
        top = cursor.fetchall()
        conn.close()
        return top
    
    def get_cars_by_region(self, region):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars_all WHERE region = ? ORDER BY price', (region,))
        cars = cursor.fetchall()
        conn.close()
        return cars
    
    def get_cars_by_brand(self, brand):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars_all WHERE brand = ? ORDER BY price', (brand,))
        cars = cursor.fetchall()
        conn.close()
        return cars

# Инициализация базы данных
db = Database()

# ==================== ОСНОВНЫЕ ФУНКЦИИ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        db.create_user(user.id, user.username, user.first_name)
    
    # Проверка на бан
    if user_data and user_data['is_banned']:
        await update.message.reply_text("⛔ Вы заблокированы в системе!")
        return
    
    welcome_text = """
    🏁 *Добро пожаловать в Racing Bot!* 🏁

    *Готовы стать легендой уличных гонок?*
    
    🚗 *Коллекция машин:*
    • Европейские: 10+ моделей
    • Азиатские: 9+ моделей  
    • Американские: 8+ моделей
    
    ⚙️ *Тюнинг:*
    • 5 двигателей
    • 12 турбин
    • 5 выхлопных систем
    • 4 радиатора
    • 4 системы закиси азота
    • 4 подвески
    • 5 видов покрышек
    
    🏆 *Соревнования:*
    • Рейтинговая система
    • 3 вида топов
    • Онлайн-гонки
    
    Хотите пройти обучение?
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Пройти обучение", callback_data="training_start")],
        [InlineKeyboardButton("🚀 Начать игру", callback_data="skip_training")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное фото
    try:
        with open('welcome.jpg', 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    except:
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
    
    2. *Первая гонка*
       - Учимся стартовать
       - Знакомимся с механикой гонок
       - Получаем первые награды
    
    3. *Основные возможности*
       - Магазин машин
       - Тюнинг и улучшения
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
    • Вес: {car['weight']} кг
    • Год: {car['year']}
    
    📝 *{car['description']}*
    
    *{car_index + 1}/3*
    """
    
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if car_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"car_prev_{car_index}"))
    
    nav_buttons.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"select_car_{car_id}"))
    
    if car_index < 2:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"car_next_{car_index}"))
    
    keyboard.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправка фото машины
    try:
        with open(car['image_path'], 'rb') as photo:
            if update.callback_query:
                await update.callback_query.message.reply_photo(
                    photo=photo,
                    caption=car_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_photo(
                    photo=photo,
                    caption=car_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
    except:
        if update.callback_query:
            await update.callback_query.message.reply_text(
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
    
    # Удаляем предыдущее сообщение
    await query.message.delete()
    
    return await show_training_car(update, context)

async def select_training_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    car_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id
    
    # Добавляем машину в гараж
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
    4. Машина проедет 500 метров

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
    
    # Анимация отсчета
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
    
    # Время реакции
    reaction_time = (datetime.now() - context.user_data['race_start_time']).total_seconds()
    
    # Анализ реакции
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
        f"{reaction_text}\n"
        f"Время реакции: {reaction_time:.2f} сек.\n\n"
        f"🏎️ Ваша машина ускоряется...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Имитация гонки
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(user_data['current_car'])
    
    # Расчет времени гонки
    base_time = 500 / (car['top_speed'] / 3.6)
    acceleration_factor = car['acceleration_100'] / 8.0
    race_time = base_time * acceleration_factor + reaction_penalty + random.uniform(0.1, 0.3)
    
    await asyncio.sleep(2)
    
    # Награды
    reward = random.randint(1000, 3000)
    followers_gain = random.randint(20, 100)
    rating_gain = random.randint(5, 20)
    
    # Обновляем данные пользователя
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
    • Дистанция: 500 метров
    • Время: {race_time:.2f} сек.
    • Реакция: {reaction_time:.2f} сек.
    • Машина: {car['name']}
    
    🎁 *Награды:*
    • 💰 +{reward} кредитов
    • 👥 +{followers_gain} подписчиков
    • ⭐ +{rating_gain} рейтинга
    
    🎉 *Обучение завершено!* Теперь вы готовы к настоящим гонкам!
    
    💡 *Совет:* Улучшайте машину в магазине запчастей для лучших результатов!
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
    
    # Если у пользователя еще нет машины, даем первую
    if not user_data['current_car']:
        db.add_car_to_garage(user_id, 1)  # Lancer X Sportback
    
    await query.edit_message_text(
        "🎮 *Обучение пропущено!*\n\n"
        "Вы можете в любое время узнать о функциях бота через /help\n\n"
        "Переходим в главное меню...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return await main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        return await start(update, context)
    
    # Получаем текущую машину
    current_car = db.get_car_info(user_data['current_car']) if user_data['current_car'] else None
    
    menu_text = f"""
    🏠 *ГЛАВНОЕ МЕНЮ*

    👤 *Игрок:* {user_data['nickname']}
    ⭐ Рейтинг: {user_data['rating']}
    💰 Баланс: {user_data['balance']} кредитов
    👥 Подписчики: {user_data['followers']}
    🏆 Побед: {user_data['wins']} / Поражений: {user_data['losses']}
    
    🚗 *Текущая машина:* {current_car['name'] if current_car else 'Нет машины'}
    💪 Мощность: {current_car['horse_power'] if current_car else 0} л.с.
    
    *Выберите действие:*
    """
    
    keyboard = [
        [InlineKeyboardButton("🏎️ Быстрая гонка", callback_data="quick_race")],
        [InlineKeyboardButton("🚗 Мой гараж", callback_data="my_garage")],
        [InlineKeyboardButton("🏪 Магазин машин", callback_data="car_shop")],
        [InlineKeyboardButton("⚙️ Магазин запчастей", callback_data="parts_shop")],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="top_menu")],
        [InlineKeyboardButton("🎁 Ввести промокод", callback_data="enter_promo")],
    ]
    
    # Добавляем админ-панель для админов
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
    • Штраф за поражение: -Рейтинг
    
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
    
    return States.RACE_WAITING

async def start_quick_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(user_data['current_car'])
    
    # Симуляция подготовки к гонке
    await query.edit_message_text(
        f"🔍 *Поиск соперника...*\n\n"
        f"Ваша машина: {car['name']}\n"
        f"Мощность: {car['horse_power']} л.с.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(2)
    
    # Симуляция нахождения соперника
    opponent_names = ["Tokyo Drifter", "Speed Demon", "Night Rider", "Street King", "Racing Pro"]
    opponent_name = random.choice(opponent_names)
    opponent_hp = car['horse_power'] + random.randint(-50, 100)
    
    await query.edit_message_text(
        f"👥 *Соперник найден!*\n\n"
        f"🏁 {opponent_name}\n"
        f"💪 Мощность: {opponent_hp} л.с.\n\n"
        f"Подготовка к старту...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(2)
    
    # Старт гонки
    context.user_data['race_start_time'] = datetime.now()
    
    keyboard = [[InlineKeyboardButton("🏁 СТАРТ ГОНКИ", callback_data="race_go")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🚦 *ГОТОВЬСЯ!*\n\n"
        "Нажимайте 'СТАРТ ГОНКИ' когда будете готовы начать!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.RACE_START

async def race_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    car = db.get_car_info(user_data['current_car'])
    
    # Расчет результата гонки
    win_chance = 0.5 + (car['horse_power'] - 200) / 1000  # Базовый шанс 50% + бонус за мощность
    win_chance = max(0.3, min(0.9, win_chance))  # Ограничиваем от 30% до 90%
    
    is_win = random.random() < win_chance
    
    # Время гонки
    race_time = 30 + random.uniform(-5, 5) - (car['horse_power'] / 500)
    race_time = max(20, race_time)
    
    if is_win:
        # Награды за победу
        reward = random.randint(2000, 5000)
        followers_gain = random.randint(50, 200)
        rating_gain = random.randint(10, 30)
        
        result_text = f"""
        🏆 *ПОБЕДА!*
        
        📊 *Результаты гонки:*
        • Время: {race_time:.2f} сек.
        • Дистанция: 1000 метров
        • Машина: {car['name']}
        
        🎁 *Награды:*
        • 💰 +{reward} кредитов
        • 👥 +{followers_gain} подписчиков
        • ⭐ +{rating_gain} рейтинга
        """
        
        # Обновляем данные
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
    else:
        # Потеря рейтинга за поражение
        rating_loss = random.randint(5, 15)
        reward = random.randint(500, 1000)  # Небольшая компенсация
        
        result_text = f"""
        🥈 *ПОРАЖЕНИЕ*
        
        📊 *Результаты гонки:*
        • Время: {race_time:.2f} сек.
        • Дистанция: 1000 метров
        • Машина: {car['name']}
        
        📉 *Потери:*
        • ⭐ -{rating_loss} рейтинга
        • 💰 +{reward} кредитов (утешительный приз)
        """
        
        # Обновляем данные
        db.update_balance(user_id, reward)
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET losses = losses + 1,
                races_total = races_total + 1,
                rating = rating - ?
            WHERE user_id = ?
        ''', (rating_loss, user_id))
        conn.commit()
        conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🏎️ Еще гонка", callback_data="quick_race")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_text,
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
            "🚗 *Ваш гараж пуст!*\n\n"
            "Купите свою первую машину в магазине!",
            parse_mode=ParseMode.MARKDOWN
        )
        return await main_menu(update, context)
    
    garage_text = "🚗 *ВАШ ГАРАЖ*\n\n"
    
    for i, car in enumerate(garage_cars, 1):
        status = "✅ Активна" if car[15] == 1 else "⚪ Не активна"
        garage_text += f"{i}. *{car[1]}*\n"
        garage_text += f"   💪 {car[6]} л.с. | ⏱️ {car[7]} сек. 0-100\n"
        garage_text += f"   🏁 {car[10]} км/ч | 📅 {car[12]} г.\n"
        garage_text += f"   {status}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Сменить активную машину", callback_data="change_active_car")],
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
    
    shop_text = """
    🏪 *МАГАЗИН МАШИН*

    Выберите регион:
    
    🇪🇺 *Европейский автопром*
    • Немецкое качество
    • Итальянский стиль
    • Французский комфорт
    • Британская роскошь
    
    🇯🇵 *Азиатский автопром*  
    • Японская надежность
    • Корейские технологии
    
    🇺🇸 *Американский автопром*
    • Мощные маслкары
    • Внедорожники и пикапы
    • Электрические автомобили
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
    
    european_brands = ["Volkswagen", "Mercedes-Benz", "BMW", "Audi", "Porsche", 
                      "Ferrari", "Lamborghini", "Bugatti", "Rolls-Royce"]
    
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
        "🇪🇺 *ЕВРОПЕЙСКИЕ МАРКИ*\n\n"
        "Выберите марку:",
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
            f"🚫 Машины марки {brand} временно отсутствуют в продаже.",
            parse_mode=ParseMode.MARKDOWN
        )
        return await car_shop(update, context)
    
    context.user_data['brand_cars'] = cars
    return await show_car_model(update, context)

async def show_car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    cars = context.user_data.get('brand_cars', [])
    if not cars:
        return await car_shop(update, context)
    
    index = context.user_data.get('model_index', 0)
    car = cars[index]
    
    car_info = {
        'id': car[0],
        'name': car[1],
        'brand': car[2],
        'region': car[3],
        'category': car[4],
        'price': car[5],
        'horse_power': car[6],
        'acceleration_100': car[7],
        'acceleration_200': car[8],
        'acceleration_300': car[9],
        'top_speed': car[10],
        'weight': car[11],
        'year': car[12],
        'image_path': car[13],
        'description': car[14]
    }
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    car_text = f"""
    🚗 *{car_info['brand']} {car_info['name']}*
    
    📊 *Характеристики:*
    • Мощность: {car_info['horse_power']} л.с.
    • Разгон 0-100: {car_info['acceleration_100']} сек.
    • Макс. скорость: {car_info['top_speed']} км/ч
    • Вес: {car_info['weight']} кг
    • Год: {car_info['year']}
    • Категория: {car_info['category']}
    
    💰 *Цена:* {car_info['price']} кредитов
    📝 *{car_info['description']}*
    
    *{index + 1}/{len(cars)}*
    """
    
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="model_prev"))
    
    # Кнопка покупки
    if user_data['balance'] >= car_info['price']:
        nav_buttons.append(InlineKeyboardButton("🛒 Купить", callback_data=f"buy_car_{car_info['id']}"))
    else:
        nav_buttons.append(InlineKeyboardButton("💸 Недостаточно средств", callback_data="no_money"))
    
    if index < len(cars) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="model_next"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🏪 Назад в магазин", callback_data="car_shop")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправка фото
    try:
        with open(car_info['image_path'], 'rb') as photo:
            if query:
                await query.message.reply_photo(
                    photo=photo,
                    caption=car_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_photo(
                    photo=photo,
                    caption=car_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
    except:
        if query:
            await query.message.reply_text(
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
    
    # Удаляем предыдущее сообщение
    await query.message.delete()
    
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
    
    # Покупка машины
    db.update_balance(user_id, -car['price'])
    db.add_car_to_garage(user_id, car_id)
    
    await query.edit_message_text(
        f"🎉 *Поздравляем с покупкой!*\n\n"
        f"Вы приобрели *{car['brand']} {car['name']}*\n"
        f"💸 Списано: {car['price']} кредитов\n"
        f"💰 Ваш баланс: {user_data['balance'] - car['price']} кредитов\n\n"
        f"Машина добавлена в ваш гараж и активирована!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(3)
    return await main_menu(update, context)

async def parts_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts_text = """
    ⚙️ *МАГАЗИН ЗАПЧАСТЕЙ*

    Выберите категорию запчастей:
    
    🚀 *Двигатели* - Увеличивают мощность
    🌀 *Турбины* - Добавляют наддув
    💨 *Выхлопы* - Улучшают отвод газов
    🌡️ *Радиаторы* - Улучшают охлаждение
    💥 *Закись азота* - Временный буст мощности
    🔄 *Подвеска* - Улучшают управляемость
    🛞 *Покрышки* - Улучшают сцепление
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 Двигатели", callback_data="parts_engines")],
        [InlineKeyboardButton("🌀 Турбины", callback_data="parts_turbos")],
        [InlineKeyboardButton("💨 Выхлопы", callback_data="parts_exhausts")],
        [InlineKeyboardButton("🌡️ Радиаторы", callback_data="parts_radiators")],
        [InlineKeyboardButton("💥 Закись азота", callback_data="parts_nitro")],
        [InlineKeyboardButton("🔄 Подвеска", callback_data="parts_suspension")],
        [InlineKeyboardButton("🛞 Покрышки", callback_data="parts_tires")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
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
    
    category = query.data.replace("parts_", "")
    context.user_data['parts_category'] = category
    
    parts_info = {
        'engines': '🚀 *ДВИГАТЕЛИ*\n\nУвеличивают мощность вашей машины.',
        'turbos': '🌀 *ТУРБИНЫ*\n\nДобавляют турбонаддув для увеличения мощности.',
        'exhausts': '💨 *ВЫХЛОПЫ*\n\nУлучшают отвод выхлопных газов.',
        'radiators': '🌡️ *РАДИАТОРЫ*\n\nУлучшают охлаждение двигателя.',
        'nitro': '💥 *ЗАКИСЬ АЗОТА*\n\nВременное увеличение мощности.',
        'suspension': '🔄 *ПОДВЕСКА*\n\nУлучшают управляемость.',
        'tires': '🛞 *ПОКРЫШКИ*\n\nУлучшают сцепление с дорогой.'
    }
    
    await query.edit_message_text(
        parts_info.get(category, "Выберите запчасть"),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # В реальном приложении здесь будет список деталей
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "⚙️ *Функция в разработке*\n\n"
        "Полный магазин запчастей будет доступен в следующем обновлении!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.MAIN_MENU

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
        "*Текущие промокоды:*\n"
        "• RACINGBOT - 1000 кредитов\n"
        "• WELCOME2024 - 5000 кредитов\n"
        "• SPEED - 2000 кредитов",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return States.PROMO_CODE

async def process_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo_code = update.message.text.upper().strip()
    user_id = update.effective_user.id
    
    # Добавляем тестовые промокоды если их нет
    if not db.check_promocode("RACINGBOT"):
        db.add_promocode("RACINGBOT", "money", 1000, 1000)
    
    if not db.check_promocode("WELCOME2024"):
        db.add_promocode("WELCOME2024", "money", 5000, 500)
    
    if not db.check_promocode("SPEED"):
        db.add_promocode("SPEED", "money", 2000, 200)
    
    if db.use_promocode(user_id, promo_code):
        promo = db.check_promocode(promo_code)
        reward_text = f"{promo['reward_value']} кредитов" if promo['reward_type'] == 'money' else f"{promo['reward_value']} подписчиков"
        
        await update.message.reply_text(
            f"🎉 *Промокод активирован!*\n\n"
            f"Награда: {reward_text}\n"
            f"Осталось использований: {promo['max_uses'] - promo['used_count'] - 1}\n\n"
            f"Возвращаемся в главное меню...",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "❌ *Неверный промокод!*\n\n"
            "Возможные причины:\n"
            "• Промокод не существует\n"
            "• Вы уже использовали этот промокод\n"
            "• Лимит использований исчерпан\n"
            "• Срок действия истек\n\n"
            "Попробуйте другой промокод или вернитесь в меню: /menu",
            parse_mode=ParseMode.MARKDOWN
        )
    
    return await main_menu(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if hasattr(update, 'callback_query'):
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
    
    *Быстрые действия:*
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Добавить промокод", callback_data="admin_add_promo")],
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
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
    
    if len(command) > 1:
        if command[1] == "addpromo" and len(command) == 6:
            code = command[2].upper()
            reward_type = command[3]
            reward_value = int(command[4])
            max_uses = int(command[5])
            
            db.add_promocode(code, reward_type, reward_value, max_uses)
            await update.message.reply_text(f"✅ Промокод {code} добавлен!")
        
        elif command[1] == "ban" and len(command) == 3:
            target_id = int(command[2])
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (target_id,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Пользователь {target_id} забанен!")
        
        elif command[1] == "unban" and len(command) == 3:
            target_id = int(command[2])
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (target_id,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Пользователь {target_id} разбанен!")
        
        elif command[1] == "addmoney" and len(command) == 4:
            target_id = int(command[2])
            amount = int(command[3])
            db.update_balance(target_id, amount)
            await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} кредитов!")
        
        elif command[1] == "addfollowers" and len(command) == 4:
            target_id = int(command[2])
            amount = int(command[3])
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET followers = followers + ? WHERE user_id = ?', 
                          (amount, target_id))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Пользователю {target_id} выдано {amount} подписчиков!")
        
        elif command[1] == "stats":
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Статистика пользователей
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
            
            *Промокоды:*
            • RACINGBOT: {db.check_promocode('RACINGBOT')['used_count'] if db.check_promocode('RACINGBOT') else 0} использований
            • WELCOME2024: {db.check_promocode('WELCOME2024')['used_count'] if db.check_promocode('WELCOME2024') else 0} использований
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
    /garage - Ваш гараж
    /top - Топ игроков
    
    *Как играть:*
    1. Выберите/купите машину
    2. Участвуйте в гонках
    3. Зарабатывайте деньги
    4. Улучшайте машину
    5. Покупайте новые машины
    6. Соревнуйтесь за место в топе
    
    *Управление:*
    • Используйте кнопки под сообщениями
    • Для покупки нажимайте на товары
    • Вводите промокоды в чат
    
    *Поддержка:*
    Для связи с администратором используйте команду /adminmessage
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
    • ID: {user_data['user_id']}
    • Рейтинг: {user_data['rating']} ⭐
    • Баланс: {user_data['balance']} 💰
    • Подписчики: {user_data['followers']} 👥
    
    *Статистика:*
    • Побед: {user_data['wins']} 🏆
    • Поражений: {user_data['losses']} 💔
    • Всего гонок: {user_data['races_total']} 🏎️
    • Winrate: {(user_data['wins'] / user_data['races_total'] * 100 if user_data['races_total'] > 0 else 0):.1f}%
    
    *Текущая машина:*
    • {current_car['name'] if current_car else 'Нет машины'}
    • Мощность: {current_car['horse_power'] if current_car else 0} л.с.
    • Разгон 0-100: {current_car['acceleration_100'] if current_car else 0} сек.
    
    *Прогресс:*
    Игрок с {user_data.get('created_at', 'недавно')}
    """
    
    await update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)

async def garage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    garage_cars = db.get_user_garage(user_id)
    
    if not garage_cars:
        await update.message.reply_text(
            "🚗 *Ваш гараж пуст!*\n\n"
            "Купите свою первую машину в магазине!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    garage_text = "🚗 *ВАШ ГАРАЖ*\n\n"
    
    for i, car in enumerate(garage_cars, 1):
        status = "✅ Активна" if car[15] == 1 else "⚪ Не активна"
        garage_text += f"{i}. *{car[1]}*\n"
        garage_text += f"   💪 {car[6]} л.с. | ⏱️ {car[7]} сек. 0-100\n"
        garage_text += f"   🏁 {car[10]} км/ч | 📅 {car[12]} г.\n"
        garage_text += f"   {status}\n\n"
    
    await update.message.reply_text(garage_text, parse_mode=ParseMode.MARKDOWN)

async def admin_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Позволяет пользователям отправить сообщение админу"""
    user_id = update.effective_user.id
    message_text = ' '.join(context.args)
    
    if not message_text:
        await update.message.reply_text(
            "📝 *Отправьте сообщение админу*\n\n"
            "Использование: /adminmessage Ваше сообщение\n\n"
            "Пример: /adminmessage Нашел баг в гонках",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Сохраняем сообщение в базе
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO admin_messages (user_id, message) VALUES (?, ?)', 
                  (user_id, message_text))
    conn.commit()
    conn.close()
    
    # Отправляем уведомление всем админам
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"📩 *НОВОЕ СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ*\n\n"
                     f"👤 ID: {user_id}\n"
                     f"📝 Сообщение: {message_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    await update.message.reply_text(
        "✅ *Сообщение отправлено администраторам!*\n\n"
        "Мы ответим вам как можно скорее.",
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Действие отменено. Используйте /menu для возврата в меню."
    )
    return ConversationHandler.END

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем тестовые промокоды
    db.add_promocode("RACINGBOT", "money", 1000, 1000)
    db.add_promocode("WELCOME2024", "money", 5000, 500)
    db.add_promocode("SPEED", "money", 2000, 200)
    
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
                CallbackQueryHandler(parts_shop, pattern='^parts_shop$'),
                CallbackQueryHandler(top_menu, pattern='^top_menu$'),
                CallbackQueryHandler(enter_promo, pattern='^enter_promo$'),
                CallbackQueryHandler(admin_panel, pattern='^admin_panel$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.CAR_SHOP: [
                CallbackQueryHandler(shop_european, pattern='^shop_european$'),
                CallbackQueryHandler(shop_european, pattern='^shop_asian$'),
                CallbackQueryHandler(shop_european, pattern='^shop_american$'),
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
                CallbackQueryHandler(show_parts_category, pattern='^parts_'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.TOP_MENU: [
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_promo),
            ],
            States.ADMIN_PANEL: [
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.RACE_WAITING: [
                CallbackQueryHandler(start_quick_race, pattern='^start_quick_race$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            ],
            States.RACE_START: [
                CallbackQueryHandler(race_go, pattern='^race_go$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Добавляем обработчики команд
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('menu', main_menu))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CommandHandler('garage', garage_command))
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('adminmessage', admin_message_command))
    application.add_handler(CommandHandler('stats', admin_command))
    
    # Запускаем бота
    print("=" * 50)
    print("RACING BOT ЗАПУЩЕН!")
    print(f"Администраторы: {ADMIN_IDS}")
    print("Добавлены промокоды: RACINGBOT, WELCOME2024, SPEED")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
