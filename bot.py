#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPLETE TELEGRAM RACING BOT
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

BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"  # Замените на ваш токен
ADMIN_ID = 123456789  # Ваш ID Telegram

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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars_european (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp INTEGER,
                acc_100 REAL,
                top_speed INTEGER,
                image_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars_asian (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp INTEGER,
                acc_100 REAL,
                top_speed INTEGER,
                image_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars_american (
                id INTEGER PRIMARY KEY,
                name TEXT,
                brand TEXT,
                price INTEGER,
                hp INTEGER,
                acc_100 REAL,
                top_speed INTEGER,
                image_path TEXT
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
        
        # Турбины
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
        
        # Европейские машины
        european_cars = [
            # Volkswagen
            (4, 'Volkswagen Golf', 'Volkswagen', 'european', 'hatchback', 15000, 150, 8.5, 18.2, 32.0, 210, 1280, 2020, 'cars/vw_golf.jpg', 'Иконка хетчбеков'),
            (5, 'Volkswagen Passat', 'Volkswagen', 'european', 'sedan', 20000, 190, 7.9, 16.8, 29.5, 230, 1480, 2019, 'cars/vw_passat.jpg', 'Просторный семейный седан'),
            
            # Mercedes-Benz
            (6, 'Mercedes-Benz C-Class', 'Mercedes-Benz', 'european', 'sedan', 35000, 255, 6.0, 13.5, 23.8, 250, 1650, 2021, 'cars/mercedes_c.jpg', 'Престиж и комфорт'),
            (7, 'Mercedes-Benz E-Class', 'Mercedes-Benz', 'european', 'sedan', 50000, 299, 5.7, 12.9, 22.7, 250, 1800, 2022, 'cars/mercedes_e.jpg', 'Бизнес-класс'),
            
            # BMW
            (8, 'BMW 5 Series', 'BMW', 'european', 'sedan', 45000, 248, 6.1, 13.8, 24.2, 250, 1670, 2021, 'cars/bmw_5.jpg', 'Водительское удовольствие'),
            (9, 'BMW X3', 'BMW', 'european', 'suv', 42000, 248, 6.0, 13.6, 24.0, 230, 1860, 2022, 'cars/bmw_x3.jpg', 'Спортивный кроссовер'),
            
            # Audi
            (10, 'Audi A6', 'Audi', 'european', 'sedan', 48000, 265, 5.9, 13.3, 23.5, 250, 1710, 2021, 'cars/audi_a6.jpg', 'Современные технологии'),
            (11, 'Audi Q7', 'Audi', 'european', 'suv', 65000, 340, 5.7, 12.5, 21.8, 250, 2150, 2023, 'cars/audi_q7.jpg', 'Роскошный внедорожник'),
            
            # Porsche
            (12, 'Porsche Panamera', 'Porsche', 'european', 'sedan', 85000, 330, 5.4, 11.9, 20.5, 285, 1870, 2022, 'cars/porsche_panamera.jpg', 'Спортивный седан'),
            (13, 'Porsche Macan', 'Porsche', 'european', 'suv', 68000, 265, 6.2, 13.8, 24.3, 260, 1920, 2023, 'cars/porsche_macan.jpg', 'Спортивный кроссовер'),
            
            # Opel
            (14, 'Opel Insignia', 'Opel', 'european', 'sedan', 22000, 170, 8.1, 17.5, 30.2, 225, 1510, 2020, 'cars/opel_insignia_std.jpg', 'Надежный немецкий седан'),
            
            # Smart
            (15, 'Smart ForFour', 'Smart', 'european', 'hatchback', 12000, 90, 11.9, 28.5, None, 155, 980, 2021, 'cars/smart_forfour.jpg', 'Компактный городской автомобиль'),
            
            # Fiat
            (16, 'Fiat Tipo', 'Fiat', 'european', 'hatchback', 14000, 120, 9.8, 21.5, 38.2, 195, 1250, 2022, 'cars/fiat_tipo.jpg', 'Итальянский стиль'),
            
            # Alfa Romeo
            (17, 'Alfa Romeo Giulietta', 'Alfa Romeo', 'european', 'hatchback', 28000, 240, 6.6, 14.5, 25.3, 240, 1390, 2019, 'cars/alfa_giulietta.jpg', 'Страсть и стиль'),
            
            # Ferrari
            (18, 'Ferrari Roma', 'Ferrari', 'european', 'coupe', 220000, 620, 3.4, 7.2, 12.8, 320, 1570, 2021, 'cars/ferrari_roma.jpg', 'Итальянская грация'),
            (19, 'Ferrari F8 Tributo', 'Ferrari', 'european', 'coupe', 280000, 720, 2.9, 6.5, 11.3, 340, 1430, 2020, 'cars/ferrari_f8.jpg', 'Трибьют легендам'),
            
            # Lamborghini
            (20, 'Lamborghini Huracán', 'Lamborghini', 'european', 'supercar', 250000, 640, 2.9, 6.4, 11.2, 325, 1420, 2022, 'cars/lambo_huracan.jpg', 'Испанский бык'),
            (21, 'Lamborghini Aventador', 'Lamborghini', 'european', 'supercar', 450000, 780, 2.8, 6.0, 10.5, 350, 1575, 2021, 'cars/lambo_aventador.jpg', 'Флагманский V12'),
            
            # Maserati
            (22, 'Maserati Ghibli', 'Maserati', 'european', 'sedan', 75000, 430, 4.9, 10.8, 18.9, 285, 1880, 2022, 'cars/maserati_ghibli.jpg', 'Итальянская роскошь'),
            
            # Pagani
            (23, 'Pagani Zonda', 'Pagani', 'european', 'hypercar', 3500000, 800, 2.7, 5.8, 9.9, 370, 1350, 2018, 'cars/pagani_zonda.jpg', 'Шедевр инженерии'),
            
            # Renault
            (24, 'Renault Megane', 'Renault', 'european', 'hatchback', 17000, 150, 8.0, 17.2, 29.8, 220, 1320, 2021, 'cars/renault_megane.jpg', 'Французский дизайн'),
            (25, 'Renault Kadjar', 'Renault', 'european', 'suv', 23000, 160, 9.2, 19.5, 33.2, 205, 1520, 2022, 'cars/renault_kadjar.jpg', 'Семейный кроссовер'),
            
            # Peugeot
            (26, 'Peugeot 208', 'Peugeot', 'european', 'hatchback', 14000, 130, 8.7, 18.9, 32.5, 205, 1160, 2022, 'cars/peugeot_208.jpg', 'Городской хетчбек'),
            (27, 'Peugeot 508', 'Peugeot', 'european', 'sedan', 28000, 225, 7.3, 15.8, 27.5, 240, 1490, 2021, 'cars/peugeot_508.jpg', 'Французский стиль'),
            
            # Citroën
            (28, 'Citroën C4', 'Citroën', 'european', 'hatchback', 16000, 130, 9.0, 19.5, 33.8, 200, 1280, 2022, 'cars/citroen_c4.jpg', 'Комфорт на первом месте'),
            (29, 'Citroën C5 Aircross', 'Citroën', 'european', 'suv', 25000, 180, 8.5, 18.2, 31.5, 215, 1520, 2023, 'cars/citroen_c5.jpg', 'Комфортный кроссовер'),
            
            # DS
            (30, 'DS 9', 'DS', 'european', 'sedan', 42000, 225, 8.3, 17.9, 31.0, 235, 1620, 2022, 'cars/ds_9.jpg', 'Французская роскошь'),
            
            # Alpine
            (31, 'Alpine A310', 'Alpine', 'european', 'coupe', 65000, 150, 8.1, 17.5, 30.2, 220, 980, 1971, 'cars/alpine_a310.jpg', 'Французская классика'),
            
            # Bugatti
            (32, 'Bugatti Chiron', 'Bugatti', 'european', 'hypercar', 3000000, 1500, 2.4, 4.9, 8.0, 420, 1990, 2022, 'cars/bugatti_chiron.jpg', 'Рекордсмен скорости'),
            
            # Rolls-Royce
            (33, 'Rolls-Royce Cullinan', 'Rolls-Royce', 'european', 'suv', 350000, 571, 5.2, 11.3, 19.8, 250, 2660, 2023, 'cars/rr_cullinan.jpg', 'Вершина роскоши'),
            
            # Bentley
            (34, 'Bentley Flying Spur', 'Bentley', 'european', 'sedan', 220000, 635, 3.8, 8.2, 14.3, 333, 2430, 2022, 'cars/bentley_spur.jpg', 'Британская мощь'),
            
            # Aston Martin
            (35, 'Aston Martin Vantage', 'Aston Martin', 'european', 'coupe', 150000, 510, 3.6, 7.9, 13.8, 314, 1530, 2022, 'cars/aston_vantage.jpg', 'Британский стиль'),
            (36, 'Aston Martin V12 Vantage', 'Aston Martin', 'european', 'coupe', 250000, 700, 3.5, 7.5, 13.0, 330, 1660, 2021, 'cars/aston_v12.jpg', 'Мощный V12'),
            
            # McLaren
            (37, 'McLaren 720S', 'McLaren', 'european', 'supercar', 280000, 720, 2.9, 6.4, 11.2, 341, 1419, 2021, 'cars/mclaren_720s.jpg', 'Британские технологии'),
            (38, 'McLaren Artura', 'McLaren', 'european', 'supercar', 220000, 680, 3.0, 6.7, 11.8, 330, 1495, 2022, 'cars/mclaren_artura.jpg', 'Гибридный суперкар'),
            
            # Jaguar
            (39, 'Jaguar F-PACE', 'Jaguar', 'european', 'suv', 52000, 300, 5.8, 12.7, 22.3, 250, 1880, 2022, 'cars/jaguar_fpace.jpg', 'Британский кроссовер'),
            (40, 'Jaguar XE', 'Jaguar', 'european', 'sedan', 42000, 250, 6.5, 14.2, 25.0, 240, 1660, 2021, 'cars/jaguar_xe.jpg', 'Спортивный седан'),
            
            # Land Rover
            (41, 'Land Rover Discovery Sport', 'Land Rover', 'european', 'suv', 45000, 249, 7.3, 16.0, 28.2, 215, 1980, 2022, 'cars/lr_discovery.jpg', 'Внедорожные способности'),
            
            # Mini
            (42, 'Mini Countryman', 'Mini', 'european', 'suv', 32000, 192, 7.4, 16.2, 28.5, 230, 1610, 2022, 'cars/mini_countryman.jpg', 'Большой Mini'),
            
            # Lotus
            (43, 'Lotus Exige', 'Lotus', 'european', 'sports', 75000, 430, 3.7, 8.1, 14.2, 290, 1176, 2021, 'cars/lotus_exige.jpg', 'Чистое вождение'),
            
            # Volvo
            (44, 'Volvo S60', 'Volvo', 'european', 'sedan', 38000, 250, 6.5, 14.3, 25.2, 235, 1720, 2022, 'cars/volvo_s60.jpg', 'Шведская безопасность'),
            (45, 'Volvo V90', 'Volvo', 'european', 'wagon', 45000, 250, 6.8, 14.9, 26.3, 230, 1830, 2021, 'cars/volvo_v90.jpg', 'Универсал-люкс'),
            
            # Koenigsegg
            (46, 'Koenigsegg Jesko', 'Koenigsegg', 'european', 'hypercar', 2800000, 1600, 2.5, 5.3, 8.9, 480, 1420, 2022, 'cars/koenigsegg_jesko.jpg', 'Шведский гиперкар'),
            
            # Polestar
            (47, 'Polestar 1', 'Polestar', 'european', 'coupe', 155000, 626, 4.2, 9.2, 16.1, 250, 2350, 2021, 'cars/polestar_1.jpg', 'Электрический гибрид'),
            
            # Škoda
            (48, 'Škoda Kodiaq', 'Škoda', 'european', 'suv', 28000, 190, 8.0, 17.3, 30.0, 215, 1740, 2022, 'cars/skoda_kodiaq.jpg', 'Практичный кроссовер'),
            (49, 'Škoda Fabia', 'Škoda', 'european', 'hatchback', 14000, 110, 9.9, 21.8, 38.5, 195, 1150, 2021, 'cars/skoda_fabia.jpg', 'Надежный хетчбек'),
            
            # Dacia
            (50, 'Dacia Logan', 'Dacia', 'european', 'sedan', 9000, 90, 11.5, 26.0, None, 175, 1080, 2022, 'cars/dacia_logan.jpg', 'Бюджетный седан'),
            (51, 'Dacia Jogger', 'Dacia', 'european', 'mpv', 15000, 110, 10.8, 23.8, 41.5, 185, 1320, 2023, 'cars/dacia_jogger.jpg', 'Семейный минивэн'),
            
            # SEAT
            (52, 'SEAT Ateca', 'SEAT', 'european', 'suv', 25000, 150, 8.9, 19.3, 33.5, 210, 1520, 2022, 'cars/seat_ateca.jpg', 'Испанский кроссовер'),
            
            # Cupra
            (53, 'Cupra Leon', 'Cupra', 'european', 'hatchback', 32000, 300, 5.7, 12.5, 22.0, 250, 1440, 2022, 'cars/cupra_leon.jpg', 'Спортивный хетчбек'),
            
            # Lada
            (54, 'Lada Granta', 'Lada', 'european', 'sedan', 7000, 90, 11.8, 26.5, None, 170, 1080, 2022, 'cars/lada_granta.jpg', 'Российская классика'),
            (55, 'Lada XRAY', 'Lada', 'european', 'crossover', 11000, 106, 11.2, 24.5, None, 180, 1240, 2021, 'cars/lada_xray.jpg', 'Российский кроссовер'),
            
            # Renault Arkana
            (56, 'Renault Arkana', 'Renault', 'european', 'crossover', 20000, 150, 9.0, 19.5, 33.8, 200, 1420, 2022, 'cars/renault_arkana.jpg', 'Купейный кроссовер'),
            
            # Hyundai (Европа)
            (57, 'Hyundai Tucson', 'Hyundai', 'european', 'suv', 28000, 186, 8.0, 17.5, 30.5, 210, 1620, 2022, 'cars/hyundai_tucson.jpg', 'Современный дизайн'),
            
            # Kia (Европа)
            (58, 'Kia Ceed', 'Kia', 'european', 'hatchback', 19000, 140, 9.0, 19.5, 34.0, 205, 1350, 2022, 'cars/kia_ceed.jpg', 'Европейская сборка'),
            
            # Toyota (Европа)
            (59, 'Toyota Yaris', 'Toyota', 'european', 'hatchback', 16000, 125, 9.7, 21.0, 36.5, 185, 1130, 2022, 'cars/toyota_yaris.jpg', 'Компактный гибрид'),
            
            # Ford (Европа)
            (60, 'Ford Focus', 'Ford', 'european', 'hatchback', 18000, 150, 8.3, 18.0, 31.5, 220, 1360, 2021, 'cars/ford_focus.jpg', 'Управляемость'),
            (61, 'Ford Kuga', 'Ford', 'european', 'suv', 25000, 150, 9.3, 20.2, 35.0, 205, 1620, 2022, 'cars/ford_kuga.jpg', 'Семейный кроссовер'),
            
            # Nissan (Европа)
            (62, 'Nissan Qashqai', 'Nissan', 'european', 'suv', 24000, 140, 9.9, 21.5, 37.2, 200, 1480, 2022, 'cars/nissan_qashqai.jpg', 'Популярный кроссовер'),
            
            # Suzuki (Европа)
            (63, 'Suzuki Swace', 'Suzuki', 'european', 'wagon', 22000, 122, 10.1, 22.0, 38.5, 180, 1470, 2022, 'cars/suzuki_swace.jpg', 'Гибридный универсал')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', european_cars)
        
        # Азиатские машины (первые 50 из списка)
        asian_cars = [
            # Toyota
            (100, 'Toyota Corolla', 'Toyota', 'asian', 'sedan', 18000, 140, 9.2, 20.0, 35.2, 195, 1330, 2022, 'cars/toyota_corolla.jpg', 'Самый продаваемый автомобиль'),
            (101, 'Toyota Camry', 'Toyota', 'asian', 'sedan', 25000, 203, 7.9, 17.3, 30.5, 230, 1550, 2022, 'cars/toyota_camry.jpg', 'Надежный бизнес-седа'),
            (102, 'Toyota RAV4', 'Toyota', 'asian', 'suv', 28000, 203, 8.0, 17.5, 30.8, 210, 1650, 2022, 'cars/toyota_rav4.jpg', 'Популярный кроссовер'),
            (103, 'Toyota Land Cruiser', 'Toyota', 'asian', 'suv', 85000, 309, 6.7, 14.7, 25.8, 210, 2600, 2022, 'cars/toyota_lc.jpg', 'Легенда бездорожья'),
            (104, 'Toyota Hilux', 'Toyota', 'asian', 'pickup', 35000, 204, 9.8, 21.5, 37.8, 180, 2050, 2022, 'cars/toyota_hilux.jpg', 'Неубиваемый пикап'),
            (105, 'Toyota Supra A90', 'Toyota', 'asian', 'coupe', 55000, 340, 4.1, 9.0, 15.8, 250, 1540, 2022, 'cars/toyota_supra.jpg', 'Возрожденная легенда'),
            (106, 'Toyota GR86', 'Toyota', 'asian', 'coupe', 32000, 235, 6.1, 13.4, 23.5, 240, 1270, 2022, 'cars/toyota_gr86.jpg', 'Заднеприводный спортсмен'),
            (107, 'Toyota Chaser JZX100', 'Toyota', 'asian', 'sedan', 15000, 280, 6.5, 14.3, 25.1, 230, 1580, 1998, 'cars/toyota_chaser.jpg', 'Японский дрифт-кар'),
            (108, 'Toyota Mark II', 'Toyota', 'asian', 'sedan', 12000, 220, 7.5, 16.5, 29.0, 220, 1500, 2000, 'cars/toyota_mark2.jpg', 'Классический седан'),
            (109, 'Toyota Cresta', 'Toyota', 'asian', 'sedan', 11000, 220, 7.6, 16.7, 29.3, 215, 1520, 1999, 'cars/toyota_cresta.jpg', 'Седан для улиц'),
            
            # Lexus
            (110, 'Lexus IS300', 'Lexus', 'asian', 'sedan', 38000, 260, 6.9, 15.2, 26.8, 230, 1650, 2022, 'cars/lexus_is.jpg', 'Японская роскошь'),
            (111, 'Lexus GS', 'Lexus', 'asian', 'sedan', 52000, 311, 5.7, 12.5, 22.0, 250, 1790, 2020, 'cars/lexus_gs.jpg', 'Бизнес-класс'),
            (112, 'Lexus LS500', 'Lexus', 'asian', 'sedan', 85000, 416, 5.0, 11.0, 19.3, 270, 2240, 2022, 'cars/lexus_ls.jpg', 'Флагманский седан'),
            (113, 'Lexus LC500', 'Lexus', 'asian', 'coupe', 95000, 477, 4.4, 9.7, 17.0, 270, 1930, 2022, 'cars/lexus_lc.jpg', 'Гранд-турер'),
            
            # Nissan
            (114, 'Nissan Silvia S15', 'Nissan', 'asian', 'coupe', 35000, 250, 6.8, 15.0, 26.3, 240, 1260, 2002, 'cars/nissan_silvia.jpg', 'Культовый дрифт-кар'),
            (115, 'Nissan Skyline GT-R R34', 'Nissan', 'asian', 'coupe', 120000, 280, 4.9, 10.8, 18.9, 250, 1560, 2002, 'cars/nissan_r34.jpg', 'Легенда JDM'),
            (116, 'Nissan 350Z', 'Nissan', 'asian', 'coupe', 22000, 287, 5.8, 12.8, 22.5, 250, 1520, 2007, 'cars/nissan_350z.jpg', 'Доступный спортсмен'),
            (117, 'Nissan GT-R R35', 'Nissan', 'asian', 'supercar', 115000, 565, 2.9, 6.4, 11.2, 315, 1780, 2022, 'cars/nissan_gtr.jpg', 'Годзилла'),
            (118, 'Nissan Fairlady Z', 'Nissan', 'asian', 'coupe', 42000, 405, 4.2, 9.2, 16.2, 260, 1600, 2023, 'cars/nissan_z.jpg', 'Новое поколение'),
            
            # Honda
            (119, 'Honda Civic Type R', 'Honda', 'asian', 'hatchback', 45000, 320, 5.4, 11.9, 20.9, 275, 1420, 2022, 'cars/honda_civic_r.jpg', 'Переднеприводный чемпион'),
            (120, 'Honda S2000', 'Honda', 'asian', 'roadster', 35000, 240, 5.8, 12.8, 22.5, 240, 1250, 2009, 'cars/honda_s2000.jpg', 'Культовый родстер'),
            (121, 'Honda NSX', 'Honda', 'asian', 'supercar', 165000, 581, 2.9, 6.4, 11.2, 307, 1725, 2022, 'cars/honda_nsx.jpg', 'Японский суперкар'),
            
            # Mazda
            (122, 'Mazda RX-7 FD', 'Mazda', 'asian', 'coupe', 45000, 255, 5.3, 11.7, 20.5, 250, 1260, 2002, 'cars/mazda_rx7.jpg', 'Роторная легенда'),
            (123, 'Mazda MX-5 Miata', 'Mazda', 'asian', 'roadster', 28000, 184, 6.5, 14.3, 25.1, 230, 1070, 2022, 'cars/mazda_mx5.jpg', 'Веселый родстер'),
            
            # Subaru
            (124, 'Subaru Impreza WRX STI', 'Subaru', 'asian', 'sedan', 38000, 310, 5.2, 11.4, 20.0, 255, 1540, 2021, 'cars/subaru_sti.jpg', 'Раллийный чемпион'),
            (125, 'Subaru BRZ', 'Subaru', 'asian', 'coupe', 30000, 228, 6.3, 13.9, 24.4, 240, 1300, 2022, 'cars/subaru_brz.jpg', 'Заднеприводный спортсмен'),
            
            # Mitsubishi
            (126, 'Mitsubishi Lancer Evolution X', 'Mitsubishi', 'asian', 'sedan', 35000, 303, 5.1, 11.2, 19.7, 250, 1610, 2015, 'cars/mitsubishi_evo.jpg', 'Последний Эво'),
            
            # Hyundai
            (127, 'Hyundai i30 N', 'Hyundai', 'asian', 'hatchback', 35000, 280, 5.9, 13.0, 22.8, 250, 1450, 2022, 'cars/hyundai_i30n.jpg', 'Горячий хетчбек'),
            (128, 'Hyundai Genesis Coupe', 'Hyundai', 'asian', 'coupe', 28000, 350, 5.2, 11.4, 20.0, 240, 1590, 2016, 'cars/hyundai_genesis.jpg', 'Корейский спортсмен'),
            
            # Kia
            (129, 'Kia Stinger', 'Kia', 'asian', 'sedan', 42000, 370, 4.7, 10.3, 18.1, 270, 1780, 2022, 'cars/kia_stinger.jpg', 'Быстрый седан'),
            
            # Genesis
            (130, 'Genesis G70', 'Genesis', 'asian', 'sedan', 45000, 370, 4.7, 10.3, 18.1, 270, 1670, 2022, 'cars/genesis_g70.jpg', 'Премиум спортсмен'),
            
            # ... можно добавить остальные азиатские машины аналогично
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', asian_cars)
        
        # Американские машины
        american_cars = [
            # Ford
            (200, 'Ford F-150 Raptor', 'Ford', 'american', 'pickup', 65000, 450, 5.1, 11.2, 19.7, 180, 2600, 2022, 'cars/ford_raptor.jpg', 'Внедорожный пикап'),
            (201, 'Ford Mustang GT', 'Ford', 'american', 'coupe', 45000, 460, 4.0, 8.8, 15.4, 250, 1730, 2022, 'cars/ford_mustang.jpg', 'Американская икона'),
            (202, 'Ford GT', 'Ford', 'american', 'supercar', 500000, 660, 3.0, 6.6, 11.6, 347, 1385, 2022, 'cars/ford_gt.jpg', 'Суперкар Ле-Мана'),
            
            # Chevrolet
            (203, 'Chevrolet Corvette C8', 'Chevrolet', 'american', 'supercar', 65000, 495, 2.9, 6.4, 11.2, 312, 1648, 2022, 'cars/chevrolet_corvette.jpg', 'Среднемоторная революция'),
            (204, 'Chevrolet Camaro ZL1', 'Chevrolet', 'american', 'coupe', 65000, 650, 3.5, 7.7, 13.5, 320, 1915, 2022, 'cars/chevrolet_camaro.jpg', 'Мощный маслкар'),
            
            # Dodge
            (205, 'Dodge Challenger Hellcat', 'Dodge', 'american', 'coupe', 70000, 717, 3.6, 7.9, 13.9, 315, 2040, 2022, 'cars/dodge_challenger.jpg', 'Современный маслкар'),
            (206, 'Dodge Charger Hellcat', 'Dodge', 'american', 'sedan', 75000, 717, 3.6, 7.9, 13.9, 315, 2150, 2022, 'cars/dodge_charger.jpg', 'Четырехдверный монстр'),
            
            # Tesla
            (207, 'Tesla Model S Plaid', 'Tesla', 'american', 'sedan', 135000, 1020, 1.99, 4.3, 7.5, 322, 2190, 2022, 'cars/tesla_model_s.jpg', 'Электрический рекордсмен'),
            (208, 'Tesla Model 3 Performance', 'Tesla', 'american', 'sedan', 62000, 450, 3.1, 6.8, 11.9, 261, 1844, 2022, 'cars/tesla_model_3.jpg', 'Доступная производительность'),
            
            # Jeep
            (209, 'Jeep Wrangler Rubicon', 'Jeep', 'american', 'suv', 45000, 285, 7.5, 16.5, None, 180, 2040, 2022, 'cars/jeep_wrangler.jpg', 'Легенда бездорожья'),
            
            # Cadillac
            (210, 'Cadillac Escalade', 'Cadillac', 'american', 'suv', 90000, 420, 5.8, 12.8, 22.5, 210, 2580, 2022, 'cars/cadillac_escalade.jpg', 'Премиум внедорожник'),
            
            # RAM
            (211, 'Ram 1500 TRX', 'Ram', 'american', 'pickup', 80000, 702, 4.5, 9.9, 17.4, 190, 2710, 2022, 'cars/ram_trx.jpg', 'Самый мощный пикап'),
            
            # GMC
            (212, 'GMC Sierra AT4', 'GMC', 'american', 'pickup', 60000, 355, 6.0, 13.2, 23.2, 180, 2300, 2022, 'cars/gmc_sierra.jpg', 'Премиум пикап'),
            
            # Buick
            (213, 'Buick Enclave', 'Buick', 'american', 'suv', 45000, 310, 6.5, 14.3, 25.1, 210, 1980, 2022, 'cars/buick_enclave.jpg', 'Комфортный кроссовер'),
            
            # Lincoln
            (214, 'Lincoln Navigator', 'Lincoln', 'american', 'suv', 85000, 450, 5.9, 13.0, 22.8, 220, 2680, 2022, 'cars/lincoln_navigator.jpg', 'Роскошный внедорожник'),
            
            # Pontiac
            (215, 'Pontiac Firebird Trans Am', 'Pontiac', 'american', 'coupe', 35000, 325, 5.0, 11.0, 19.3, 250, 1680, 2002, 'cars/pontiac_firebird.jpg', 'Американская классика'),
            
            # Shelby
            (216, 'Shelby Cobra 427', 'Shelby', 'american', 'roadster', 1500000, 485, 4.2, 9.2, 16.2, 265, 1060, 1967, 'cars/shelby_cobra.jpg', 'Американская легенда'),
            
            # ... можно добавить остальные американские машины
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO cars_all VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', american_cars)
    
    def insert_all_parts(self, cursor):
        # Европейские двигатели
        euro_engines = [
            (1, 'Volkswagen EA888 2.0 TSI', 'Volkswagen', 'european', 5000, 50, -10, 85, 8.2, 'parts/engine_vw.jpg'),
            (2, 'Mercedes-Benz M104 3.2 I6', 'Mercedes', 'european', 8500, 80, 25, 90, 11.5, 'parts/engine_mb.jpg'),
            (3, 'BMW B58 3.0 I6', 'BMW', 'european', 12000, 100, -5, 88, 9.8, 'parts/engine_bmw.jpg'),
            (4, 'Porsche Mezger 3.8 H6', 'Porsche', 'european', 25000, 150, -15, 92, 12.5, 'parts/engine_porsche.jpg'),
            (5, 'Audi 2.5 TFSI 5-cyl', 'Audi', 'european', 18000, 120, 10, 87, 11.0, 'parts/engine_audi.jpg'),
            (6, 'Ferrari F136 V8 4.3', 'Ferrari', 'european', 85000, 220, -30, 85, 16.8, 'parts/engine_ferrari.jpg'),
            (7, 'Ferrari F140 V12 6.5', 'Ferrari', 'european', 150000, 350, 40, 82, 21.5, 'parts/engine_ferrari_v12.jpg'),
            (8, 'BMW S65 V8', 'BMW', 'european', 32000, 180, 15, 80, 14.2, 'parts/engine_bmw_v8.jpg'),
            (9, 'Mercedes M113 5.4 V8 Kompressor', 'Mercedes', 'european', 28000, 200, 35, 78, 15.8, 'parts/engine_mb_v8.jpg'),
            (10, 'Volkswagen 1.9 TDI PD', 'Volkswagen', 'european', 3500, 40, 5, 95, 5.8, 'parts/engine_vw_tdi.jpg'),
            (11, 'BMW S55 I6 TwinTurbo', 'BMW', 'european', 22000, 180, -8, 83, 10.5, 'parts/engine_bmw_s55.jpg'),
            (12, 'Audi 4.2 FSI V8', 'Audi', 'european', 30000, 160, 20, 81, 13.5, 'parts/engine_audi_v8.jpg'),
            (13, 'Opel C20XE', 'Opel', 'european', 2500, 30, -3, 88, 9.2, 'parts/engine_opel.jpg'),
            (14, 'Renault F7R 2.0 16V', 'Renault', 'european', 2800, 35, -5, 85, 9.5, 'parts/engine_renault.jpg'),
            (15, 'Alfa Romeo Twin Spark 2.0', 'Alfa Romeo', 'european', 3200, 45, -7, 82, 10.2, 'parts/engine_alfa.jpg'),
            (16, 'Jaguar AJ-V8 5.0', 'Jaguar', 'european', 45000, 250, 25, 79, 14.8, 'parts/engine_jaguar.jpg'),
            (17, 'Volvo B230 2.3 Turbo', 'Volvo', 'european', 3800, 55, 12, 90, 10.5, 'parts/engine_volvo.jpg'),
            (18, 'Škoda 1.8T 20V AUQ', 'Škoda', 'european', 3000, 48, -4, 86, 9.8, 'parts/engine_skoda.jpg'),
            (19, 'BMW S85 V10', 'BMW', 'european', 55000, 280, 30, 75, 18.5, 'parts/engine_bmw_v10.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_engines VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', euro_engines)
        
        # Азиатские двигатели
        asian_engines = [
            (20, 'Toyota 2JZ-GTE 3.0 I6 TwinTurbo', 'Toyota', 'asian', 15000, 120, 20, 95, 12.5, 'parts/engine_2jz.jpg'),
            (21, 'Nissan RB26DETT 2.6 I6 TwinTurbo', 'Nissan', 'asian', 18000, 140, 18, 92, 13.2, 'parts/engine_rb26.jpg'),
            (22, 'Honda K20A 2.0 I4 VTEC', 'Honda', 'asian', 8500, 60, -8, 90, 9.8, 'parts/engine_k20.jpg'),
            (23, 'Mazda 13B-REW 1.3 TwinRotary', 'Mazda', 'asian', 12000, 110, -15, 70, 14.5, 'parts/engine_13b.jpg'),
            (24, 'Subaru EJ25 2.5 B4 Turbo', 'Subaru', 'asian', 9500, 85, 10, 85, 11.2, 'parts/engine_ej25.jpg'),
            (25, 'Mitsubishi 4G63T 2.0 I4 Turbo', 'Mitsubishi', 'asian', 6500, 70, -5, 88, 10.5, 'parts/engine_4g63.jpg'),
            (26, 'Honda F20C 2.0 I4 VTEC', 'Honda', 'asian', 11000, 90, -10, 89, 10.8, 'parts/engine_f20c.jpg'),
            (27, 'Nissan SR20DET 2.0 I4 Turbo', 'Nissan', 'asian', 7000, 75, -6, 87, 10.2, 'parts/engine_sr20.jpg'),
            (28, 'Toyota 1UZ-FE 4.0 V8', 'Toyota', 'asian', 12500, 100, 25, 93, 13.8, 'parts/engine_1uz.jpg'),
            (29, 'Toyota 1GR-FE 4.0 V6', 'Toyota', 'asian', 10500, 80, 15, 94, 12.5, 'parts/engine_1gr.jpg'),
            (30, 'Honda B16B 1.6 I4 VTEC', 'Honda', 'asian', 5500, 45, -12, 91, 8.5, 'parts/engine_b16b.jpg'),
            (31, 'Nissan VQ35DE 3.5 V6', 'Nissan', 'asian', 9500, 90, 18, 89, 12.0, 'parts/engine_vq35.jpg'),
            (32, 'Hyundai Gamma 1.6 T-GDi', 'Hyundai', 'asian', 4500, 55, -4, 86, 7.8, 'parts/engine_gamma.jpg'),
            (33, 'Toyota 2AR-FE 2.5 I4', 'Toyota', 'asian', 3500, 30, 3, 96, 8.2, 'parts/engine_2ar.jpg'),
            (34, 'Mitsubishi 6G74 3.5 V6', 'Mitsubishi', 'asian', 6500, 65, 20, 87, 11.5, 'parts/engine_6g74.jpg'),
            (35, 'Suzuki K14B 1.4 I4', 'Suzuki', 'asian', 2200, 20, -2, 94, 6.5, 'parts/engine_k14b.jpg'),
            (36, 'Subaru FA20 2.0 B4', 'Subaru', 'asian', 8500, 70, -8, 88, 9.8, 'parts/engine_fa20.jpg'),
            (37, 'Toyota 1NZ-FE 1.5 I4', 'Toyota', 'asian', 2500, 15, -1, 97, 6.2, 'parts/engine_1nz.jpg'),
            (38, 'Mazda SkyActiv-G 2.5 I4', 'Mazda', 'asian', 5000, 50, -6, 91, 8.0, 'parts/engine_skyactiv.jpg'),
            (39, 'Isuzu 4JJ1 3.0 I4 турбодизель', 'Isuzu', 'asian', 6000, 60, 25, 98, 7.5, 'parts/engine_4jj1.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_engines VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', asian_engines)
        
        # Американские двигатели
        american_engines = [
            (40, 'Chevrolet LS3 6.2 V8', 'Chevrolet', 'american', 12000, 150, 30, 92, 14.5, 'parts/engine_ls3.jpg'),
            (41, 'Ford Coyote 5.0 V8', 'Ford', 'american', 13500, 160, 28, 90, 13.8, 'parts/engine_coyote.jpg'),
            (42, 'Chrysler HEMI 6.4 V8', 'Chrysler', 'american', 15000, 180, 35, 87, 15.2, 'parts/engine_hemi.jpg'),
            (43, 'Chevrolet Big Block 454 V8', 'Chevrolet', 'american', 22000, 250, 65, 80, 19.5, 'parts/engine_bigblock.jpg'),
            (44, 'Ford Modular 5.4 V8', 'Ford', 'american', 9500, 130, 25, 85, 13.5, 'parts/engine_modular.jpg'),
            (45, 'Dodge Hellcat 6.2 V8 Supercharged', 'Dodge', 'american', 35000, 300, 45, 78, 17.8, 'parts/engine_hellcat.jpg'),
            (46, 'Cadillac Northstar 4.6 V8', 'Cadillac', 'american', 8500, 100, 22, 82, 12.8, 'parts/engine_northstar.jpg'),
            (47, 'Ford Ecoboost 2.3 I4 Turbo', 'Ford', 'american', 5500, 70, -3, 88, 9.2, 'parts/engine_ecoboost.jpg'),
            (48, 'GM Ecotec 2.0 I4', 'GM', 'american', 3800, 45, -4, 89, 8.5, 'parts/engine_ecotec.jpg'),
            (49, 'AMC 4.0 I6', 'AMC', 'american', 2800, 40, 15, 90, 10.5, 'parts/engine_amc.jpg'),
            (50, 'Chrysler Slant-6 2.5 I4', 'Chrysler', 'american', 2200, 25, 8, 92, 9.8, 'parts/engine_slant6.jpg'),
            (51, 'Buick 3.8 V6 3800', 'Buick', 'american', 3200, 55, 18, 93, 11.2, 'parts/engine_3800.jpg'),
            (52, 'Ford 7.3 Power Stroke V8 Diesel', 'Ford', 'american', 18000, 120, 85, 95, 13.5, 'parts/engine_powerstroke.jpg'),
            (53, 'Cummins 5.9L 6BT I6 Diesel', 'Cummins', 'american', 25000, 150, 95, 96, 14.2, 'parts/engine_cummins.jpg'),
            (54, 'Chevrolet 350 Small Block V8', 'Chevrolet', 'american', 8500, 120, 25, 91, 13.8, 'parts/engine_smallblock.jpg'),
            (55, 'Pontiac 455 V8', 'Pontiac', 'american', 12500, 140, 35, 84, 16.5, 'parts/engine_pontiac.jpg'),
            (56, 'Oldsmobile 455 Rocket V8', 'Oldsmobile', 'american', 11500, 135, 32, 83, 15.8, 'parts/engine_oldsmobile.jpg'),
            (57, 'Ford Flathead V8', 'Ford', 'american', 6500, 80, 20, 85, 12.5, 'parts/engine_flathead.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_engines VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', american_engines)
        
        # Турбины
        turbos = [
            (1, 'Garrett GT28', 'Garrett', 3000, 30, 1.2, 2800, 85, 'parts/turbo_gt28.jpg'),
            (2, 'Garrett GT30', 'Garrett', 4500, 45, 1.5, 3200, 82, 'parts/turbo_gt30.jpg'),
            (3, 'Garrett GT35', 'Garrett', 6000, 60, 1.8, 3800, 78, 'parts/turbo_gt35.jpg'),
            (4, 'Garrett GTX35', 'Garrett', 7500, 75, 2.0, 3500, 80, 'parts/turbo_gtx35.jpg'),
            (5, 'Garrett GTX3582R', 'Garrett', 8500, 85, 2.2, 3400, 77, 'parts/turbo_gtx3582.jpg'),
            (6, 'Garrett GTX3584RS', 'Garrett', 9500, 95, 2.4, 3300, 75, 'parts/turbo_gtx3584.jpg'),
            (7, 'Garrett G25-550', 'Garrett', 7000, 70, 1.9, 2900, 83, 'parts/turbo_g25.jpg'),
            (8, 'Garrett G30-660', 'Garrett', 8000, 80, 2.1, 3100, 79, 'parts/turbo_g30.jpg'),
            (9, 'BorgWarner EFR 6258', 'BorgWarner', 5500, 55, 1.6, 2600, 86, 'parts/turbo_efr6258.jpg'),
            (10, 'BorgWarner EFR 7163', 'BorgWarner', 6500, 65, 1.8, 2800, 84, 'parts/turbo_efr7163.jpg'),
            (11, 'BorgWarner EFR 8374', 'BorgWarner', 8500, 85, 2.2, 3000, 80, 'parts/turbo_efr8374.jpg'),
            (12, 'BorgWarner K04', 'BorgWarner', 2800, 28, 1.1, 2500, 88, 'parts/turbo_k04.jpg'),
            (13, 'BorgWarner K16', 'BorgWarner', 3500, 35, 1.3, 2700, 85, 'parts/turbo_k16.jpg'),
            (14, 'BorgWarner S200', 'BorgWarner', 5000, 50, 1.7, 3200, 81, 'parts/turbo_s200.jpg'),
            (15, 'BorgWarner S300', 'BorgWarner', 6500, 65, 1.9, 3400, 78, 'parts/turbo_s300.jpg'),
            (16, 'BorgWarner S400', 'BorgWarner', 8000, 80, 2.3, 3600, 76, 'parts/turbo_s400.jpg'),
            (17, 'Honeywell HT30', 'Honeywell', 3200, 32, 1.2, 2900, 84, 'parts/turbo_ht30.jpg'),
            (18, 'Honeywell HE351', 'Honeywell', 4200, 42, 1.4, 3100, 82, 'parts/turbo_he351.jpg'),
            (19, 'Mitsubishi TD04', 'Mitsubishi', 2500, 25, 1.0, 2400, 87, 'parts/turbo_td04.jpg'),
            (20, 'Mitsubishi TD05', 'Mitsubishi', 3500, 35, 1.3, 2600, 85, 'parts/turbo_td05.jpg'),
            (21, 'Mitsubishi TD06', 'Mitsubishi', 5000, 50, 1.6, 2800, 82, 'parts/turbo_td06.jpg'),
            (22, 'Mitsubishi TF035', 'Mitsubishi', 2800, 28, 1.1, 2500, 86, 'parts/turbo_tf035.jpg'),
            (23, 'IHI VF39', 'IHI', 3800, 38, 1.4, 2700, 83, 'parts/turbo_vf39.jpg'),
            (24, 'IHI VF48', 'IHI', 4500, 45, 1.5, 2800, 82, 'parts/turbo_vf48.jpg'),
            (25, 'IHI RHF5', 'IHI', 5200, 52, 1.7, 2900, 81, 'parts/turbo_rhf5.jpg'),
            (26, 'KKK K03', 'KKK', 2200, 22, 0.9, 2300, 88, 'parts/turbo_k03.jpg'),
            (27, 'KKK K24', 'KKK', 3800, 38, 1.4, 2600, 84, 'parts/turbo_k24.jpg'),
            (28, 'Holset HX35', 'Holset', 5500, 55, 1.8, 3200, 82, 'parts/turbo_hx35.jpg'),
            (29, 'Holset HX40', 'Holset', 7000, 70, 2.0, 3400, 79, 'parts/turbo_hx40.jpg'),
            (30, 'Holset HE221', 'Holset', 4200, 42, 1.4, 3000, 83, 'parts/turbo_he221.jpg'),
            (31, 'Precision Turbo 6266', 'Precision', 8500, 85, 2.2, 3300, 78, 'parts/turbo_pt6266.jpg'),
            (32, 'Precision Turbo 6766', 'Precision', 9500, 95, 2.4, 3400, 76, 'parts/turbo_pt6766.jpg'),
            (33, 'Precision Turbo 7675', 'Precision', 11000, 110, 2.6, 3500, 74, 'parts/turbo_pt7675.jpg'),
            (34, 'Turbosmart Kompact', 'Turbosmart', 1800, 18, 0.8, 2200, 89, 'parts/turbo_kompact.jpg'),
            (35, 'Turbosmart Hyperboost', 'Turbosmart', 3200, 32, 1.2, 2500, 86, 'parts/turbo_hyperboost.jpg'),
            (36, 'GReddy TD05', 'GReddy', 3800, 38, 1.4, 2600, 85, 'parts/turbo_greddy_td05.jpg'),
            (37, 'GReddy T518Z', 'GReddy', 4200, 42, 1.5, 2700, 84, 'parts/turbo_t518z.jpg'),
            (38, 'Blouch Dominator 3.0', 'Blouch', 6800, 68, 2.0, 3100, 80, 'parts/turbo_dom3.jpg'),
            (39, 'Blouch 20G-XT', 'Blouch', 5200, 52, 1.7, 2900, 82, 'parts/turbo_20g.jpg'),
            (40, 'HKS GT2835', 'HKS', 7200, 72, 2.1, 3000, 81, 'parts/turbo_gt2835.jpg'),
            (41, 'HKS GT-RS', 'HKS', 8800, 88, 2.3, 3200, 79, 'parts/turbo_gtrs.jpg'),
            (42, 'Turbonetics T-70', 'Turbonetics', 6500, 65, 1.9, 3300, 80, 'parts/turbo_t70.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_turbos VALUES (?,?,?,?,?,?,?,?)
        ''', turbos)
        
        # Выхлопы
        exhausts = [
            (1, 'Akrapovič Evolution', 'Akrapovič', 5000, 15, 8, 95, 'Титан', 'parts/exhaust_akra.jpg'),
            (2, 'Remus PowerSound', 'Remus', 2800, 10, 5, 85, 'Нержавеющая сталь', 'parts/exhaust_remus.jpg'),
            (3, 'Milltek Non-Resonated', 'Milltek', 3200, 12, 6, 90, 'Нержавеющая сталь', 'parts/exhaust_milltek.jpg'),
            (4, 'Supersprint Sport', 'Supersprint', 2500, 8, 4, 80, 'Нержавеющая сталь', 'parts/exhaust_supersprint.jpg'),
            (5, 'Sebring Sport', 'Sebring', 1800, 6, 3, 75, 'Алюминиевая сталь', 'parts/exhaust_sebring.jpg'),
            (6, 'MagnaFlow Competition', 'MagnaFlow', 2200, 9, 5, 82, 'Нержавеющая сталь', 'parts/exhaust_magnaflow.jpg'),
            (7, 'Borla Atak', 'Borla', 3500, 13, 7, 92, 'Титан', 'parts/exhaust_borla.jpg'),
            (8, 'FOX Performance', 'FOX', 1500, 5, 2, 70, 'Сталь', 'parts/exhaust_fox.jpg'),
            (9, 'HKS Hi-Power', 'HKS', 3800, 14, 8, 88, 'Нержавеющая сталь', 'parts/exhaust_hks.jpg'),
            (10, 'HKS Legamax Premium', 'HKS', 4200, 10, 9, 78, 'Титан', 'parts/exhaust_legamax.jpg'),
            (11, 'GReddy Power Extreme', 'GReddy', 3200, 11, 6, 85, 'Нержавеющая сталь', 'parts/exhaust_greddy.jpg'),
            (12, 'AsSO "Прямоток"', 'AsSO', 1200, 7, 1, 98, 'Сталь', 'parts/exhaust_asso.jpg'),
            (13, 'Plazma "Спорт"', 'Plazma', 1000, 5, 2, 95, 'Сталь', 'parts/exhaust_plazma.jpg'),
            (14, 'STiM "Стандарт"', 'STiM', 800, 3, 0, 75, 'Сталь', 'parts/exhaust_stim.jpg'),
            (15, 'Scarab "Спорт"', 'Scarab', 1600, 6, 3, 80, 'Алюминиевая сталь', 'parts/exhaust_scarab.jpg'),
            (16, 'TiAL Q', 'TiAL', 4500, 12, 10, 85, 'Титан', 'parts/exhaust_tial.jpg'),
            (17, 'Walker Quiet-Flow', 'Walker', 900, 2, 0, 65, 'Сталь', 'parts/exhaust_walker.jpg'),
            (18, 'Bosal Performance', 'Bosal', 2000, 7, 4, 78, 'Нержавеющая сталь', 'parts/exhaust_bosal.jpg'),
            (19, 'AP Exhaust Sport', 'AP', 1400, 5, 2, 72, 'Сталь', 'parts/exhaust_ap.jpg'),
            (20, 'Jetex Race', 'Jetex', 2800, 10, 6, 88, 'Нержавеющая сталь', 'parts/exhaust_jetex.jpg'),
            (21, 'Bastuck Sport', 'Bastuck', 2300, 8, 5, 82, 'Нержавеющая сталь', 'parts/exhaust_bastuck.jpg'),
            (22, 'A"PEXi N1', 'A"PEXi', 3400, 12, 7, 90, 'Нержавеющая сталь', 'parts/exhaust_apexi.jpg'),
            (23, '5Zigen Fireball', '5Zigen', 3100, 11, 6, 87, 'Нержавеющая сталь', 'parts/exhaust_5zigen.jpg'),
            (24, 'Tanabe Medalion Touring', 'Tanabe', 3800, 9, 8, 80, 'Титан', 'parts/exhaust_tanabe.jpg'),
            (25, 'Fujitsubo Legalis R', 'Fujitsubo', 4200, 10, 9, 78, 'Титан', 'parts/exhaust_fujitsubo.jpg'),
            (26, 'Skunk2 MegaPower', 'Skunk2', 2900, 10, 5, 85, 'Нержавеющая сталь', 'parts/exhaust_skunk2.jpg'),
            (27, 'Thermal R&D', 'Thermal', 2600, 9, 4, 83, 'Нержавеющая сталь', 'parts/exhaust_thermal.jpg'),
            (28, 'Mugen Twin Loop', 'Mugen', 4800, 8, 10, 75, 'Титан', 'parts/exhaust_mugen.jpg'),
            (29, 'Spoon Sports', 'Spoon', 5200, 13, 9, 82, 'Титан', 'parts/exhaust_spoon.jpg'),
            (30, 'Kakimoto Regu 06&R', 'Kakimoto', 4400, 12, 8, 85, 'Нержавеющая сталь', 'parts/exhaust_kakimoto.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_exhausts VALUES (?,?,?,?,?,?,?,?)
        ''', exhausts)
        
        # Радиаторы
        radiators = [
            (1, 'Nissens Performance', 'Nissens', 800, 25, 8, 'Стандарт', 'Алюминий', 'parts/radiator_nissens.jpg'),
            (2, 'Behr Hella OEM Plus', 'Behr', 1200, 30, 10, 'Увеличенный', 'Алюминий', 'parts/radiator_behr.jpg'),
            (3, 'Denso Ultra-Cool', 'Denso', 1500, 35, 12, 'Спортивный', 'Алюминий', 'parts/radiator_denso.jpg'),
            (4, 'Valeo Premium', 'Valeo', 1000, 28, 9, 'Стандарт', 'Алюминий', 'parts/radiator_valeo.jpg'),
            (5, 'Koyo Racing VH Series', 'Koyo', 2200, 45, 15, 'Гоночный', 'Алюминий', 'parts/radiator_koyo.jpg'),
            (6, 'Mishimoto M-Line', 'Mishimoto', 1800, 40, 14, 'Увеличенный', 'Алюминий', 'parts/radiator_mishimoto.jpg'),
            (7, 'CSF Racing Triple-Pass', 'CSF', 2500, 50, 18, 'Гоночный', 'Алюминий', 'parts/radiator_csf.jpg'),
            (8, 'N-Flow Pro Series', 'N-Flow', 1600, 35, 13, 'Увеличенный', 'Алюминий', 'parts/radiator_nflow.jpg'),
            (9, 'Fenox Turbo-Cool', 'Fenox', 900, 22, 8, 'Стандарт', 'Алюминий', 'parts/radiator_fenox.jpg'),
            (10, 'AVA High-Efficiency', 'AVA', 1300, 32, 11, 'Увеличенный', 'Алюминий', 'parts/radiator_ava.jpg'),
            (11, 'Calsonic Nismo', 'Calsonic', 2800, 48, 16, 'Гоночный', 'Алюминий', 'parts/radiator_calsonic.jpg'),
            (12, 'GRAF A/C Plus', 'GRAF', 1100, 26, 9, 'Стандарт', 'Алюминий', 'parts/radiator_graf.jpg'),
            (13, 'Luzar ProFlow', 'Luzar', 850, 20, 7, 'Стандарт', 'Алюминий', 'parts/radiator_luzar.jpg'),
            (14, 'TYC All-Aluminum', 'TYC', 1400, 33, 12, 'Увеличенный', 'Алюминий', 'parts/radiator_tyc.jpg'),
            (15, 'Meyle HD', 'Meyle', 1200, 28, 10, 'Стандарт', 'Алюминий', 'parts/radiator_meyle.jpg'),
            (16, 'Automega Extreme', 'Automega', 1900, 42, 15, 'Гоночный', 'Алюминий', 'parts/radiator_automega.jpg'),
            (17, 'HJS Competition', 'HJS', 2300, 46, 17, 'Гоночный', 'Алюминий', 'parts/radiator_hjs.jpg'),
            (18, 'PWR Performance', 'PWR', 2700, 52, 19, 'Гоночный', 'Алюминий', 'parts/radiator_pwr.jpg'),
            (19, 'Champion Cooler', 'Champion', 950, 24, 8, 'Стандарт', 'Алюминий', 'parts/radiator_champion.jpg'),
            (20, 'Rada-Expert Pro', 'Rada-Expert', 1700, 38, 14, 'Увеличенный', 'Алюминий', 'parts/radiator_rada.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_radiators VALUES (?,?,?,?,?,?,?,?)
        ''', radiators)
        
        # Закись азота
        nitro_kits = [
            (1, 'NOS Sniper Kit', 'NOS', 5000, 100, 15, 500, 85, 'parts/nitro_nos.jpg'),
            (2, 'NOS Cheater Kit', 'NOS', 6500, 125, 20, 600, 80, 'parts/nitro_cheater.jpg'),
            (3, 'NOS Powershot Kit', 'NOS', 7500, 150, 25, 700, 78, 'parts/nitro_powershot.jpg'),
            (4, 'NOS Nytrex Kit', 'NOS', 8500, 175, 30, 800, 75, 'parts/nitro_nytrex.jpg'),
            (5, 'NOS Pro Shot Fogger Kit', 'NOS', 10000, 200, 35, 900, 72, 'parts/nitro_fogger.jpg'),
            (6, 'ZEX Nitrous Kit Dry', 'ZEX', 4500, 90, 12, 450, 87, 'parts/nitro_zex.jpg'),
            (7, 'ZEX Nitrous Kit Wet', 'ZEX', 5500, 110, 14, 550, 85, 'parts/nitro_zex_wet.jpg'),
            (8, 'Nitrous Express EFI Kit', 'Nitrous Express', 7000, 140, 18, 650, 82, 'parts/nitro_ne.jpg'),
            (9, 'Nitrous Express Shark Nozzle Kit', 'Nitrous Express', 9000, 180, 25, 750, 78, 'parts/nitro_shark.jpg'),
            (10, 'NX Stage Kit', 'NX', 6000, 120, 15, 600, 84, 'parts/nitro_nx.jpg'),
            (11, 'NX Maximizer Kit', 'NX', 8000, 160, 22, 700, 80, 'parts/nitro_maximizer.jpg'),
            (12, 'WON Direct Port Kit', 'Wizard of Nos', 12000, 220, 35, 850, 75, 'parts/nitro_won.jpg'),
            (13, 'WON Progressive Controller', 'Wizard of Nos', 3000, 0, 0, 0, 95, 'parts/nitro_controller.jpg'),
            (14, 'Edelbrock Nitrous Kit', 'Edelbrock', 5800, 115, 16, 580, 83, 'parts/nitro_edelbrock.jpg'),
            (15, 'Holley NOS Plate Kit', 'Holley', 7200, 145, 20, 680, 81, 'parts/nitro_holley.jpg'),
            (16, 'TNT Nitrous Kit', 'TNT', 4800, 95, 13, 480, 86, 'parts/nitro_tnt.jpg'),
            (17, 'DynoTune NOS', 'DynoTune', 5200, 105, 14, 520, 85, 'parts/nitro_dynotune.jpg'),
            (18, 'Nitrous Pro Race Kit', 'Nitrous Pro', 9500, 190, 28, 820, 77, 'parts/nitro_prorace.jpg'),
            (19, 'SNIPEFX Nitrous System', 'SNIPEFX', 6800, 135, 19, 630, 82, 'parts/nitro_snipefx.jpg'),
            (20, 'MDS Fogger', 'MDS', 11000, 210, 32, 880, 74, 'parts/nitro_mds.jpg'),
            (21, 'ICE Nitrous Plate System', 'ICE', 7700, 155, 23, 720, 79, 'parts/nitro_ice.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_nitro VALUES (?,?,?,?,?,?,?,?)
        ''', nitro_kits)
        
        # Подвеска
        suspensions = [
            (1, 'Koni Sport Желтые', 'Koni', 3000, 15, -2, 1, 'Монотрубная', 'parts/suspension_koni.jpg'),
            (2, 'Bilstein B8 Sport', 'Bilstein', 3500, 18, -1, 1, 'Монотрубная', 'parts/suspension_bilstein.jpg'),
            (3, 'Öhlins Road & Track', 'Öhlins', 8000, 25, 1, 1, 'Койловеры', 'parts/suspension_ohlins.jpg'),
            (4, 'KW Variant 3', 'KW', 7000, 22, 0, 1, 'Койловеры', 'parts/suspension_kw.jpg'),
            (5, 'KYB Gas-a-Just', 'KYB', 1500, 8, 3, 0, 'Газомасляная', 'parts/suspension_kyb.jpg'),
            (6, 'Monroe Reflex', 'Monroe', 1200, 5, 5, 0, 'Газомасляная', 'parts/suspension_monroe.jpg'),
            (7, 'Sachs Performance', 'Sachs', 2800, 12, 0, 1, 'Газомасляная', 'parts/suspension_sachs.jpg'),
            (8, 'Tein Flex Z', 'Tein', 4500, 16, -3, 1, 'Койловеры', 'parts/suspension_tein.jpg'),
            (9, 'BC Racing BR Series', 'BC Racing', 5500, 20, -2, 1, 'Койловеры', 'parts/suspension_bc.jpg'),
            (10, 'H&R Monotube', 'H&R', 4000, 14, -1, 1, 'Монотрубная', 'parts/suspension_hr.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_suspension VALUES (?,?,?,?,?,?,?,?)
        ''', suspensions)
        
        # Покрышки
        tires = [
            (1, 'Michelin Pilot Sport 4 S', 'Michelin', 2000, 20, 85, 90, 'Летние', 'parts/tires_michelin.jpg'),
            (2, 'Goodyear Eagle F1 Asymmetric 6', 'Goodyear', 1800, 18, 80, 88, 'Летние', 'parts/tires_goodyear.jpg'),
            (3, 'Bridgestone Potenza Sport', 'Bridgestone', 1900, 19, 82, 89, 'Летние', 'parts/tires_bridgestone.jpg'),
            (4, 'Pirelli P Zero PZ4', 'Pirelli', 2100, 21, 83, 91, 'Летние', 'parts/tires_pirelli.jpg'),
            (5, 'Continental PremiumContact 6', 'Continental', 1700, 17, 78, 87, 'Летние', 'parts/tires_continental.jpg'),
            (6, 'Dunlop Sport Maxx RT2', 'Dunlop', 1600, 16, 75, 85, 'Летние', 'parts/tires_dunlop.jpg'),
            (7, 'Hankook Ventus S1 evo3', 'Hankook', 1500, 15, 73, 84, 'Летние', 'parts/tires_hankook.jpg'),
            (8, 'Yokohama Advan Sport V105', 'Yokohama', 1850, 18, 79, 86, 'Летние', 'parts/tires_yokohama.jpg'),
            (9, 'Nokian Hakkapeliitta 10', 'Nokian', 2200, 15, 90, 70, 'Зимние', 'parts/tires_nokian.jpg'),
            (10, 'Toyo Proxes Sport', 'Toyo', 1400, 14, 72, 83, 'Летние', 'parts/tires_toyo.jpg'),
            (11, 'Falken Azenis FK510', 'Falken', 1300, 13, 70, 82, 'Летние', 'parts/tires_falken.jpg'),
            (12, 'Kumho Ecsta PS91', 'Kumho', 1250, 12, 68, 81, 'Летние', 'parts/tires_kumho.jpg'),
            (13, 'BFGoodrich g-Force Sport COMP-2', 'BFGoodrich', 1650, 16, 76, 85, 'Летние', 'parts/tires_bfgoodrich.jpg'),
            (14, 'Vredestein Ultrac Vorti', 'Vredestein', 1550, 15, 74, 84, 'Летние', 'parts/tires_vredestein.jpg'),
            (15, 'Apollo Alnac 4G', 'Apollo', 900, 9, 65, 78, 'Всесезонные', 'parts/tires_apollo.jpg'),
            (16, 'Matador MP46 Hectorra 3', 'Matador', 950, 10, 66, 79, 'Всесезонные', 'parts/tires_matador.jpg'),
            (17, 'Triangle Sportex TH201', 'Triangle', 850, 8, 63, 77, 'Летние', 'parts/tires_triangle.jpg'),
            (18, 'Tigar Syneris', 'Tigar', 800, 7, 62, 76, 'Всесезонные', 'parts/tires_tigar.jpg'),
            (19, 'Lassa Impetus Revo', 'Lassa', 1000, 11, 67, 80, 'Летние', 'parts/tires_lassa.jpg'),
            (20, 'Cordiant Sport 3', 'Cordiant', 1100, 12, 69, 81, 'Летние', 'parts/tires_cordiant.jpg'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO parts_tires VALUES (?,?,?,?,?,?,?,?)
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
    • Европейские: 60+ моделей
    • Азиатские: 50+ моделей  
    • Американские: 20+ моделей
    
    ⚙️ *Тюнинг:*
    • 57 двигателей
    • 42 турбины
    • 30 выхлопных систем
    • 20 радиаторов
    • 21 система закиси азота
    • 10 подвесок
    • 20 видов покрышек
    
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
    
    # Добавляем админ-панель для админа
    if user_id == ADMIN_ID:
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
    • Китайская доступность
    
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
    
    european_brands = [
        "Volkswagen", "Mercedes-Benz", "BMW", "Audi", "Porsche",
        "Opel", "Smart", "Fiat", "Alfa Romeo", "Ferrari", "Lamborghini",
        "Maserati", "Pagani", "Renault", "Peugeot", "Citroën", "DS",
        "Alpine", "Bugatti", "Rolls-Royce", "Bentley", "Aston Martin",
        "McLaren", "Jaguar", "Land Rover", "Mini", "Lotus", "Volvo",
        "Koenigsegg", "Polestar", "Škoda", "Dacia", "SEAT", "Cupra", "Lada"
    ]
    
    keyboard = []
    for i in range(0, len(european_brands), 2):
        row = []
        if i < len(european_brands):
            row.append(InlineKeyboardButton(european_brands[i], callback_data=f"brand_{european_brands[i]}"))
        if i + 1 < len(european_brands):
            row.append(InlineKeyboardButton(european_brands[i+1], callback_data=f"brand_{european_brands[i+1]}"))
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
    context.user_data['part_index'] = 0
    
    # Здесь будет логика загрузки деталей по категории
    # Для примера, создадим заглушку
    
    parts_text = f"""
    ⚙️ *{category.upper()}*

    Выберите деталь для покупки:
    
    *Примечание:* Установка деталей увеличивает характеристики вашей активной машины.
    """
    
    # В реальности здесь нужно загружать детали из базы
    # Покажем пример для двигателей
    if category == "engines":
        parts_list = [
            "Volkswagen EA888 2.0 TSI - 5000 кредитов",
            "Mercedes-Benz M104 3.2 I6 - 8500 кредитов",
            "BMW B58 3.0 I6 - 12000 кредитов",
            "Porsche Mezger 3.8 H6 - 25000 кредитов"
        ]
    else:
        parts_list = ["Деталь 1", "Деталь 2", "Деталь 3"]
    
    keyboard = []
    for part in parts_list:
        keyboard.append([InlineKeyboardButton(part, callback_data=f"part_{part.split(' - ')[0]}")])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        parts_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return States.PARTS_LIST

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
        "*Текущий промокод:* RACINGBOT (1000 кредитов)",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return States.PROMO_CODE

async def process_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo_code = update.message.text.upper().strip()
    user_id = update.effective_user.id
    
    # Добавляем тестовый промокод если его нет
    if not db.check_promocode("RACINGBOT"):
        db.add_promocode("RACINGBOT", "money", 1000, 1000)
    
    if not db.check_promocode("WELCOME2024"):
        db.add_promocode("WELCOME2024", "money", 5000, 500)
    
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
    if user_id != ADMIN_ID:
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
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Добавить промокод", callback_data="admin_add_promo")],
        [InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
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
    if user_id != ADMIN_ID:
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
    db.add_promocode("FOLLOWERS", "followers", 100, 100)
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
                CallbackQueryHandler(shop_european, pattern='^shop_asian$'),  # Заглушка
                CallbackQueryHandler(shop_european, pattern='^shop_american$'),  # Заглушка
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
            States.PARTS_LIST: [
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
    application.add_handler(CommandHandler('admin', admin_command))
    
    # Запускаем бота
    print("=" * 50)
    print("RACING BOT ЗАПУЩЕН!")
    print(f"Бот содержит: 200+ машин, 57 двигателей, 42 турбины, 30 выхлопов")
    print("Добавлены промокоды: RACINGBOT, WELCOME2024, FOLLOWERS, SPEED")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
