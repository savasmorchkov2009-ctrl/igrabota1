import logging
import sqlite3
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from threading import Thread
from queue import Queue

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton
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
TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_IT"  # Замените на ваш токен
ADMINS = [5189651311, 5887846215]  # ID администраторов
DATABASE_NAME = "racing_bot.db"

# Состояния для ConversationHandler
(
    MAIN_MENU, CHOOSING_CAR, TRAINING, RACING, 
    SHOP_MENU, GARAGE, TUNING, MARKET,
    EUROPEAN_MARKET, ASIAN_MARKET, AMERICAN_MARKET,
    PARTS_SHOP, ENGINES, TURBOS, EXHAUSTS, RADIATORS,
    NITROUS, SHOCK_ABSORBERS, TIRES, DUEL, WAITING_DUEL
) = range(20)

# Класс для работы с базой данных
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()
        self.init_all_data()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
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
        
        # Таблица запчастей (общая структура)
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
    
    def init_all_data(self):
        cursor = self.conn.cursor()
        
        # Очистка старых данных (опционально)
        cursor.execute("DELETE FROM cars")
        cursor.execute("DELETE FROM parts")
        
        # Добавление начальных машин для обучения
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
        
        # Добавление европейских машин
        european_cars = [
            ("Volkswagen", "Golf", "european", 150, 8.2, 210, 25000, "vw_golf.jpg"),
            ("Volkswagen", "Passat", "european", 190, 7.5, 235, 35000, "vw_passat.jpg"),
            ("Mercedes-Benz", "C-Class", "european", 255, 6.0, 250, 45000, "merc_c_class.jpg"),
            ("Mercedes-Benz", "E-Class", "european", 367, 4.7, 250, 65000, "merc_e_class.jpg"),
            ("BMW", "5 Series", "european", 249, 6.0, 250, 55000, "bmw_5.jpg"),
            ("BMW", "X3", "european", 248, 6.3, 240, 52000, "bmw_x3.jpg"),
            ("Audi", "A6", "european", 340, 5.1, 250, 60000, "audi_a6.jpg"),
            ("Audi", "Q7", "european", 340, 5.9, 250, 70000, "audi_q7.jpg"),
            ("Porsche", "Panamera", "european", 330, 5.4, 270, 90000, "porsche_panamera.jpg"),
            ("Porsche", "Macan", "european", 265, 6.2, 232, 65000, "porsche_macan.jpg"),
            ("Opel", "Insignia", "european", 170, 8.9, 220, 30000, "opel_insignia_std.jpg"),
            ("Ferrari", "Roma", "european", 620, 3.4, 320, 250000, "ferrari_roma.jpg"),
            ("Ferrari", "F8 Tributo", "european", 720, 2.9, 340, 300000, "ferrari_f8.jpg"),
            ("Lamborghini", "Huracán", "european", 640, 3.2, 325, 280000, "lambo_huracan.jpg"),
            ("Lamborghini", "Aventador", "european", 770, 2.9, 350, 400000, "lambo_aventador.jpg"),
            ("Bugatti", "Chiron", "european", 1500, 2.4, 420, 3000000, "bugatti_chiron.jpg"),
            ("Rolls-Royce", "Cullinan", "european", 571, 5.2, 250, 350000, "rr_cullinan.jpg"),
            ("Bentley", "Flying Spur", "european", 635, 3.8, 333, 220000, "bentley_spur.jpg"),
            ("McLaren", "720S", "european", 720, 2.9, 341, 300000, "mclaren_720s.jpg"),
            ("McLaren", "Artura", "european", 680, 3.0, 330, 225000, "mclaren_artura.jpg"),
        ]
        
        cursor.executemany('''
            INSERT INTO cars (brand, model, region, base_hp, base_acceleration_0_100, 
                            base_top_speed, price, image_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', european_cars)
        
        # Добавление азиатских машин (сокращённый список)
        asian_cars = [
            ("Toyota", "Corolla AE86", "asian", 130, 8.9, 200, 25000, "toyota_ae86.jpg"),
            ("Toyota", "Supra A90", "asian", 382, 4.1, 250, 55000, "toyota_supra.jpg"),
            ("Nissan", "Skyline GT-R R34", "asian", 330, 4.9, 250, 120000, "nissan_gtr34.jpg"),
            ("Nissan", "GT-R R35", "asian", 570, 2.9, 315, 115000, "nissan_gtr35.jpg"),
            ("Honda", "Civic Type R", "asian", 320, 5.7, 275, 40000, "honda_civic_r.jpg"),
            ("Honda", "NSX", "asian", 573, 2.9, 307, 170000, "honda_nsx.jpg"),
            ("Mazda", "RX-7", "asian", 280, 5.3, 250, 80000, "mazda_rx7.jpg"),
            ("Subaru", "Impreza WRX STI", "asian", 310, 5.2, 250, 40000, "subaru_sti.jpg"),
            ("Mitsubishi", "Lancer Evolution X", "asian", 303, 5.1, 250, 45000, "mitsubishi_evo.jpg"),
            ("Lexus", "LC 500", "asian", 477, 4.4, 270, 95000, "lexus_lc.jpg"),
            ("Hyundai", "i30 N", "asian", 280, 6.1, 250, 35000, "hyundai_i30n.jpg"),
            ("Kia", "Stinger", "asian", 370, 4.7, 270, 50000, "kia_stinger.jpg"),
        ]
        
        cursor.executemany('''
            INSERT INTO cars (brand, model, region, base_hp, base_acceleration_0_100, 
                            base_top_speed, price, image_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', asian_cars)
        
        # Добавление американских машин
        american_cars = [
            ("Ford", "Mustang GT", "american", 460, 4.3, 250, 45000, "ford_mustang.jpg"),
            ("Chevrolet", "Corvette Stingray", "american", 495, 3.0, 312, 65000, "chevrolet_corvette.jpg"),
            ("Dodge", "Challenger Hellcat", "american", 717, 3.6, 315, 70000, "dodge_challenger.jpg"),
            ("Tesla", "Model S Plaid", "american", 1020, 2.1, 322, 140000, "tesla_model_s.jpg"),
            ("Jeep", "Wrangler", "american", 285, 7.5, 180, 40000, "jeep_wrangler.jpg"),
            ("Cadillac", "Escalade", "american", 420, 6.1, 180, 90000, "cadillac_escalade.jpg"),
            ("Chevrolet", "Camaro SS", "american", 455, 4.0, 250, 40000, "chevrolet_camaro.jpg"),
            ("Ford", "F-150 Raptor", "american", 450, 5.1, 180, 75000, "ford_raptor.jpg"),
            ("Dodge", "Charger SRT", "american", 485, 4.3, 265, 45000, "dodge_charger.jpg"),
            ("Chevrolet", "Silverado", "american", 420, 5.9, 180, 50000, "chevrolet_silverado.jpg"),
        ]
        
        cursor.executemany('''
            INSERT INTO cars (brand, model, region, base_hp, base_acceleration_0_100, 
                            base_top_speed, price, image_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', american_cars)
        
        # Добавление запчастей - ДВИГАТЕЛИ
        engines = [
            ("engines", "Volkswagen EA888 2.0 TSI", "2.0L турбированный двигатель", 40, -0.5, 15, 5000),
            ("engines", "BMW B58 3.0 TwinTurbo", "3.0L рядная шестерка с двойным турбо", 80, -1.2, 30, 12000),
            ("engines", "Porsche Mezger 3.8", "Оппозитный 6-цилиндровый двигатель", 120, -1.5, 40, 25000),
            ("engines", "Toyota 2JZ-GTE", "Легендарный 3.0L I6 TwinTurbo", 150, -1.8, 50, 30000),
            ("engines", "Nissan RB26DETT", "2.6L I6 TwinTurbo от Skyline GT-R", 140, -1.7, 45, 28000),
            ("engines", "Chevrolet LS3 V8", "6.2L V8 двигатель", 130, -1.3, 35, 15000),
            ("engines", "Ford Coyote V8 5.0", "5.0L V8 с 32 клапанами", 110, -1.1, 32, 14000),
            ("engines", "Ferrari F136 V8", "4.3L V8 от Ferrari 458", 180, -2.0, 60, 45000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', engines)
        
        # Добавление турбин
        turbos = [
            ("turbos", "Garrett GTX3582R", "Высокоэффективная турбина", 100, -0.8, 25, 8000),
            ("turbos", "BorgWarner EFR 8374", "Турбина с керамическими подшипниками", 120, -1.0, 30, 10000),
            ("turbos", "Mitsubishi TD05", "Надежная турбина для тюнинга", 60, -0.5, 15, 3000),
            ("turbos", "Precision Turbo 6266", "Турбина для дрэг-рейсинга", 140, -1.2, 35, 12000),
            ("turbos", "HKS GT2835", "Японская турбина для Street-тюнинга", 90, -0.7, 22, 7000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', turbos)
        
        # Добавление выхлопных систем
        exhausts = [
            ("exhausts", "Akrapovič Evolution", "Титановая выхлопная система", 15, -0.2, 10, 4000),
            ("exhausts", "Remus PowerSound", "Спортивная выхлопная система", 10, -0.1, 8, 2000),
            ("exhausts", "HKS Hi-Power", "Японская выхлопная система", 12, -0.15, 9, 2500),
            ("exhausts", "Borla Atak", "Американская выхлопная система", 18, -0.25, 12, 3500),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', exhausts)
        
        # Добавление радиаторов
        radiators = [
            ("radiators", "Mishimoto M-Line", "Алюминиевый радиатор", 5, 0, 5, 1000),
            ("radiators", "Koyo Racing", "Радиатор для трека", 8, 0, 8, 1500),
            ("radiators", "CSF Racing", "Трехрядный радиатор", 10, 0, 10, 2000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', radiators)
        
        # Добавление систем закиси азота
        nitrous = [
            ("nitrous", "NOS Sniper Kit", "Система закиси азота 100hp", 100, -0.5, 20, 5000),
            ("nitrous", "ZEX Nitrous Kit", "Сухая система закиси азота", 75, -0.4, 15, 3500),
            ("nitrous", "Nitrous Express EFI", "Продвинутая система впрыска", 150, -0.8, 30, 8000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', nitrous)
        
        # Добавление амортизаторов
        shock_absorbers = [
            ("shock_absorbers", "KW Variant 3", "Регулируемая подвеска", 0, -0.3, 0, 3000),
            ("shock_absorbers", "Öhlins Road & Track", "Высококачественные амортизаторы", 0, -0.4, 0, 4000),
            ("shock_absorbers", "Bilstein B8", "Спортивные амортизаторы", 0, -0.2, 0, 2000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', shock_absorbers)
        
        # Добавление покрышек
        tires = [
            ("tires", "Michelin Pilot Sport 4S", "Летние спортивные шины", 0, -0.4, 5, 1500),
            ("tires", "Pirelli P Zero", "Высокопроизводительные шины", 0, -0.3, 3, 1200),
            ("tires", "Toyoo Proxes Sport", "Дрэговые шины", 0, -0.6, 0, 2000),
        ]
        
        cursor.executemany('''
            INSERT INTO parts (category, name, description, hp_boost, acceleration_boost, 
                             top_speed_boost, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', tires)
        
        # Добавление промокодов
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
    
    # Методы для работы с пользователями
    def get_user(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    
    def create_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, balance)
            VALUES (?, ?, ?, ?, 10000)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()
    
    def update_user_balance(self, user_id: int, amount: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def update_user_followers(self, user_id: int, amount: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def update_user_rating(self, user_id: int, amount: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET rating = rating + ? WHERE user_id = ?", (amount, user_id))
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
        
        # Проверяем, есть ли у пользователя деньги
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_balance = cursor.fetchone()["balance"]
        
        cursor.execute("SELECT price FROM cars WHERE id = ?", (car_id,))
        car_price = cursor.fetchone()["price"]
        
        if user_balance >= car_price:
            # Снимаем деньги
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (car_price, user_id))
            
            # Добавляем машину пользователю
            cursor.execute('''
                INSERT INTO user_cars (user_id, car_id, is_active)
                VALUES (?, ?, 0)
            ''', (user_id, car_id))
            
            # Если это первая машина, делаем ее активной
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
        
        # Сначала снимаем активность со всех машин
        cursor.execute('''
            UPDATE user_cars SET is_active = 0 
            WHERE user_id = ?
        ''', (user_id,))
        
        # Устанавливаем активную машину
        cursor.execute('''
            UPDATE user_cars SET is_active = 1 
            WHERE user_id = ? AND car_id = ?
        ''', (user_id, car_id))
        
        # Обновляем current_car_id в users
        cursor.execute('''
            UPDATE users SET current_car_id = ? 
            WHERE user_id = ?
        ''', (car_id, user_id))
        
        self.conn.commit()
    
    # Методы для работы с запчастями
    def get_parts_by_category(self, category: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM parts WHERE category = ?", (category,))
        return cursor.fetchall()
    
    def buy_part(self, user_id: int, part_id: int):
        cursor = self.conn.cursor()
        
        # Получаем информацию о запчасти
        cursor.execute("SELECT * FROM parts WHERE id = ?", (part_id,))
        part = cursor.fetchone()
        
        if not part:
            return False
        
        # Проверяем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_balance = cursor.fetchone()["balance"]
        
        if user_balance >= part["price"]:
            # Снимаем деньги
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (part["price"], user_id))
            
            # Добавляем запчасть пользователю (без привязки к машине)
            cursor.execute('''
                INSERT INTO user_parts (user_id, part_id)
                VALUES (?, ?)
            ''', (user_id, part_id))
            
            self.conn.commit()
            return True
        return False
    
    def install_part(self, user_id: int, part_id: int, car_id: int):
        cursor = self.conn.cursor()
        
        # Обновляем запись в user_parts
        cursor.execute('''
            UPDATE user_parts SET car_id = ?
            WHERE user_id = ? AND part_id = ?
        ''', (car_id, user_id, part_id))
        
        # Получаем данные запчасти
        cursor.execute("SELECT * FROM parts WHERE id = ?", (part_id,))
        part = cursor.fetchone()
        
        # Обновляем характеристики машины
        cursor.execute('''
            UPDATE user_cars 
            SET tuning_hp = tuning_hp + ?,
                tuning_acceleration = tuning_acceleration + ?,
                tuning_top_speed = tuning_top_speed + ?
            WHERE user_id = ? AND car_id = ?
        ''', (part["hp_boost"], part["acceleration_boost"], part["top_speed_boost"], user_id, car_id))
        
        self.conn.commit()
    
    # Методы для работы с гонками
    def add_race(self, user_id: int, opponent_id: int, race_type: str, result: str, 
                 distance: int, race_time: float, reaction_time: float, 
                 earned_money: int, earned_followers: int, earned_rating: int):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO races (user_id, opponent_id, race_type, result, distance, 
                             time, reaction_time, earned_money, earned_followers, earned_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, opponent_id, race_type, result, distance, race_time, 
              reaction_time, earned_money, earned_followers, earned_rating))
        
        # Обновляем статистику пользователя
        if result == 'win':
            cursor.execute('''
                UPDATE users 
                SET wins = wins + 1, 
                    total_races = total_races + 1,
                    balance = balance + ?,
                    followers = followers + ?,
                    rating = rating + ?,
                    last_race_time = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (earned_money, earned_followers, earned_rating, user_id))
        else:
            cursor.execute('''
                UPDATE users 
                SET losses = losses + 1, 
                    total_races = total_races + 1,
                    rating = rating + ?,
                    last_race_time = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (earned_rating, user_id))
        
        self.conn.commit()
    
    # Методы для работы с промокодами
    def use_promocode(self, user_id: int, code: str):
        cursor = self.conn.cursor()
        
        # Проверяем существование промокода
        cursor.execute('''
            SELECT * FROM promocodes 
            WHERE code = ? AND is_active = 1
        ''', (code,))
        promocode = cursor.fetchone()
        
        if not promocode:
            return None
        
        # Проверяем, использовал ли пользователь уже этот промокод
        cursor.execute('''
            SELECT * FROM used_promocodes up
            JOIN promocodes p ON up.promocode_id = p.id
            WHERE up.user_id = ? AND p.code = ?
        ''', (user_id, code))
        
        if cursor.fetchone():
            return None
        
        # Начисляем награду
        if promocode["reward_type"] == "money":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                         (promocode["reward_value"], user_id))
        elif promocode["reward_type"] == "followers":
            cursor.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", 
                         (promocode["reward_value"], user_id))
        elif promocode["reward_type"] == "rating":
            cursor.execute("UPDATE users SET rating = rating + ? WHERE user_id = ?", 
                         (promocode["reward_value"], user_id))
        
        # Отмечаем промокод как использованный
        cursor.execute('''
            INSERT INTO used_promocodes (user_id, promocode_id)
            VALUES (?, ?)
        ''', (user_id, promocode["id"]))
        
        self.conn.commit()
        return promocode["reward_type"], promocode["reward_value"]
    
    # Методы для работы с дуэлями
    def create_duel(self, challenger_id: int, opponent_id: int, bet_amount: int = 0):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO duels (challenger_id, opponent_id, bet_amount)
            VALUES (?, ?, ?)
        ''', (challenger_id, opponent_id, bet_amount))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_duels(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT d.*, u.username as challenger_name
            FROM duels d
            JOIN users u ON d.challenger_id = u.user_id
            WHERE d.opponent_id = ? AND d.status = 'pending'
        ''', (user_id,))
        return cursor.fetchall()
    
    def update_duel_status(self, duel_id: int, status: str, winner_id: int = None):
        cursor = self.conn.cursor()
        
        if winner_id:
            cursor.execute('''
                UPDATE duels 
                SET status = ?, winner_id = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, winner_id, duel_id))
        else:
            cursor.execute('''
                UPDATE duels 
                SET status = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, duel_id))
        
        self.conn.commit()
    
    # Методы для получения топов
    def get_top_money(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, balance 
            FROM users 
            WHERE is_banned = 0
            ORDER BY balance DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_rating(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, rating 
            FROM users 
            WHERE is_banned = 0
            ORDER BY rating DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_followers(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, followers 
            FROM users 
            WHERE is_banned = 0
            ORDER BY followers DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_horsepower(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT uc.user_id, u.username, 
                   (c.base_hp + uc.tuning_hp) as total_hp,
                   c.brand, c.model
            FROM user_cars uc
            JOIN cars c ON uc.car_id = c.id
            JOIN users u ON uc.user_id = u.user_id
            WHERE uc.is_active = 1 AND u.is_banned = 0
            ORDER BY total_hp DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_acceleration(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT uc.user_id, u.username, 
                   (c.base_acceleration_0_100 + uc.tuning_acceleration) as total_acceleration,
                   c.brand, c.model
            FROM user_cars uc
            JOIN cars c ON uc.car_id = c.id
            JOIN users u ON uc.user_id = u.user_id
            WHERE uc.is_active = 1 AND u.is_banned = 0
            ORDER BY total_acceleration ASC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_speed(self, limit: int = 10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT uc.user_id, u.username, 
                   (c.base_top_speed + uc.tuning_top_speed) as total_speed,
                   c.brand, c.model
            FROM user_cars uc
            JOIN cars c ON uc.car_id = c.id
            JOIN users u ON uc.user_id = u.user_id
            WHERE uc.is_active = 1 AND u.is_banned = 0
            ORDER BY total_speed DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def search_user(self, username: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, rating
            FROM users 
            WHERE username LIKE ? OR first_name LIKE ?
            LIMIT 10
        ''', (f"%{username}%", f"%{username}%"))
        return cursor.fetchall()

# Глобальная переменная для базы данных
db = Database()

# Класс для управления активными гонками и дуэлями
class RaceManager:
    def __init__(self):
        self.active_races = {}
        self.duel_requests = {}
        self.race_queue = Queue()
    
    def start_race_timer(self, user_id: int, context):
        """Запускает таймер гонки"""
        time.sleep(5)  # 5 секунд ожидания старта
        
        if user_id in self.active_races:
            race_data = self.active_races[user_id]
            
            # Отправляем сообщение о старте
            context.bot.send_message(
                chat_id=user_id,
                text="🚦 ГОНКА НАЧАЛАСЬ! 🏁\n"
                     "Машина разгоняется...",
                reply_markup=InlineKeyboardMarkup([[]])
            )
            
            # Рассчитываем время гонки на основе характеристик машины
            car_data = db.get_active_car(user_id)
            if car_data:
                base_time = 15.0  # Базовое время на 500м
                
                # Влияние характеристик на время
                hp_factor = 500 / (car_data["base_hp"] + car_data["tuning_hp"])
                acc_factor = car_data["base_acceleration_0_100"] + car_data["tuning_acceleration"]
                
                race_time = base_time * (hp_factor / 100) * (acc_factor / 8.0)
                race_time = max(5.0, min(30.0, race_time))  # Ограничиваем время
                
                time.sleep(race_time)
                
                # Отправляем результаты
                reward_money = random.randint(500, 2000)
                reward_followers = random.randint(10, 50)
                
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"🏁 ФИНИШ!\n"
                         f"⏱ Время: {race_time:.2f} сек\n"
                         f"💰 Выигрыш: ${reward_money}\n"
                         f"👥 Подписчики: +{reward_followers}\n"
                         f"📈 Опыт: +100",
                    reply_markup=get_main_menu_keyboard()
                )
                
                # Сохраняем результаты
                db.add_race(
                    user_id=user_id,
                    opponent_id=0,
                    race_type="training",
                    result="win",
                    distance=500,
                    race_time=race_time,
                    reaction_time=5.0,
                    earned_money=reward_money,
                    earned_followers=reward_followers,
                    earned_rating=10
                )
                
                # Удаляем из активных гонок
                if user_id in self.active_races:
                    del self.active_races[user_id]

race_manager = RaceManager()

# Функции для создания клавиатур
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚗 Гараж", callback_data="garage"),
         InlineKeyboardButton("🏎 Гонки", callback_data="racing")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton("⚙️ Тюнинг", callback_data="tuning")],
        [InlineKeyboardButton("🏆 Топы", callback_data="top"),
         InlineKeyboardButton("💰 Рынок", callback_data="market")],
        [InlineKeyboardButton("👑 Профиль", callback_data="profile"),
         InlineKeyboardButton("⚔️ Дуэль", callback_data="duel")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="promocode")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_training_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Начать обучение", callback_data="start_training")],
        [InlineKeyboardButton("⏩ Пропустить", callback_data="skip_training")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_car_selection_keyboard(car_index: int, total_cars: int):
    keyboard = []
    
    if car_index > 0:
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"car_{car_index-1}")])
    
    row = []
    row.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"select_car_{car_index}"))
    
    if car_index < total_cars - 1:
        row.append(InlineKeyboardButton("Далее ▶️", callback_data=f"car_{car_index+1}"))
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def get_race_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚀 ГОТОВ!", callback_data="ready_to_race")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_shop_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇪🇺 Европейский", callback_data="european_market")],
        [InlineKeyboardButton("🇯🇵 Азиатский", callback_data="asian_market")],
        [InlineKeyboardButton("🇺🇸 Американский", callback_data="american_market")],
        [InlineKeyboardButton("🛠 Запчасти", callback_data="parts_shop")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_parts_shop_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚗 Двигатели", callback_data="engines")],
        [InlineKeyboardButton("🌀 Турбины", callback_data="turbos")],
        [InlineKeyboardButton("💨 Выхлопы", callback_data="exhausts")],
        [InlineKeyboardButton("🌡 Радиаторы", callback_data="radiators")],
        [InlineKeyboardButton("⚡️ Закись азота", callback_data="nitrous")],
        [InlineKeyboardButton("🛡 Амортизаторы", callback_data="shock_absorbers")],
        [InlineKeyboardButton("🌀 Покрышки", callback_data="tires")],
        [InlineKeyboardButton("🔙 Назад", callback_data="shop")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_top_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 По деньгам", callback_data="top_money")],
        [InlineKeyboardButton("⭐️ По рейтингу", callback_data="top_rating")],
        [InlineKeyboardButton("👥 По подписчикам", callback_data="top_followers")],
        [InlineKeyboardButton("🐎 По л.с.", callback_data="top_hp")],
        [InlineKeyboardButton("⚡️ По разгону", callback_data="top_acceleration")],
        [InlineKeyboardButton("🚀 По скорости", callback_data="top_speed")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Регистрируем пользователя
    db.create_user(user_id, user.username, user.first_name, user.last_name)
    
    # Отправляем приветственное сообщение с фото
    welcome_text = (
        f"🏁 Добро пожаловать в Racing Bot, {user.first_name}!\n\n"
        "Это мир высокоскоростных гонок, мощных машин и адреналина!\n\n"
        "📚 Рекомендуем пройти обучение, чтобы освоить основы игры."
    )
    
    # Здесь будет ваше фото (замените photo_url на путь к вашему фото)
    try:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=open("welcome.jpg", "rb") if os.path.exists("welcome.jpg") else None,
            caption=welcome_text,
            reply_markup=get_training_keyboard(),
            parse_mode=ParseMode.HTML
        )
    except:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_training_keyboard(),
            parse_mode=ParseMode.HTML
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

async def choose_first_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Сохраняем индекс текущей машины в контексте
    context.user_data["car_index"] = 0
    
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
    
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=open(car['image'], 'rb') if os.path.exists(car['image']) else None,
                caption=car_text
            ),
            reply_markup=get_car_selection_keyboard(0, 3)
        )
    except:
        await query.edit_message_text(
            text=car_text,
            reply_markup=get_car_selection_keyboard(0, 3)
        )
    
    return CHOOSING_CAR

async def show_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Получаем индекс машины из callback_data
    data = query.data
    car_index = int(data.split("_")[1])
    context.user_data["car_index"] = car_index
    
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
    
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=open(car['image'], 'rb') if os.path.exists(car['image']) else None,
                caption=car_text
            ),
            reply_markup=get_car_selection_keyboard(car_index, 3)
        )
    except:
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
    
    # ID машин в базе данных (предполагаем, что training cars имеют ID 1, 2, 3)
    car_ids = [1, 2, 3]
    selected_car_id = car_ids[car_index]
    
    # Покупаем машину (в обучении она бесплатная)
    db.buy_car(user_id, selected_car_id)
    db.set_active_car(user_id, selected_car_id)
    
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

async def ready_to_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Запускаем таймер гонки в отдельном потоке
    import threading
    race_thread = threading.Thread(
        target=race_manager.start_race_timer,
        args=(user_id, context)
    )
    race_thread.start()
    
    # Сохраняем время начала ожидания
    context.user_data["race_start_time"] = time.time()
    
    await query.edit_message_text(
        text="⏱ Ожидание старта...\n"
             "Нажмите 'СТАРТ!' через 5 секунд!\n\n"
             "Таймер: 5...",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏁 СТАРТ!", callback_data="race_start")
        ]])
    )

async def race_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    start_time = context.user_data.get("race_start_time", 0)
    current_time = time.time()
    reaction_time = current_time - start_time
    
    if reaction_time < 5.0:
        # Фальстарт
        await query.edit_message_text(
            text="❌ ФАЛЬСТАРТ!\n"
                 "Вы нажали слишком рано!\n"
                 "Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Повторить", callback_data="first_race")
            ]])
        )
    elif reaction_time > 6.0:
        # Поздний старт
        await query.edit_message_text(
            text="⚠️ ПОЗДНИЙ СТАРТ!\n"
                 "Вы задержались на старте!\n"
                 "Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Повторить", callback_data="first_race")
            ]])
        )
    else:
        # Успешный старт
        race_manager.active_races[user_id] = {
            "start_time": time.time(),
            "distance": 500,
            "status": "racing"
        }
        
        await query.edit_message_text(
            text="✅ ИДЕАЛЬНЫЙ СТАРТ!\n"
                 "⏱ Реакция: {:.2f} сек\n\n"
                 "Машина разгоняется...".format(reaction_time),
            reply_markup=InlineKeyboardMarkup([[]])
        )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user:
        profile_text = (
            f"👤 {user['first_name']} (@{user['username']})\n"
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
    active_car = db.get_active_car(user_id)
    
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
            f"   🐎 {car['base_hp'] + car['tuning_hp']} л.с. "
            f"⚡️ {car['base_acceleration_0_100'] + car['tuning_acceleration']:.1f} сек "
            f"🚀 {car['base_top_speed'] + car['tuning_top_speed']} км/ч\n\n"
        )
    
    keyboard = []
    for idx, car in enumerate(user_cars):
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
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM cars WHERE region = 'european' LIMIT 20")
    european_cars = cursor.fetchall()
    
    if not european_cars:
        await query.edit_message_text(
            text="🚫 Европейские машины временно недоступны.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="shop")
            ]])
        )
        return EUROPEAN_MARKET
    
    context.user_data["market_cars"] = european_cars
    context.user_data["market_index"] = 0
    
    car = european_cars[0]
    car_text = (
        f"🇪🇺 ЕВРОПЕЙСКИЙ АВТОПРОМ\n\n"
        f"🚗 {car['brand']} {car['model']}\n"
        f"💰 Цена: ${car['price']:,}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['base_hp']} л.с.\n"
        f"• Разгон 0-100: {car['base_acceleration_0_100']} сек\n"
        f"• Макс. скорость: {car['base_top_speed']} км/ч"
    )
    
    keyboard = []
    row = []
    if len(european_cars) > 1:
        row.append(InlineKeyboardButton("Далее ▶️", callback_data="market_next"))
    
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
    region_text = {
        "european": "🇪🇺 ЕВРОПЕЙСКИЙ АВТОПРОМ",
        "asian": "🇯🇵 АЗИАТСКИЙ АВТОПРОМ", 
        "american": "🇺🇸 АМЕРИКАНСКИЙ АВТОПРОМ"
    }.get(car["region"], "МАГАЗИН")
    
    car_text = (
        f"{region_text}\n\n"
        f"🚗 {car['brand']} {car['model']}\n"
        f"💰 Цена: ${car['price']:,}\n\n"
        f"⚙️ Характеристики:\n"
        f"• Лошадиные силы: {car['base_hp']} л.с.\n"
        f"• Разгон 0-100: {car['base_acceleration_0_100']} сек\n"
        f"• Макс. скорость: {car['base_top_speed']} км/ч"
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
    
    return EUROPEAN_MARKET if car["region"] == "european" else ASIAN_MARKET if car["region"] == "asian" else AMERICAN_MARKET

async def buy_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    car_id = int(data.split("_")[2])
    
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

async def parts_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🛠 МАГАЗИН ЗАПЧАСТЕЙ\n\n"
             "Выберите категорию запчастей:",
        reply_markup=get_parts_shop_keyboard()
    )
    
    return PARTS_SHOP

async def show_parts_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category_map = {
        "engines": ("🚗 ДВИГАТЕЛИ", ENGINES),
        "turbos": ("🌀 ТУРБИНЫ", TURBOS),
        "exhausts": ("💨 ВЫХЛОПНЫЕ СИСТЕМЫ", EXHAUSTS),
        "radiators": ("🌡 РАДИАТОРЫ", RADIATORS),
        "nitrous": ("⚡️ СИСТЕМЫ ЗАКИСИ АЗОТА", NITROUS),
        "shock_absorbers": ("🛡 АМОРТИЗАТОРЫ", SHOCK_ABSORBERS),
        "tires": ("🌀 ПОКРЫШКИ", TIRES)
    }
    
    data = query.data
    if data not in category_map:
        return await parts_shop(update, context)
    
    category_name, state = category_map[data]
    parts = db.get_parts_by_category(data)
    
    if not parts:
        await query.edit_message_text(
            text=f"🚫 {category_name} временно недоступны.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="parts_shop")
            ]])
        )
        return state
    
    context.user_data["parts_list"] = parts
    context.user_data["parts_index"] = 0
    context.user_data["parts_category"] = data
    
    part = parts[0]
    part_text = (
        f"{category_name}\n\n"
        f"🛠 {part['name']}\n"
        f"📝 {part['description']}\n"
        f"💰 Цена: ${part['price']:,}\n\n"
        f"⚙️ Улучшения:\n"
        f"• +{part['hp_boost']} л.с.\n"
        f"• {part['acceleration_boost']:.1f} сек к разгону\n"
        f"• +{part['top_speed_boost']} км/ч к скорости"
    )
    
    keyboard = []
    if len(parts) > 1:
        keyboard.append([
            InlineKeyboardButton("Далее ▶️", callback_data="parts_next")
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Купить", callback_data=f"buy_part_{part['id']}"),
        InlineKeyboardButton("🔙 Назад", callback_data="parts_shop")
    ])
    
    await query.edit_message_text(
        text=part_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return state

async def parts_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current_index = context.user_data.get("parts_index", 0)
    parts = context.user_data.get("parts_list", [])
    category = context.user_data.get("parts_category", "")
    
    category_names = {
        "engines": "🚗 ДВИГАТЕЛИ",
        "turbos": "🌀 ТУРБИНЫ", 
        "exhausts": "💨 ВЫХЛОПНЫЕ СИСТЕМЫ",
        "radiators": "🌡 РАДИАТОРЫ",
        "nitrous": "⚡️ СИСТЕМЫ ЗАКИСИ АЗОТА",
        "shock_absorbers": "🛡 АМОРТИЗАТОРЫ",
        "tires": "🌀 ПОКРЫШКИ"
    }
    
    if data == "parts_next" and current_index < len(parts) - 1:
        current_index += 1
    elif data == "parts_prev" and current_index > 0:
        current_index -= 1
    
    context.user_data["parts_index"] = current_index
    
    part = parts[current_index]
    part_text = (
        f"{category_names.get(category, 'ЗАПЧАСТИ')}\n\n"
        f"🛠 {part['name']}\n"
        f"📝 {part['description']}\n"
        f"💰 Цена: ${part['price']:,}\n\n"
        f"⚙️ Улучшения:\n"
        f"• +{part['hp_boost']} л.с.\n"
        f"• {part['acceleration_boost']:.1f} сек к разгону\n"
        f"• +{part['top_speed_boost']} км/ч к скорости"
    )
    
    keyboard = []
    row = []
    
    if current_index > 0:
        row.append(InlineKeyboardButton("◀️ Назад", callback_data="parts_prev"))
    
    if current_index < len(parts) - 1:
        if row:
            row.append(InlineKeyboardButton("Далее ▶️", callback_data="parts_next"))
        else:
            row.append(InlineKeyboardButton("Далее ▶️", callback_data="parts_next"))
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("✅ Купить", callback_data=f"buy_part_{part['id']}"),
        InlineKeyboardButton("🔙 Назад", callback_data="parts_shop")
    ])
    
    await query.edit_message_text(
        text=part_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Возвращаем соответствующее состояние
    state_map = {
        "engines": ENGINES,
        "turbos": TURBOS,
        "exhausts": EXHAUSTS,
        "radiators": RADIATORS,
        "nitrous": NITROUS,
        "shock_absorbers": SHOCK_ABSORBERS,
        "tires": TIRES
    }
    
    return state_map.get(category, PARTS_SHOP)

async def buy_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    part_id = int(data.split("_")[2])
    
    success = db.buy_part(user_id, part_id)
    
    if success:
        await query.edit_message_text(
            text="✅ Запчасть куплена!\n"
                 "Установите ее на машину в разделе тюнинга.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚙️ Тюнинг", callback_data="tuning"),
                InlineKeyboardButton("🛒 Продолжить покупки", callback_data="parts_shop")
            ]])
        )
    else:
        await query.edit_message_text(
            text="❌ Недостаточно средств!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏎 Заработать деньги", callback_data="racing"),
                InlineKeyboardButton("🔙 Назад", callback_data="parts_shop")
            ]])
        )
    
    return PARTS_SHOP

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
        f"Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛠 Установить запчасти", callback_data="install_parts")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=car_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return TUNING

async def top_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🏆 ТОП ИГРОКОВ\n\n"
             "Выберите категорию:",
        reply_markup=get_top_keyboard()
    )
    
    return MAIN_MENU

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    top_name = ""
    top_data = []
    
    if data == "top_money":
        top_name = "💰 ТОП ПО ДЕНЬГАМ"
        top_data = db.get_top_money(10)
    elif data == "top_rating":
        top_name = "⭐️ ТОП ПО РЕЙТИНГУ"
        top_data = db.get_top_rating(10)
    elif data == "top_followers":
        top_name = "👥 ТОП ПО ПОДПИСЧИКАМ"
        top_data = db.get_top_followers(10)
    elif data == "top_hp":
        top_name = "🐎 ТОП ПО ЛОШАДИНЫМ СИЛАМ"
        top_data = db.get_top_horsepower(10)
    elif data == "top_acceleration":
        top_name = "⚡️ ТОП ПО РАЗГОНУ 0-100"
        top_data = db.get_top_acceleration(10)
    elif data == "top_speed":
        top_name = "🚀 ТОП ПО МАКСИМАЛЬНОЙ СКОРОСТИ"
        top_data = db.get_top_speed(10)
    else:
        return await top_menu(update, context)
    
    if not top_data:
        await query.edit_message_text(
            text=f"🚫 {top_name} пока пуст.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="top")
            ]])
        )
        return MAIN_MENU
    
    top_text = f"{top_name}\n\n"
    
    for idx, item in enumerate(top_data, 1):
        if data == "top_hp":
            top_text += f"{idx}. {item['username']} - {item['total_hp']} л.с. ({item['brand']} {item['model']})\n"
        elif data == "top_acceleration":
            top_text += f"{idx}. {item['username']} - {item['total_acceleration']:.1f} сек ({item['brand']} {item['model']})\n"
        elif data == "top_speed":
            top_text += f"{idx}. {item['username']} - {item['total_speed']} км/ч ({item['brand']} {item['model']})\n"
        else:
            value = item.get('balance', item.get('rating', item.get('followers', 0)))
            top_text += f"{idx}. {item['username']} - {value:,}\n"
    
    keyboard = [
        [InlineKeyboardButton("🏆 Другие топы", callback_data="top")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=top_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return MAIN_MENU

async def duel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, есть ли активные вызовы
    pending_duels = db.get_pending_duels(user_id)
    
    duel_text = "⚔️ ДУЭЛИ\n\n"
    
    if pending_duels:
        duel_text += "📨 Вам бросили вызов:\n"
        for duel in pending_duels:
            duel_text += f"• {duel['challenger_name']} (ID: {duel['challenger_id']})\n"
        
        keyboard = []
        for duel in pending_duels:
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Принять вызов от {duel['challenger_name']}",
                    callback_data=f"accept_duel_{duel['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🎯 Вызвать на дуэль", callback_data="challenge_player"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
    else:
        duel_text += "Бросьте вызов другому игроку или дождитесь вызова."
        
        keyboard = [
            [InlineKeyboardButton("🎯 Вызвать на дуэль", callback_data="challenge_player")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
    
    await query.edit_message_text(
        text=duel_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return DUEL

async def challenge_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🎯 ВЫЗОВ НА ДУЭЛЬ\n\n"
             "Введите username игрока, которого хотите вызвать:\n"
             "Например: @username или username",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="duel")
        ]])
    )
    
    return WAITING_DUEL

async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.message.text.strip().replace('@', '')
    
    # Ищем пользователя
    users = db.search_user(username)
    
    if not users:
        await update.message.reply_text(
            "🚫 Игрок не найден.\n"
            "Попробуйте еще раз:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="duel")
            ]])
        )
        return WAITING_DUEL
    
    context.user_data["search_results"] = users
    
    users_text = "👥 НАЙДЕННЫЕ ИГРОКИ:\n\n"
    keyboard = []
    
    for idx, user in enumerate(users[:5], 1):
        users_text += f"{idx}. {user['username']} ({user['first_name']}) - Рейтинг: {user['rating']}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"⚔️ Вызвать {user['username']}",
                callback_data=f"challenge_{user['user_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="duel")
    ])
    
    await update.message.reply_text(
        users_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_DUEL

async def send_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    opponent_id = int(data.split("_")[1])
    
    # Создаем дуэль
    duel_id = db.create_duel(user_id, opponent_id)
    
    # Отправляем уведомление противнику
    try:
        opponent = db.get_user(opponent_id)
        challenger = db.get_user(user_id)
        
        await context.bot.send_message(
            chat_id=opponent_id,
            text=f"⚔️ ВАМ БРОСИЛИ ВЫЗОВ!\n\n"
                 f"Игрок: {challenger['username']}\n"
                 f"Рейтинг: {challenger['rating']}\n\n"
                 f"Принять вызов?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Принять", callback_data=f"accept_duel_{duel_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_duel_{duel_id}")
            ]])
        )
        
        await query.edit_message_text(
            text="✅ Вызов отправлен!\n"
                 "Ожидайте ответа от противника.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="duel")
            ]])
        )
    except:
        await query.edit_message_text(
            text="❌ Не удалось отправить вызов.\n"
                 "Возможно, игрок заблокировал бота.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="duel")
            ]])
        )
    
    return DUEL

async def accept_duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    duel_id = int(data.split("_")[2])
    
    # Обновляем статус дуэли
    db.update_duel_status(duel_id, "accepted")
    
    await query.edit_message_text(
        text="✅ Вы приняли вызов!\n"
             "Подготовьтесь к гонке...",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏎 Начать гонку", callback_data=f"start_duel_{duel_id}")
        ]])
    )
    
    return DUEL

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
    
    return MAIN_MENU

async def activate_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    result = db.use_promocode(user_id, code)
    
    if result:
        reward_type, value = result
        reward_text = {
            "money": f"💰 {value:,} денег",
            "followers": f"👥 {value:,} подписчиков", 
            "rating": f"⭐️ {value:,} рейтинга"
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

async def admin_add_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /addpromo <code> <type> <value>\n"
                                       "Типы: money, followers, rating")
        return
    
    code = context.args[0].upper()
    reward_type = context.args[1]
    value = int(context.args[2])
    
    if reward_type not in ["money", "followers", "rating"]:
        await update.message.reply_text("❌ Неверный тип награды. Используйте: money, followers, rating")
        return
    
    cursor = db.conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO promocodes (code, reward_type, reward_value)
            VALUES (?, ?, ?)
        ''', (code, reward_type, value))
        db.conn.commit()
        
        await update.message.reply_text(f"✅ Промокод {code} добавлен.")
    except:
        await update.message.reply_text("❌ Ошибка при добавлении промокода.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = db.conn.cursor()
    
    # Получаем статистику
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as active FROM users WHERE last_race_time > datetime('now', '-7 days')")
    active_users = cursor.fetchone()["active"]
    
    cursor.execute("SELECT SUM(balance) as total_money FROM users")
    total_money = cursor.fetchone()["total_money"] or 0
    
    cursor.execute("SELECT COUNT(*) as total_races FROM races")
    total_races = cursor.fetchone()["total_races"]
    
    stats_text = (
        "📊 СТАТИСТИКА БОТА\n\n"
        f"👥 Всего пользователей: {total_users:,}\n"
        f"🎮 Активных (7 дней): {active_users:,}\n"
        f"💰 Общая сумма денег: ${total_money:,}\n"
        f"🏎 Всего гонок: {total_races:,}"
    )
    
    await update.message.reply_text(stats_text)

# Обработка неизвестных команд
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Неизвестная команда. Используйте /start для начала игры."
    )

# Основная функция
def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", admin_ban))
    application.add_handler(CommandHandler("unban", admin_unban))
    application.add_handler(CommandHandler("addmoney", admin_add_money))
    application.add_handler(CommandHandler("addpromo", admin_add_promo))
    application.add_handler(CommandHandler("stats", admin_stats))
    
    # Conversation Handler для основного потока
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
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
                CallbackQueryHandler(show_car, pattern="^car_"),
                CallbackQueryHandler(select_car, pattern="^select_car_"),
            ],
            RACING: [
                CallbackQueryHandler(first_race, pattern="^first_race$"),
                CallbackQueryHandler(ready_to_race, pattern="^ready_to_race$"),
                CallbackQueryHandler(race_start, pattern="^race_start$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            SHOP_MENU: [
                CallbackQueryHandler(european_market, pattern="^european_market$"),
                CallbackQueryHandler(asian_market, pattern="^asian_market$"),
                CallbackQueryHandler(american_market, pattern="^american_market$"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            EUROPEAN_MARKET: [
                CallbackQueryHandler(market_navigation, pattern="^market_"),
                CallbackQueryHandler(buy_car, pattern="^buy_car_"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
            ],
            ASIAN_MARKET: [
                CallbackQueryHandler(market_navigation, pattern="^market_"),
                CallbackQueryHandler(buy_car, pattern="^buy_car_"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
            ],
            AMERICAN_MARKET: [
                CallbackQueryHandler(market_navigation, pattern="^market_"),
                CallbackQueryHandler(buy_car, pattern="^buy_car_"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
            ],
            PARTS_SHOP: [
                CallbackQueryHandler(show_parts_category, pattern="^engines$|^turbos$|^exhausts$|^radiators$|^nitrous$|^shock_absorbers$|^tires$"),
                CallbackQueryHandler(shop_menu, pattern="^shop$"),
            ],
            ENGINES: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            TURBOS: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            EXHAUSTS: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            RADIATORS: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            NITROUS: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            SHOCK_ABSORBERS: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            TIRES: [
                CallbackQueryHandler(parts_navigation, pattern="^parts_"),
                CallbackQueryHandler(buy_part, pattern="^buy_part_"),
                CallbackQueryHandler(parts_shop, pattern="^parts_shop$"),
            ],
            DUEL: [
                CallbackQueryHandler(challenge_player, pattern="^challenge_player$"),
                CallbackQueryHandler(accept_duel, pattern="^accept_duel_"),
                CallbackQueryHandler(send_challenge, pattern="^challenge_"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            ],
            WAITING_DUEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_player),
                CallbackQueryHandler(duel_menu, pattern="^duel$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv_handler)
    
    # Обработчик промокодов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, activate_promocode))
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Запуск бота
    print("============================================================")
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMINS}")
    print("🎁 Промокоды: WELCOME2024, RACINGBOT, SPEED, FOLLOWERS, RICH")
    print("⚔️ Дуэли включены, время реакции: 5-6 секунд")
    print("💰 Улучшенная экономика, 5 видов топов")
    print("⚙️ Магазин запчастей, тюнинг машин")
    print("============================================================")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

