#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlite3
import asyncio
import os
import random
import re
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes, CallbackContext
)
from telegram.constants import ParseMode

# ==================== НАСТРОЙКИ ====================
TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"  # Замените на реальный токен от BotFather
ADMIN_IDS = [5887846215, 5189651311]  # Список ID администраторов

# Состояния для ConversationHandler
(CHOOSE_NAME, MAIN_MENU, CHOOSE_CAR, RACE_WAIT, RACE_START, DUEL_SEARCH, 
 ADMIN_PANEL, PROMO_CODE, TUNING_MENU, DEALERSHIP_MENU, PARTS_SHOP_MENU) = range(11)

# ==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('racing_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                balance INTEGER DEFAULT 50000,
                rating INTEGER DEFAULT 1000,
                followers INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                current_car_id INTEGER,
                banned BOOLEAN DEFAULT 0,
                last_race_time INTEGER DEFAULT 0,
                duel_cooldown INTEGER DEFAULT 0,
                promo_used TEXT DEFAULT '',
                register_date INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица машин пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                car_id TEXT,
                engine_id TEXT,
                turbo_id TEXT,
                exhaust_id TEXT,
                radiator_id TEXT,
                nos_id TEXT,
                suspension_id TEXT,
                tires_id TEXT,
                is_selected BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица базовых машин (каталог)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars_catalog (
                id TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                brand TEXT,
                price INTEGER,
                hp INTEGER,
                accel REAL,
                top_speed INTEGER,
                photo TEXT
            )
        ''')
        
        # Таблицы запчастей
        self.create_parts_tables()
        
        # Таблица дуэлей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                opponent_id INTEGER,
                status TEXT,
                winner_id INTEGER,
                time INTEGER
            )
        ''')
        
        # Таблица промокодов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward INTEGER,
                uses INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 1
            )
        ''')
        
        self.conn.commit()
        self.init_catalog_data()
        self.init_promocodes()

    def create_parts_tables(self):
        # Двигатели
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_engines (
                id TEXT PRIMARY KEY,
                name TEXT,
                hp_bonus INTEGER,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Турбины
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_turbos (
                id TEXT PRIMARY KEY,
                name TEXT,
                hp_bonus INTEGER,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Выхлопы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_exhausts (
                id TEXT PRIMARY KEY,
                name TEXT,
                hp_bonus INTEGER,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Радиаторы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_radiators (
                id TEXT PRIMARY KEY,
                name TEXT,
                hp_bonus INTEGER,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Закись азота
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_nos (
                id TEXT PRIMARY KEY,
                name TEXT,
                hp_bonus INTEGER,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Подвеска
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_suspensions (
                id TEXT PRIMARY KEY,
                name TEXT,
                handling_bonus REAL,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        # Покрышки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_tires (
                id TEXT PRIMARY KEY,
                name TEXT,
                grip_bonus REAL,
                price INTEGER,
                description TEXT,
                photo TEXT
            )
        ''')
        
        self.conn.commit()
        self.insert_all_parts()

    def init_catalog_data(self):
        self.cursor.execute("SELECT COUNT(*) FROM cars_catalog")
        if self.cursor.fetchone()[0] == 0:
            # Европейские машины
            european_cars = [
                ("vw_golf", "Volkswagen Golf", "Европа", "Volkswagen", 25000, 150, 8.5, 210, "photo"),
                ("vw_passat", "Volkswagen Passat", "Европа", "Volkswagen", 32000, 190, 7.2, 230, "photo"),
                ("mb_cclass", "Mercedes-Benz C-Class", "Европа", "Mercedes-Benz", 45000, 255, 6.0, 250, "photo"),
                ("mb_eclass", "Mercedes-Benz E-Class", "Европа", "Mercedes-Benz", 65000, 367, 4.8, 270, "photo"),
                ("bmw_5series", "BMW 5 Series", "Европа", "BMW", 60000, 340, 4.9, 260, "photo"),
                ("bmw_x3", "BMW X3", "Европа", "BMW", 55000, 300, 5.5, 245, "photo"),
                ("audi_a6", "Audi A6", "Европа", "Audi", 58000, 340, 5.1, 260, "photo"),
                ("audi_q7", "Audi Q7", "Европа", "Audi", 70000, 400, 5.2, 250, "photo"),
                ("porsche_panamera", "Porsche Panamera", "Европа", "Porsche", 120000, 550, 3.5, 310, "photo"),
                ("porsche_macan", "Porsche Macan", "Европа", "Porsche", 90000, 440, 4.3, 280, "photo"),
                ("opel_insignia", "Opel Insignia OPC", "Европа", "Opel", 40000, 325, 5.8, 270, "photo"),
                ("smart_forfour", "Smart ForFour", "Европа", "Smart", 18000, 109, 11.5, 180, "photo"),
                ("fiat_tipo", "Fiat Tipo", "Европа", "Fiat", 22000, 130, 9.5, 200, "photo"),
                ("alfa_giulietta", "Alfa Romeo Giulietta", "Европа", "Alfa Romeo", 38000, 240, 6.0, 245, "photo"),
                ("ferrari_roma", "Ferrari Roma", "Европа", "Ferrari", 250000, 620, 3.4, 320, "photo"),
                ("ferrari_f8", "Ferrari F8 Tributo", "Европа", "Ferrari", 350000, 720, 2.9, 340, "photo"),
                ("lambo_huracan", "Lamborghini Huracán", "Европа", "Lamborghini", 280000, 640, 2.9, 325, "photo"),
                ("lambo_aventador", "Lamborghini Aventador", "Европа", "Lamborghini", 450000, 770, 2.8, 350, "photo"),
                ("maserati_ghibli", "Maserati Ghibli", "Европа", "Maserati", 95000, 430, 4.7, 285, "photo"),
                ("pagani_zonda", "Pagani Zonda", "Европа", "Pagani", 1500000, 800, 2.6, 360, "photo"),
                ("renault_megane", "Renault Megane", "Европа", "Renault", 30000, 205, 7.1, 235, "photo"),
                ("renault_kadjar", "Renault Kadjar", "Европа", "Renault", 35000, 160, 8.9, 210, "photo"),
                ("peugeot_208", "Peugeot 208", "Европа", "Peugeot", 25000, 130, 8.7, 200, "photo"),
                ("peugeot_508", "Peugeot 508", "Европа", "Peugeot", 42000, 225, 7.3, 240, "photo"),
                ("citroen_c4", "Citroën C4", "Европа", "Citroën", 28000, 155, 8.1, 210, "photo"),
                ("citroen_c5", "Citroën C5 Aircross", "Европа", "Citroën", 38000, 180, 8.0, 220, "photo"),
                ("ds9", "DS 9", "Европа", "DS", 55000, 250, 7.5, 245, "photo"),
                ("alpine_a310", "Alpine A310", "Европа", "Alpine", 75000, 300, 4.5, 270, "photo"),
                ("bugatti_chiron", "Bugatti Chiron", "Европа", "Bugatti", 3000000, 1500, 2.4, 420, "photo"),
                ("rolls_cullinan", "Rolls-Royce Cullinan", "Европа", "Rolls-Royce", 350000, 571, 5.0, 250, "photo"),
                ("bentley_flyingspur", "Bentley Flying Spur", "Европа", "Bentley", 250000, 635, 3.8, 333, "photo"),
                ("aston_vantage", "Aston Martin Vantage", "Европа", "Aston Martin", 180000, 510, 3.6, 314, "photo"),
                ("aston_v12", "Aston Martin V12 Vantage", "Европа", "Aston Martin", 220000, 700, 3.4, 330, "photo"),
                ("mclaren_720s", "McLaren 720S", "Европа", "McLaren", 320000, 720, 2.9, 341, "photo"),
                ("mclaren_artura", "McLaren Artura", "Европа", "McLaren", 240000, 680, 3.0, 330, "photo"),
                ("jaguar_fpace", "Jaguar F-PACE", "Европа", "Jaguar", 70000, 400, 5.1, 260, "photo"),
                ("jaguar_xe", "Jaguar XE", "Европа", "Jaguar", 55000, 300, 5.5, 250, "photo"),
                ("landrover_discovery", "Land Rover Discovery Sport", "Европа", "Land Rover", 60000, 290, 7.0, 225, "photo"),
                ("mini_countryman", "Mini Countryman", "Европа", "Mini", 45000, 190, 7.5, 225, "photo"),
                ("lotus_exige", "Lotus Exige", "Европа", "Lotus", 90000, 430, 3.3, 290, "photo"),
                ("volvo_s60", "Volvo S60", "Европа", "Volvo", 50000, 250, 6.5, 240, "photo"),
                ("volvo_v90", "Volvo V90", "Европа", "Volvo", 60000, 310, 6.0, 250, "photo"),
                ("koenigsegg_jesko", "Koenigsegg Jesko", "Европа", "Koenigsegg", 3500000, 1600, 2.5, 480, "photo"),
                ("polestar_1", "Polestar 1", "Европа", "Polestar", 155000, 619, 4.2, 305, "photo"),
                ("skoda_kodiaq", "Škoda Kodiaq", "Европа", "Škoda", 40000, 190, 8.0, 215, "photo"),
                ("skoda_fabia", "Škoda Fabia", "Европа", "Škoda", 22000, 110, 10.1, 195, "photo"),
                ("dacia_logan", "Dacia Logan", "Европа", "Dacia", 18000, 90, 11.9, 180, "photo"),
                ("dacia_jogger", "Dacia Jogger", "Европа", "Dacia", 22000, 110, 10.5, 190, "photo"),
                ("seat_ateca", "SEAT Ateca", "Европа", "SEAT", 35000, 150, 9.0, 200, "photo"),
                ("cupra_leon", "Cupra Leon", "Европа", "Cupra", 45000, 310, 4.9, 260, "photo"),
                ("lada_granta", "Lada Granta", "Европа", "Lada", 12000, 106, 11.0, 185, "photo"),
                ("lada_xray", "Lada XRAY", "Европа", "Lada", 15000, 122, 10.4, 190, "photo"),
                ("renault_arkana", "Renault Arkana", "Европа", "Renault", 32000, 150, 9.2, 205, "photo"),
                ("hyundai_tucson", "Hyundai Tucson", "Азия", "Hyundai", 38000, 190, 8.9, 210, "photo"),
                ("kia_ceed", "Kia Ceed", "Азия", "Kia", 32000, 140, 9.2, 205, "photo"),
                ("toyota_yaris", "Toyota Yaris", "Азия", "Toyota", 25000, 116, 10.2, 190, "photo"),
                ("ford_focus", "Ford Focus", "Америка", "Ford", 30000, 160, 8.5, 220, "photo"),
                ("ford_kuga", "Ford Kuga", "Америка", "Ford", 35000, 190, 8.9, 215, "photo"),
                ("nissan_qashqai", "Nissan Qashqai", "Азия", "Nissan", 33000, 150, 9.5, 200, "photo"),
                ("suzuki_swace", "Suzuki Swace", "Азия", "Suzuki", 28000, 122, 10.5, 185, "photo"),
            ]
            
            # Азиатские машины
            asian_cars = [
                ("toyota_corolla", "Toyota Corolla", "Азия", "Toyota", 28000, 169, 8.0, 210, "photo"),
                ("toyota_camry", "Toyota Camry", "Азия", "Toyota", 40000, 249, 7.5, 230, "photo"),
                ("toyota_rav4", "Toyota RAV4", "Азия", "Toyota", 38000, 203, 8.4, 215, "photo"),
                ("toyota_landcruiser", "Toyota Land Cruiser", "Азия", "Toyota", 80000, 309, 8.0, 210, "photo"),
                ("toyota_hilux", "Toyota Hilux", "Азия", "Toyota", 35000, 204, 10.0, 190, "photo"),
                ("toyota_supra", "Toyota Supra", "Азия", "Toyota", 55000, 382, 3.9, 280, "photo"),
                ("toyota_gt86", "Toyota GR86", "Азия", "Toyota", 35000, 235, 6.3, 235, "photo"),
                ("toyota_chaser", "Toyota Chaser", "Азия", "Toyota", 30000, 280, 5.9, 250, "photo"),
                ("toyota_mark2", "Toyota Mark II", "Азия", "Toyota", 28000, 280, 6.0, 245, "photo"),
                ("toyota_cresta", "Toyota Cresta", "Азия", "Toyota", 27000, 280, 6.1, 245, "photo"),
                ("toyota_soarer", "Toyota Soarer", "Азия", "Toyota", 35000, 310, 5.5, 260, "photo"),
                ("toyota_altezza", "Toyota Altezza", "Азия", "Toyota", 25000, 210, 7.0, 230, "photo"),
                ("toyota_aristo", "Toyota Aristo", "Азия", "Toyota", 32000, 280, 6.2, 245, "photo"),
                ("toyota_crown", "Toyota Crown", "Азия", "Toyota", 45000, 315, 6.0, 250, "photo"),
                ("toyota_celsior", "Toyota Celsior", "Азия", "Toyota", 40000, 280, 6.5, 240, "photo"),
                ("toyota_mr2", "Toyota MR2", "Азия", "Toyota", 25000, 245, 5.7, 245, "photo"),
                ("toyota_celica", "Toyota Celica GT-Four", "Азия", "Toyota", 28000, 255, 6.0, 240, "photo"),
                ("toyota_starlet", "Toyota Starlet", "Азия", "Toyota", 15000, 135, 8.5, 195, "photo"),
                ("toyota_gr_yaris", "Toyota GR Yaris", "Азия", "Toyota", 45000, 272, 5.5, 230, "photo"),
                ("toyota_vios", "Toyota Vios", "Азия", "Toyota", 20000, 107, 10.5, 185, "photo"),
                ("toyota_fortuner", "Toyota Fortuner", "Азия", "Toyota", 40000, 204, 9.5, 195, "photo"),
                ("toyota_progres", "Toyota Progres", "Азия", "Toyota", 30000, 280, 6.8, 230, "photo"),
                ("toyota_carina", "Toyota Carina ED", "Азия", "Toyota", 22000, 160, 8.5, 200, "photo"),
                ("toyota_sprinter", "Toyota Sprinter", "Азия", "Toyota", 20000, 145, 8.8, 195, "photo"),
                ("toyota_corona", "Toyota Corona", "Азия", "Toyota", 22000, 150, 9.0, 195, "photo"),
                ("lexus_is", "Lexus IS", "Азия", "Lexus", 45000, 311, 5.7, 250, "photo"),
                ("lexus_gs", "Lexus GS", "Азия", "Lexus", 55000, 311, 5.9, 250, "photo"),
                ("lexus_ls", "Lexus LS", "Азия", "Lexus", 90000, 416, 4.6, 280, "photo"),
                ("lexus_rc", "Lexus RC", "Азия", "Lexus", 50000, 311, 5.8, 255, "photo"),
                ("lexus_rx", "Lexus RX", "Азия", "Lexus", 60000, 308, 7.7, 225, "photo"),
                ("lexus_nx", "Lexus NX", "Азия", "Lexus", 45000, 275, 7.0, 225, "photo"),
                ("lexus_lc", "Lexus LC", "Азия", "Lexus", 100000, 471, 4.5, 270, "photo"),
                ("lexus_es", "Lexus ES", "Азия", "Lexus", 48000, 302, 6.6, 245, "photo"),
                ("lexus_ux", "Lexus UX", "Азия", "Lexus", 40000, 181, 8.5, 200, "photo"),
                ("nissan_silvia", "Nissan Silvia", "Азия", "Nissan", 25000, 250, 5.9, 240, "photo"),
                ("nissan_180sx", "Nissan 180SX", "Азия", "Nissan", 22000, 205, 6.5, 225, "photo"),
                ("nissan_skyline_gtr", "Nissan Skyline GT-R", "Азия", "Nissan", 60000, 280, 5.2, 260, "photo"),
                ("nissan_skyline", "Nissan Skyline", "Азия", "Nissan", 35000, 250, 6.0, 240, "photo"),
                ("nissan_fairlady", "Nissan Fairlady Z", "Азия", "Nissan", 35000, 287, 5.5, 250, "photo"),
                ("nissan_350z", "Nissan 350Z", "Азия", "Nissan", 30000, 287, 5.6, 250, "photo"),
                ("nissan_370z", "Nissan 370Z", "Азия", "Nissan", 35000, 332, 5.1, 260, "photo"),
                ("nissan_cefiro", "Nissan Cefiro", "Азия", "Nissan", 25000, 200, 7.5, 220, "photo"),
                ("nissan_laurel", "Nissan Laurel", "Азия", "Nissan", 25000, 280, 6.2, 245, "photo"),
                ("nissan_gloria", "Nissan Gloria", "Азия", "Nissan", 30000, 280, 6.5, 240, "photo"),
                ("nissan_stagea", "Nissan Stagea", "Азия", "Nissan", 35000, 280, 6.0, 240, "photo"),
                ("nissan_pulsar", "Nissan Pulsar GTI-R", "Азия", "Nissan", 25000, 230, 5.8, 235, "photo"),
                ("nissan_leopard", "Nissan Leopard", "Азия", "Nissan", 28000, 280, 6.3, 240, "photo"),
                ("nissan_presea", "Nissan Presea", "Азия", "Nissan", 20000, 150, 9.0, 195, "photo"),
                ("nissan_bluebird", "Nissan Bluebird", "Азия", "Nissan", 22000, 160, 8.5, 200, "photo"),
                ("nissan_qashqai", "Nissan Qashqai", "Азия", "Nissan", 33000, 150, 9.5, 200, "photo"),
                ("nissan_xtrail", "Nissan X-Trail", "Азия", "Nissan", 38000, 184, 9.0, 210, "photo"),
                ("nissan_gtr", "Nissan GT-R", "Азия", "Nissan", 120000, 565, 2.9, 315, "photo"),
                ("nissan_almera", "Nissan Almera", "Азия", "Nissan", 20000, 102, 11.5, 180, "photo"),
                ("nissan_note", "Nissan Note", "Азия", "Nissan", 22000, 98, 12.0, 175, "photo"),
                ("nissan_murano", "Nissan Murano", "Азия", "Nissan", 45000, 260, 7.5, 225, "photo"),
                ("nissan_pathfinder", "Nissan Pathfinder", "Азия", "Nissan", 50000, 284, 7.2, 230, "photo"),
                ("nissan_avenir", "Nissan Avenir", "Азия", "Nissan", 25000, 190, 8.0, 210, "photo"),
                ("nissan_march", "Nissan March", "Азия", "Nissan", 18000, 79, 13.0, 160, "photo"),
                ("honda_civic", "Honda Civic", "Азия", "Honda", 30000, 180, 7.5, 220, "photo"),
                ("honda_accord", "Honda Accord", "Азия", "Honda", 38000, 252, 6.7, 235, "photo"),
                ("honda_crv", "Honda CR-V", "Азия", "Honda", 40000, 190, 8.8, 210, "photo"),
                ("honda_s2000", "Honda S2000", "Азия", "Honda", 35000, 247, 6.2, 240, "photo"),
                ("honda_nsx", "Honda NSX", "Азия", "Honda", 160000, 573, 2.9, 307, "photo"),
                ("honda_integra", "Honda Integra Type R", "Азия", "Honda", 25000, 200, 6.5, 235, "photo"),
                ("honda_prelude", "Honda Prelude", "Азия", "Honda", 22000, 200, 6.8, 230, "photo"),
                ("honda_city", "Honda City", "Азия", "Honda", 22000, 120, 9.9, 195, "photo"),
                ("honda_fit", "Honda Fit", "Азия", "Honda", 22000, 130, 9.5, 195, "photo"),
                ("honda_hrv", "Honda HR-V", "Азия", "Honda", 32000, 141, 10.0, 190, "photo"),
                ("honda_odyssey", "Honda Odyssey", "Азия", "Honda", 40000, 280, 7.5, 220, "photo"),
                ("honda_beat", "Honda Beat", "Азия", "Honda", 15000, 64, 12.5, 150, "photo"),
                ("mazda_rx7", "Mazda RX-7", "Азия", "Mazda", 45000, 280, 5.0, 260, "photo"),
                ("mazda_rx8", "Mazda RX-8", "Азия", "Mazda", 30000, 238, 6.4, 235, "photo"),
                ("mazda_mx5", "Mazda MX-5 Miata", "Азия", "Mazda", 30000, 181, 6.5, 220, "photo"),
                ("mazda_3", "Mazda 3", "Азия", "Mazda", 28000, 186, 7.9, 215, "photo"),
                ("mazda_6", "Mazda 6", "Азия", "Mazda", 35000, 250, 7.0, 235, "photo"),
                ("mazda_cx5", "Mazda CX-5", "Азия", "Mazda", 38000, 187, 9.2, 205, "photo"),
                ("mazda_cx30", "Mazda CX-30", "Азия", "Mazda", 35000, 186, 8.8, 205, "photo"),
                ("mazda_cx60", "Mazda CX-60", "Азия", "Mazda", 50000, 328, 5.8, 240, "photo"),
                ("mazda_323", "Mazda 323", "Азия", "Mazda", 18000, 114, 10.5, 185, "photo"),
                ("mazda_626", "Mazda 626", "Азия", "Mazda", 22000, 136, 9.5, 195, "photo"),
                ("mazda_929", "Mazda 929", "Азия", "Mazda", 28000, 200, 8.0, 215, "photo"),
                ("mazda_cosmo", "Mazda Cosmo", "Азия", "Mazda", 35000, 130, 9.0, 200, "photo"),
                ("mazda_luce", "Mazda Luce", "Азия", "Mazda", 30000, 135, 9.5, 195, "photo"),
                ("subaru_impreza", "Subaru Impreza WRX STI", "Азия", "Subaru", 45000, 310, 4.9, 260, "photo"),
                ("subaru_brz", "Subaru BRZ", "Азия", "Subaru", 32000, 228, 6.5, 230, "photo"),
                ("subaru_legacy", "Subaru Legacy", "Азия", "Subaru", 35000, 260, 6.3, 235, "photo"),
                ("subaru_outback", "Subaru Outback", "Азия", "Subaru", 38000, 182, 8.5, 210, "photo"),
                ("subaru_forester", "Subaru Forester", "Азия", "Subaru", 35000, 182, 8.8, 205, "photo"),
                ("subaru_levorg", "Subaru Levorg", "Азия", "Subaru", 40000, 300, 5.9, 250, "photo"),
                ("subaru_svx", "Subaru SVX", "Азия", "Subaru", 25000, 230, 7.0, 230, "photo"),
                ("mitsubishi_evo", "Mitsubishi Lancer Evolution", "Азия", "Mitsubishi", 45000, 291, 5.1, 255, "photo"),
                ("mitsubishi_lancer", "Mitsubishi Lancer", "Азия", "Mitsubishi", 25000, 168, 8.5, 210, "photo"),
                ("mitsubishi_outlander", "Mitsubishi Outlander", "Азия", "Mitsubishi", 35000, 184, 9.5, 200, "photo"),
                ("mitsubishi_pajero", "Mitsubishi Pajero", "Азия", "Mitsubishi", 45000, 200, 10.5, 185, "photo"),
                ("mitsubishi_3000gt", "Mitsubishi 3000GT", "Азия", "Mitsubishi", 35000, 320, 5.5, 260, "photo"),
                ("mitsubishi_galant", "Mitsubishi Galant VR-4", "Азия", "Mitsubishi", 25000, 240, 6.5, 235, "photo"),
                ("mitsubishi_starion", "Mitsubishi Starion", "Азия", "Mitsubishi", 22000, 200, 7.0, 225, "photo"),
                ("mitsubishi_fto", "Mitsubishi FTO", "Азия", "Mitsubishi", 20000, 200, 7.2, 225, "photo"),
                ("mitsubishi_colt", "Mitsubishi Colt", "Азия", "Mitsubishi", 18000, 109, 10.5, 185, "photo"),
                ("suzuki_swift", "Suzuki Swift", "Азия", "Suzuki", 25000, 140, 9.1, 200, "photo"),
                ("suzuki_jimny", "Suzuki Jimny", "Азия", "Suzuki", 28000, 102, 12.5, 145, "photo"),
                ("suzuki_vitara", "Suzuki Vitara", "Азия", "Suzuki", 30000, 140, 9.5, 195, "photo"),
                ("suzuki_cappuccino", "Suzuki Cappuccino", "Азия", "Suzuki", 18000, 64, 12.0, 150, "photo"),
                ("suzuki_alto", "Suzuki Alto Works", "Азия", "Suzuki", 15000, 64, 11.5, 155, "photo"),
                ("suzuki_ignis", "Suzuki Ignis", "Азия", "Suzuki", 22000, 91, 11.9, 170, "photo"),
                ("daihatsu_charade", "Daihatsu Charade", "Азия", "Daihatsu", 15000, 105, 10.5, 185, "photo"),
                ("daihatsu_copen", "Daihatsu Copen", "Азия", "Daihatsu", 22000, 87, 11.5, 170, "photo"),
                ("daihatsu_terios", "Daihatsu Terios", "Азия", "Daihatsu", 25000, 105, 12.0, 165, "photo"),
                ("daihatsu_mira", "Daihatsu Mira", "Азия", "Daihatsu", 12000, 52, 15.0, 130, "photo"),
                ("isuzu_piazza", "Isuzu Piazza", "Азия", "Isuzu", 20000, 150, 8.5, 200, "photo"),
                ("isuzu_dmax", "Isuzu D-Max", "Азия", "Isuzu", 35000, 190, 11.0, 180, "photo"),
                ("hyundai_genesis", "Hyundai Genesis Coupe", "Азия", "Hyundai", 35000, 348, 5.5, 260, "photo"),
                ("hyundai_i30n", "Hyundai i30 N", "Азия", "Hyundai", 38000, 280, 5.9, 250, "photo"),
                ("hyundai_veloster", "Hyundai Veloster N", "Азия", "Hyundai", 35000, 275, 5.6, 250, "photo"),
                ("hyundai_elantra", "Hyundai Elantra", "Азия", "Hyundai", 28000, 201, 7.5, 225, "photo"),
                ("hyundai_sonata", "Hyundai Sonata", "Азия", "Hyundai", 32000, 191, 8.5, 210, "photo"),
                ("hyundai_tucson", "Hyundai Tucson", "Азия", "Hyundai", 38000, 190, 8.9, 210, "photo"),
                ("hyundai_santafe", "Hyundai Santa Fe", "Азия", "Hyundai", 45000, 277, 7.5, 225, "photo"),
                ("hyundai_creta", "Hyundai Creta", "Азия", "Hyundai", 28000, 123, 10.5, 185, "photo"),
                ("hyundai_porter", "Hyundai Porter", "Азия", "Hyundai", 25000, 136, 14.0, 150, "photo"),
                ("kia_stinger", "Kia Stinger", "Азия", "Kia", 45000, 368, 4.9, 270, "photo"),
                ("kia_rio", "Kia Rio", "Азия", "Kia", 22000, 123, 10.5, 185, "photo"),
                ("kia_cerato", "Kia Cerato", "Азия", "Kia", 28000, 152, 9.5, 200, "photo"),
                ("kia_optima", "Kia Optima", "Азия", "Kia", 32000, 188, 8.5, 215, "photo"),
                ("kia_sportage", "Kia Sportage", "Азия", "Kia", 38000, 187, 9.2, 205, "photo"),
                ("kia_sorento", "Kia Sorento", "Азия", "Kia", 45000, 281, 7.5, 225, "photo"),
                ("kia_ceed", "Kia Ceed", "Азия", "Kia", 32000, 140, 9.2, 205, "photo"),
                ("kia_picanto", "Kia Picanto", "Азия", "Kia", 18000, 84, 12.5, 165, "photo"),
                ("genesis_g70", "Genesis G70", "Азия", "Genesis", 45000, 365, 4.7, 270, "photo"),
                ("genesis_g80", "Genesis G80", "Азия", "Genesis", 55000, 375, 5.0, 260, "photo"),
                ("genesis_g90", "Genesis G90", "Азия", "Genesis", 80000, 409, 5.2, 250, "photo"),
                ("genesis_gv70", "Genesis GV70", "Азия", "Genesis", 50000, 375, 5.0, 255, "photo"),
                ("genesis_gv80", "Genesis GV80", "Азия", "Genesis", 65000, 375, 5.5, 250, "photo"),
                ("ssangyong_rexton", "SsangYong Rexton", "Азия", "SsangYong", 40000, 202, 10.0, 185, "photo"),
                ("ssangyong_actyon", "SsangYong Actyon", "Азия", "SsangYong", 30000, 149, 11.0, 175, "photo"),
                ("geely_atlas", "Geely Atlas", "Азия", "Geely", 30000, 177, 9.5, 200, "photo"),
                ("geely_emgrand", "Geely Emgrand", "Азия", "Geely", 25000, 139, 10.5, 185, "photo"),
                ("geely_monjaro", "Geely Monjaro", "Азия", "Geely", 38000, 238, 7.9, 215, "photo"),
                ("haval_jolion", "Haval Jolion", "Азия", "Haval", 32000, 150, 9.8, 195, "photo"),
                ("haval_h6", "Haval H6", "Азия", "Haval", 38000, 190, 8.5, 205, "photo"),
                ("haval_h9", "Haval H9", "Азия", "Haval", 45000, 218, 10.0, 190, "photo"),
                ("chery_tiggo4", "Chery Tiggo 4", "Азия", "Chery", 25000, 147, 10.0, 185, "photo"),
                ("chery_tiggo7", "Chery Tiggo 7", "Азия", "Chery", 30000, 156, 9.5, 195, "photo"),
                ("chery_tiggo8", "Chery Tiggo 8", "Азия", "Chery", 35000, 186, 8.9, 205, "photo"),
                ("chery_arrizo", "Chery Arrizo", "Азия", "Chery", 28000, 147, 10.0, 190, "photo"),
                ("changan_cs35", "Changan CS35 Plus", "Азия", "Changan", 30000, 158, 9.5, 195, "photo"),
                ("changan_cs55", "Changan CS55 Plus", "Азия", "Changan", 35000, 180, 8.9, 205, "photo"),
                ("changan_cs75", "Changan CS75 Plus", "Азия", "Changan", 40000, 232, 8.0, 215, "photo"),
                ("changan_unik", "Changan UNI-K", "Азия", "Changan", 45000, 226, 8.5, 210, "photo"),
                ("changan_univ", "Changan UNI-V", "Азия", "Changan", 35000, 188, 7.9, 215, "photo"),
                ("byd_song", "BYD Song", "Азия", "BYD", 38000, 181, 8.5, 205, "photo"),
                ("byd_tang", "BYD Tang", "Азия", "BYD", 45000, 245, 7.5, 220, "photo"),
                ("byd_han", "BYD Han", "Азия", "BYD", 55000, 222, 7.9, 210, "photo"),
                ("byd_seagull", "BYD Seagull", "Азия", "BYD", 18000, 75, 13.0, 130, "photo"),
                ("byd_dolphin", "BYD Dolphin", "Азия", "BYD", 25000, 95, 11.5, 150, "photo"),
                ("byd_atto3", "BYD Atto 3", "Азия", "BYD", 35000, 204, 7.3, 225, "photo"),
                ("mg4", "MG 4", "Азия", "MG", 30000, 170, 7.9, 210, "photo"),
                ("mg5", "MG 5", "Азия", "MG", 28000, 168, 8.5, 205, "photo"),
                ("mg6", "MG 6", "Азия", "MG", 32000, 181, 8.0, 210, "photo"),
                ("mg_zs", "MG ZS", "Азия", "MG", 25000, 111, 11.5, 175, "photo"),
                ("mg_hs", "MG HS", "Азия", "MG", 35000, 162, 9.5, 195, "photo"),
                ("proton_saga", "Proton Saga", "Азия", "Proton", 15000, 95, 12.5, 165, "photo"),
                ("proton_x50", "Proton X50", "Азия", "Proton", 28000, 150, 8.9, 200, "photo"),
                ("proton_x70", "Proton X70", "Азия", "Proton", 35000, 184, 9.5, 195, "photo"),
                ("perodua_myvi", "Perodua Myvi", "Азия", "Perodua", 18000, 102, 11.5, 175, "photo"),
                ("perodua_axia", "Perodua Axia", "Азия", "Perodua", 12000, 68, 14.0, 140, "photo"),
            ]
            
            # Американские машины
            american_cars = [
                ("ford_f150", "Ford F-Series", "Америка", "Ford", 45000, 400, 6.5, 200, "photo"),
                ("chevrolet_silverado", "Chevrolet Silverado", "Америка", "Chevrolet", 45000, 420, 6.3, 205, "photo"),
                ("ram_1500", "Ram 1500", "Америка", "Ram", 48000, 395, 6.7, 195, "photo"),
                ("gmc_sierra", "GMC Sierra", "Америка", "GMC", 47000, 420, 6.4, 200, "photo"),
                ("ford_mustang", "Ford Mustang", "Америка", "Ford", 40000, 450, 4.2, 280, "photo"),
                ("chevrolet_corvette", "Chevrolet Corvette", "Америка", "Chevrolet", 80000, 495, 2.9, 312, "photo"),
                ("jeep_wrangler", "Jeep Wrangler", "Америка", "Jeep", 40000, 285, 7.5, 190, "photo"),
                ("chevrolet_camaro", "Chevrolet Camaro", "Америка", "Chevrolet", 38000, 455, 4.0, 290, "photo"),
                ("dodge_challenger", "Dodge Challenger", "Америка", "Dodge", 45000, 485, 3.6, 320, "photo"),
                ("tesla_model_y", "Tesla Model Y", "Америка", "Tesla", 60000, 456, 3.5, 250, "photo"),
                ("tesla_model_3", "Tesla Model 3", "Америка", "Tesla", 50000, 450, 3.1, 261, "photo"),
                ("jeep_grand_cherokee", "Jeep Grand Cherokee", "Америка", "Jeep", 55000, 357, 6.0, 230, "photo"),
                ("ford_explorer", "Ford Explorer", "Америка", "Ford", 48000, 400, 5.5, 230, "photo"),
                ("chevrolet_tahoe", "Chevrolet Tahoe", "Америка", "Chevrolet", 65000, 420, 6.2, 210, "photo"),
                ("chevrolet_suburban", "Chevrolet Suburban", "Америка", "Chevrolet", 70000, 420, 6.5, 205, "photo"),
                ("dodge_charger", "Dodge Charger", "Америка", "Dodge", 45000, 485, 3.6, 320, "photo"),
                ("cadillac_escalade", "Cadillac Escalade", "Америка", "Cadillac", 90000, 420, 5.9, 215, "photo"),
                ("ford_expedition", "Ford Expedition", "Америка", "Ford", 65000, 400, 6.0, 220, "photo"),
                ("lincoln_navigator", "Lincoln Navigator", "Америка", "Lincoln", 85000, 450, 5.5, 225, "photo"),
                ("gmc_yukon", "GMC Yukon", "Америка", "GMC", 70000, 420, 6.2, 210, "photo"),
                ("chevrolet_equinox", "Chevrolet Equinox", "Америка", "Chevrolet", 35000, 170, 8.5, 200, "photo"),
                ("ford_escape", "Ford Escape", "Америка", "Ford", 33000, 181, 7.9, 210, "photo"),
                ("tesla_model_s", "Tesla Model S", "Америка", "Tesla", 100000, 1020, 1.99, 320, "photo"),
                ("tesla_model_x", "Tesla Model X", "Америка", "Tesla", 110000, 1020, 2.5, 262, "photo"),
                ("dodge_durango", "Dodge Durango", "Америка", "Dodge", 50000, 475, 4.4, 290, "photo"),
                ("chevrolet_traverse", "Chevrolet Traverse", "Америка", "Chevrolet", 45000, 310, 7.5, 215, "photo"),
                ("ford_bronco", "Ford Bronco", "Америка", "Ford", 45000, 330, 6.5, 225, "photo"),
                ("gmc_acadia", "GMC Acadia", "Америка", "GMC", 42000, 228, 8.0, 210, "photo"),
                ("chrysler_300", "Chrysler 300", "Америка", "Chrysler", 38000, 363, 5.5, 250, "photo"),
                ("chevrolet_impala", "Chevrolet Impala", "Америка", "Chevrolet", 35000, 305, 6.0, 240, "photo"),
                ("ford_crown_victoria", "Ford Crown Victoria", "Америка", "Ford", 25000, 250, 7.5, 220, "photo"),
                ("buick_enclave", "Buick Enclave", "Америка", "Buick", 50000, 310, 7.5, 215, "photo"),
                ("cadillac_cts", "Cadillac CTS", "Америка", "Cadillac", 55000, 335, 5.6, 260, "photo"),
                ("cadillac_xt5", "Cadillac XT5", "Америка", "Cadillac", 50000, 310, 6.5, 230, "photo"),
                ("lincoln_continental", "Lincoln Continental", "Америка", "Lincoln", 55000, 400, 5.0, 250, "photo"),
                ("ford_taurus", "Ford Taurus", "Америка", "Ford", 35000, 288, 6.0, 235, "photo"),
                ("chevrolet_malibu", "Chevrolet Malibu", "Америка", "Chevrolet", 30000, 160, 8.0, 210, "photo"),
                ("ford_fusion", "Ford Fusion", "Америка", "Ford", 32000, 175, 7.5, 215, "photo"),
                ("chevrolet_bolt", "Chevrolet Bolt EV", "Америка", "Chevrolet", 35000, 200, 6.5, 230, "photo"),
                ("pontiac_firebird", "Pontiac Firebird", "Америка", "Pontiac", 30000, 325, 5.3, 260, "photo"),
                ("pontiac_gto", "Pontiac GTO", "Америка", "Pontiac", 35000, 400, 4.8, 280, "photo"),
                ("oldsmobile_cutlass", "Oldsmobile Cutlass", "Америка", "Oldsmobile", 25000, 250, 6.5, 230, "photo"),
                ("plymouth_barracuda", "Plymouth Barracuda", "Америка", "Plymouth", 40000, 425, 5.0, 270, "photo"),
                ("shelby_cobra", "Shelby Cobra", "Америка", "Shelby", 80000, 485, 4.2, 290, "photo"),
                ("dodge_viper", "Dodge Viper", "Америка", "Dodge", 120000, 645, 3.5, 330, "photo"),
                ("chevrolet_chevelle", "Chevrolet Chevelle SS", "Америка", "Chevrolet", 50000, 450, 5.0, 270, "photo"),
                ("ford_gt", "Ford GT", "Америка", "Ford", 500000, 660, 3.0, 347, "photo"),
                ("hummer_h2", "Hummer H2", "Америка", "Hummer", 40000, 325, 9.0, 190, "photo"),
                ("jeep_cherokee", "Jeep Cherokee", "Америка", "Jeep", 35000, 270, 7.5, 210, "photo"),
                ("ford_maverick", "Ford Maverick", "Америка", "Ford", 28000, 250, 6.5, 220, "photo"),
                ("ford_f150_lightning", "Ford F-150 Lightning", "Америка", "Ford", 70000, 580, 4.0, 280, "photo"),
                ("chevrolet_blazer", "Chevrolet Blazer", "Америка", "Chevrolet", 40000, 308, 6.5, 225, "photo"),
                ("buick_regal", "Buick Regal", "Америка", "Buick", 35000, 250, 6.8, 230, "photo"),
                ("cadillac_lyriq", "Cadillac Lyriq", "Америка", "Cadillac", 65000, 340, 5.5, 250, "photo"),
                ("rivian_r1t", "Rivian R1T", "Америка", "Rivian", 80000, 835, 3.0, 300, "photo"),
                ("lucid_air", "Lucid Air", "Америка", "Lucid", 100000, 1111, 2.5, 320, "photo"),
                ("chevrolet_colorado", "Chevrolet Colorado", "Америка", "Chevrolet", 35000, 308, 7.5, 205, "photo"),
                ("gmc_canyon", "GMC Canyon", "Америка", "GMC", 37000, 308, 7.5, 205, "photo"),
                ("jeep_gladiator", "Jeep Gladiator", "Америка", "Jeep", 45000, 285, 8.0, 185, "photo"),
                ("chevrolet_corvette_stingray", "Chevrolet Corvette Stingray", "Америка", "Chevrolet", 85000, 495, 2.9, 312, "photo"),
            ]
            
            all_cars = european_cars + asian_cars + american_cars
            self.cursor.executemany('''
                INSERT OR IGNORE INTO cars_catalog 
                (id, name, market, brand, price, hp, accel, top_speed, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', all_cars)
            self.conn.commit()

    def init_promocodes(self):
        default_promos = [
            ("WELCOME2024", 10000, 1),
            ("RACINGBOT", 25000, 1),
            ("SPEED", 15000, 1),
            ("FOLLOWERS", 5000, 2),
            ("RICH", 50000, 1)
        ]
        for promo in default_promos:
            self.cursor.execute(
                "INSERT OR IGNORE INTO promocodes (code, reward, max_uses) VALUES (?, ?, ?)",
                promo
            )
        self.conn.commit()

    def insert_all_parts(self):
        # Двигатели
        engines = [
            ("vw_ea888", "Volkswagen EA888", 50, 5000, "2.0 TSI", "photo"),
            ("mb_m104", "Mercedes-Benz M104", 70, 8000, "3.2 I6", "photo"),
            ("bmw_m54", "BMW M54", 80, 9000, "3.0 I6", "photo"),
            ("porsche_mezger", "Porsche Mezger", 120, 20000, "3.6-3.8 H6", "photo"),
            ("audi_25tfsi", "Audi 2.5 TFSI", 100, 15000, "5-цилиндровый", "photo"),
            ("ferrari_f136", "Ferrari F136", 150, 30000, "V8 4.3", "photo"),
            ("ferrari_f140", "Ferrari F140", 200, 50000, "V12 6.5", "photo"),
            ("bmw_s65", "BMW S65", 150, 25000, "V8 4.0", "photo"),
            ("mb_m113", "Mercedes-Benz M113", 100, 15000, "5.4 V8 Kompressor", "photo"),
            ("vw_19tdi", "Volkswagen 1.9 TDI", 30, 3000, "1.9 TDI", "photo"),
            ("bmw_s55", "BMW S55", 130, 20000, "3.0 I6 TwinTurbo", "photo"),
            ("audi_42fsi", "Audi 4.2 FSI", 120, 18000, "V8", "photo"),
            ("porsche_m97", "Porsche M97", 110, 18000, "оппозитная 6-ка", "photo"),
            ("opel_c20xe", "Opel C20XE", 40, 4000, "2.0 16V", "photo"),
            ("renault_f7r", "Renault F7R", 45, 4500, "2.0 16V", "photo"),
            ("alfa_twinspark", "Alfa Romeo Twin Spark", 35, 3500, "2.0", "photo"),
            ("jaguar_ajv8", "Jaguar AJ-V8", 130, 22000, "4.0-5.0", "photo"),
            ("volvo_b230", "Volvo B230", 50, 5000, "2.3 турбо", "photo"),
            ("skoda_18t", "Škoda 1.8T 20V", 45, 4500, "1.8T", "photo"),
            ("bmw_s85", "BMW S85", 200, 40000, "V10 5.0", "photo"),
            ("toyota_2jz", "Toyota 2JZ-GTE", 150, 25000, "3.0 I6 TwinTurbo", "photo"),
            ("nissan_rb26", "Nissan RB26DETT", 140, 24000, "2.6 I6 TwinTurbo", "photo"),
            ("honda_k20a", "Honda K20A", 70, 8000, "2.0 I4 VTEC", "photo"),
            ("mazda_13b", "Mazda 13B-REW", 130, 20000, "1.3 TwinRotary", "photo"),
            ("subaru_ej25", "Subaru EJ25", 80, 10000, "2.5 B4 Turbo", "photo"),
            ("mitsubishi_4g63", "Mitsubishi 4G63T", 90, 12000, "2.0 I4 Turbo", "photo"),
            ("honda_f20c", "Honda F20C", 70, 9000, "2.0 I4 VTEC", "photo"),
            ("nissan_sr20", "Nissan SR20DET", 80, 10000, "2.0 I4 Turbo", "photo"),
            ("toyota_1uz", "Toyota 1UZ-FE", 100, 15000, "4.0 V8", "photo"),
            ("toyota_1gr", "Toyota 1GR-FE", 80, 12000, "4.0 V6", "photo"),
            ("honda_b16b", "Honda B16B", 50, 6000, "1.6 I4 VTEC", "photo"),
            ("nissan_vq35", "Nissan VQ35DE", 90, 13000, "3.5 V6", "photo"),
            ("hyundai_gamma", "Hyundai Gamma 1.6 T-GDi", 60, 7000, "1.6 I4 Turbo", "photo"),
            ("toyota_2ar", "Toyota 2AR-FE", 40, 5000, "2.4-2.5 I4", "photo"),
            ("mitsubishi_6g74", "Mitsubishi 6G74", 70, 9000, "3.5 V6", "photo"),
            ("suzuki_k14b", "Suzuki K14B", 20, 2000, "1.4 I4", "photo"),
            ("subaru_fa20", "Subaru FA20", 60, 8000, "2.0-2.4 B4", "photo"),
            ("toyota_1nz", "Toyota 1NZ-FE", 15, 1500, "1.0-1.5 I4", "photo"),
            ("mazda_skyactiv", "Mazda SkyActiv-G 2.5", 30, 4000, "2.5 I4", "photo"),
            ("isuzu_4jj1", "Isuzu 4JJ1", 40, 5000, "3.0 I4 турбодизель", "photo"),
            ("chevrolet_ls", "Chevrolet LS", 150, 25000, "Small Block V8", "photo"),
            ("ford_windsor", "Ford Windsor V8", 130, 20000, "302, 351", "photo"),
            ("chrysler_hemi", "Chrysler HEMI", 180, 30000, "5.7-6.4 V8", "photo"),
            ("chevrolet_bigblock", "Chevrolet Big Block V8", 200, 35000, "454", "photo"),
            ("ford_modular", "Ford Modular V8", 120, 18000, "4.6, 5.4", "photo"),
            ("ford_coyote", "Ford Coyote V8", 160, 28000, "5.0", "photo"),
            ("chevrolet_lt", "Chevrolet LT", 170, 30000, "Small Block V8", "photo"),
            ("dodge_hellcat", "Dodge Hellcat V8", 250, 50000, "6.2 Supercharged", "photo"),
            ("cadillac_northstar", "Cadillac Northstar V8", 130, 22000, "4.6", "photo"),
            ("ford_ecoboost", "Ford Ecoboost 2.3", 60, 7000, "I4 Turbo", "photo"),
            ("gm_ecotec", "GM Ecotec", 40, 5000, "2.0-2.4 I4", "photo"),
            ("amc_40", "AMC 4.0 I6", 50, 6000, "4.0 I6", "photo"),
            ("chrysler_slant6", "Chrysler Slant-6", 30, 3000, "2.2-2.5 I4", "photo"),
            ("buick_38", "Buick 3.8 V6", 45, 5000, "3.8 V6", "photo"),
            ("ford_powerstroke", "Ford 7.3 Power Stroke", 100, 18000, "V8 Diesel", "photo"),
            ("cummins_59", "Cummins 5.9L 6BT", 120, 20000, "I6 Diesel", "photo"),
            ("chevrolet_350", "Chevrolet 350 Small Block", 130, 18000, "5.7 V8", "photo"),
            ("pontiac_455", "Pontiac 455 V8", 180, 28000, "7.5 V8", "photo"),
            ("oldsmobile_455", "Oldsmobile 455 Rocket V8", 170, 27000, "7.5 V8", "photo"),
            ("ford_flathead", "Ford Flathead V8", 90, 12000, "V8", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_engines 
            (id, name, hp_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', engines)
        
        # Турбины
        turbos = [
            ("garrett_gt28", "Garrett GT28", 80, 10000, "Twin-scroll", "photo"),
            ("garrett_gt30", "Garrett GT30", 120, 15000, "GT30", "photo"),
            ("garrett_gt35", "Garrett GT35", 160, 20000, "GT35", "photo"),
            ("garrett_gtx35", "Garrett GTX35", 200, 25000, "GTX35", "photo"),
            ("garrett_gtx3582r", "Garrett GTX3582R", 250, 35000, "GTX3582R", "photo"),
            ("garrett_gtx3584rs", "Garrett GTX3584RS", 300, 45000, "GTX3584RS", "photo"),
            ("garrett_g25", "Garrett G25-550", 150, 20000, "G25-550", "photo"),
            ("garrett_g30", "Garrett G30-660", 220, 30000, "G30-660", "photo"),
            ("borgwarner_efr", "BorgWarner EFR", 180, 22000, "EFR Series", "photo"),
            ("borgwarner_k04", "BorgWarner K04", 60, 8000, "K04", "photo"),
            ("borgwarner_k16", "BorgWarner K16", 100, 12000, "K16", "photo"),
            ("borgwarner_s200", "BorgWarner S200", 140, 18000, "S200", "photo"),
            ("borgwarner_s300", "BorgWarner S300", 200, 28000, "S300", "photo"),
            ("borgwarner_s400", "BorgWarner S400", 280, 40000, "S400", "photo"),
            ("honeywell_ht30", "Honeywell HT30", 130, 16000, "HT30", "photo"),
            ("honeywell_he351", "Honeywell HE351", 170, 22000, "HE351", "photo"),
            ("mitsubishi_td04", "Mitsubishi TD04", 70, 9000, "TD04", "photo"),
            ("mitsubishi_td05", "Mitsubishi TD05", 110, 14000, "TD05", "photo"),
            ("mitsubishi_td06", "Mitsubishi TD06", 150, 19000, "TD06", "photo"),
            ("mitsubishi_tf035", "Mitsubishi TF035", 50, 6000, "TF035", "photo"),
            ("ihi_vf39", "IHI VF39", 90, 11000, "VF39", "photo"),
            ("ihi_rhf5", "IHI RHF5", 120, 15000, "RHF5", "photo"),
            ("kkk_k03", "KKK K03", 60, 7000, "K03", "photo"),
            ("kkk_k24", "KKK K24", 130, 16000, "K24", "photo"),
            ("holset_hx35", "Holset HX35", 180, 24000, "HX35", "photo"),
            ("holset_hx40", "Holset HX40", 240, 32000, "HX40", "photo"),
            ("holset_he221", "Holset HE221", 100, 13000, "HE221", "photo"),
            ("precision_6266", "Precision Turbo 6266", 260, 35000, "6266", "photo"),
            ("precision_6766", "Precision Turbo 6766", 300, 42000, "6766", "photo"),
            ("precision_7675", "Precision Turbo 7675", 350, 50000, "7675", "photo"),
            ("turbosmart_kompact", "Turbosmart Kompact", 160, 20000, "Kompact", "photo"),
            ("turbosmart_hyperboost", "Turbosmart Hyperboost", 200, 26000, "Hyperboost", "photo"),
            ("greddy_td05", "GReddy TD05", 140, 18000, "TD05", "photo"),
            ("greddy_t518z", "GReddy T518Z", 190, 25000, "T518Z", "photo"),
            ("blouch_dominator", "Blouch Dominator 3.0", 230, 30000, "Dominator 3.0", "photo"),
            ("blouch_20g", "Blouch 20G-XT", 180, 24000, "20G-XT", "photo"),
            ("hks_gt2835", "HKS GT2835", 170, 22000, "GT2835", "photo"),
            ("hks_gtrs", "HKS GT-RS", 210, 28000, "GT-RS", "photo"),
            ("turbonetics_t70", "Turbonetics T-70", 220, 30000, "T-70", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_turbos 
            (id, name, hp_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', turbos)
        
        # Выхлопы
        exhausts = [
            ("akrapovic", "Akrapovič Evolution", 25, 5000, "Evolution", "photo"),
            ("remus", "Remus PowerSound", 20, 4000, "PowerSound", "photo"),
            ("milltek", "Milltek Non-Resonated", 22, 4500, "Non-Resonated", "photo"),
            ("supersprint", "Supersprint Sport", 18, 3500, "Sport", "photo"),
            ("sebring", "Sebring Sport", 15, 3000, "Sport", "photo"),
            ("magnaflow", "MagnaFlow Competition", 30, 6000, "Competition", "photo"),
            ("borla", "Borla Atak", 35, 7000, "Atak", "photo"),
            ("fox", "FOX Performance", 20, 4000, "Performance", "photo"),
            ("hks_hipower", "HKS Hi-Power", 28, 5500, "Hi-Power", "photo"),
            ("hks_legamax", "HKS Legamax Premium", 25, 5000, "Legamax Premium", "photo"),
            ("greddy_power", "GReddy Power Extreme", 30, 6000, "Power Extreme", "photo"),
            ("asso", "AsSO Прямоток", 15, 2500, "Прямоток", "photo"),
            ("plazma", "Plazma Спорт", 18, 3000, "Спорт", "photo"),
            ("stim", "STiM Стандарт", 10, 2000, "Стандарт", "photo"),
            ("scarab", "Scarab Спорт", 22, 4000, "Спорт", "photo"),
            ("tial", "TiAL Q", 40, 8000, "Q", "photo"),
            ("walker", "Walker Quiet-Flow", 12, 2200, "Quiet-Flow", "photo"),
            ("bosal", "Bosal Performance", 15, 2800, "Performance", "photo"),
            ("ap_exhaust", "AP Exhaust Sport", 18, 3200, "Sport", "photo"),
            ("jetex", "Jetex Race", 35, 6500, "Race", "photo"),
            ("bastuck", "Bastuck Sport", 25, 4800, "Sport", "photo"),
            ("apexi_n1", "A'PEXi N1", 32, 6200, "N1", "photo"),
            ("5zigen", "5Zigen Fireball", 30, 5800, "Fireball", "photo"),
            ("tanabe", "Tanabe Medalion Touring", 22, 4200, "Medalion Touring", "photo"),
            ("fujitsubo", "Fujitsubo Legalis R", 20, 3800, "Legalis R", "photo"),
            ("skunk2", "Skunk2 MegaPower", 38, 7500, "MegaPower", "photo"),
            ("thermal", "Thermal R&D", 35, 7000, "R&D", "photo"),
            ("mugen", "Mugen Twin Loop", 28, 5500, "Twin Loop", "photo"),
            ("spoon", "Spoon Sports", 30, 6000, "Sports", "photo"),
            ("kakimoto", "Kakimoto Regu 06&R", 25, 5000, "Regu 06&R", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_exhausts 
            (id, name, hp_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', exhausts)
        
        # Радиаторы
        radiators = [
            ("nissens", "Nissens Performance", 15, 3000, "Performance", "photo"),
            ("behr", "Behr Hella OEM Plus", 12, 2500, "OEM Plus", "photo"),
            ("denso", "Denso Ultra-Cool", 18, 3500, "Ultra-Cool", "photo"),
            ("valeo", "Valeo Premium", 14, 2800, "Premium", "photo"),
            ("koyo", "Koyo Racing VH Series", 25, 5000, "Racing VH", "photo"),
            ("mishimoto", "Mishimoto M-Line", 20, 4000, "M-Line", "photo"),
            ("csf", "CSF Racing Triple-Pass", 30, 6000, "Triple-Pass", "photo"),
            ("nflow", "N-Flow Pro Series", 22, 4500, "Pro Series", "photo"),
            ("fenox", "Fenox Turbo-Cool", 16, 3200, "Turbo-Cool", "photo"),
            ("ava", "AVA High-Efficiency", 18, 3500, "High-Efficiency", "photo"),
            ("calsonic", "Calsonic Nismo", 28, 5500, "Nismo", "photo"),
            ("graf", "GRAF A/C Plus", 14, 2800, "A/C Plus", "photo"),
            ("luzar", "Luzar ProFlow", 16, 3000, "ProFlow", "photo"),
            ("tyc", "TYC All-Aluminum", 20, 3800, "All-Aluminum", "photo"),
            ("meyle", "Meyle HD", 15, 3000, "HD", "photo"),
            ("automega", "Automega Extreme", 22, 4200, "Extreme", "photo"),
            ("hjs", "HJS Competition", 25, 4800, "Competition", "photo"),
            ("pwr", "PWR Performance", 30, 5800, "Performance", "photo"),
            ("champion", "Champion Cooler", 18, 3500, "Cooler", "photo"),
            ("rada", "Rada-Expert Pro", 16, 3200, "Expert Pro", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_radiators 
            (id, name, hp_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', radiators)
        
        # Закись азота
        nos_list = [
            ("nos_sniper", "NOS Sniper Kit", 100, 15000, "Sniper Kit", "photo"),
            ("nos_cheater", "NOS Cheater Kit", 150, 25000, "Cheater Kit", "photo"),
            ("nos_powershot", "NOS Powershot Kit", 120, 20000, "Powershot Kit", "photo"),
            ("nos_nytrex", "NOS Nytrex Kit", 180, 30000, "Nytrex Kit", "photo"),
            ("nos_proshot", "NOS Pro Shot Fogger Kit", 250, 45000, "Pro Shot Fogger", "photo"),
            ("zex_dry", "ZEX Nitrous Kit (Dry)", 90, 12000, "Dry Kit", "photo"),
            ("zex_wet", "ZEX Nitrous Kit (Wet)", 130, 22000, "Wet Kit", "photo"),
            ("nx_efi", "Nitrous Express EFI Kit", 140, 24000, "EFI Kit", "photo"),
            ("nx_shark", "Nitrous Express Shark Nozzle", 200, 35000, "Shark Nozzle", "photo"),
            ("nx_stage", "NX Stage Kit", 160, 28000, "Stage Kit", "photo"),
            ("nx_maximizer", "NX Maximizer Kit", 220, 40000, "Maximizer Kit", "photo"),
            ("won_direct", "WON Direct Port Kit", 300, 50000, "Direct Port", "photo"),
            ("won_progressive", "WON Progressive Controller", 280, 48000, "Progressive", "photo"),
            ("edelbrock", "Edelbrock Nitrous Kit", 150, 25000, "Nitrous Kit", "photo"),
            ("holley", "Holley NOS Plate Kit", 170, 28000, "Plate Kit", "photo"),
            ("tnt", "TNT Nitrous Kit", 190, 32000, "Nitrous Kit", "photo"),
            ("dynotune", "DynoTune NOS", 130, 22000, "NOS", "photo"),
            ("nitrous_pro", "Nitrous Pro Race Kit", 240, 42000, "Pro Race Kit", "photo"),
            ("snipefx", "SNIPEFX Nitrous System", 200, 35000, "Nitrous System", "photo"),
            ("mds", "MDS Fogger", 260, 46000, "Fogger", "photo"),
            ("ice", "ICE Nitrous Plate System", 180, 30000, "Plate System", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_nos 
            (id, name, hp_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', nos_list)
        
        # Подвеска
        suspensions = [
            ("koni", "Koni Sport", 0.2, 5000, "Желтые", "photo"),
            ("bilstein", "Bilstein B8", 0.25, 6000, "Sport", "photo"),
            ("ohlins", "Öhlins Road & Track", 0.3, 10000, "Road & Track", "photo"),
            ("kw", "KW Variant 3", 0.28, 8000, "Variant 3", "photo"),
            ("kyb", "KYB Gas-a-Just", 0.15, 3000, "Gas-a-Just", "photo"),
            ("monroe", "Monroe Reflex", 0.12, 2500, "Reflex", "photo"),
            ("sachs", "Sachs Performance", 0.2, 4500, "Performance", "photo"),
            ("tein", "Tein Flex Z", 0.25, 7000, "Flex Z", "photo"),
            ("bc_racing", "BC Racing BR Series", 0.22, 5500, "BR Series", "photo"),
            ("hr", "H&R monotube", 0.18, 4000, "monotube", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_suspensions 
            (id, name, handling_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', suspensions)
        
        # Покрышки
        tires = [
            ("michelin_ps4s", "Michelin Pilot Sport 4 S", 0.25, 4000, "Pilot Sport 4 S", "photo"),
            ("goodyear_eagle", "Goodyear Eagle F1", 0.22, 3500, "Eagle F1", "photo"),
            ("bridgestone_potenza", "Bridgestone Potenza Sport", 0.23, 3800, "Potenza Sport", "photo"),
            ("pirelli_pzero", "Pirelli P Zero", 0.24, 4200, "P Zero", "photo"),
            ("continental_pc6", "Continental PremiumContact 6", 0.18, 3000, "PremiumContact 6", "photo"),
            ("dunlop_sportmax", "Dunlop Sport Maxx RT2", 0.2, 3200, "Sport Maxx RT2", "photo"),
            ("hankook_ventus", "Hankook Ventus S1 evo3", 0.2, 3100, "Ventus S1 evo3", "photo"),
            ("yokohama_advan", "Yokohama Advan Sport V105", 0.21, 3300, "Advan Sport V105", "photo"),
            ("nokian_hakka", "Nokian Hakkapeliitta 10", 0.15, 2800, "Hakkapeliitta 10", "photo"),
            ("toyo_proxes", "Toyo Proxes Sport", 0.19, 3000, "Proxes Sport", "photo"),
            ("falken_azenis", "Falken Azenis FK510", 0.18, 2900, "Azenis FK510", "photo"),
            ("kumho_ecsta", "Kumho Ecsta PS91", 0.17, 2700, "Ecsta PS91", "photo"),
            ("bfgoodrich_gforce", "BFGoodrich g-Force Sport", 0.2, 3200, "g-Force Sport", "photo"),
            ("vredestein_ultrac", "Vredestein Ultrac Vorti", 0.19, 3100, "Ultrac Vorti", "photo"),
            ("apollo_alnac", "Apollo Alnac 4G", 0.15, 2500, "Alnac 4G", "photo"),
            ("matador_mp46", "Matador MP46 Hectorra 3", 0.14, 2200, "MP46 Hectorra 3", "photo"),
            ("triangle_sportex", "Triangle Sportex TH201", 0.13, 2000, "Sportex TH201", "photo"),
            ("tigar_syneris", "Tigar Syneris", 0.12, 1800, "Syneris", "photo"),
            ("lassa_impetus", "Lassa Impetus Revo", 0.14, 2100, "Impetus Revo", "photo"),
            ("cordiant_sport3", "Cordiant Sport 3", 0.13, 1900, "Sport 3", "photo"),
        ]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO parts_tires 
            (id, name, grip_bonus, price, description, photo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', tires)
        
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()
    
    def create_user(self, user_id, username, nickname):
        self.cursor.execute('''
            INSERT INTO users (user_id, username, nickname, register_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, nickname, int(time.time())))
        self.conn.commit()
    
    def get_user_car(self, user_id):
        self.cursor.execute('''
            SELECT uc.*, cc.* FROM user_cars uc
            JOIN cars_catalog cc ON uc.car_id = cc.id
            WHERE uc.user_id = ? AND uc.is_selected = 1
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_user_cars(self, user_id):
        self.cursor.execute('''
            SELECT uc.*, cc.* FROM user_cars uc
            JOIN cars_catalog cc ON uc.car_id = cc.id
            WHERE uc.user_id = ?
        ''', (user_id,))
        return self.cursor.fetchall()
    
    def add_user_car(self, user_id, car_id):
        self.cursor.execute('''
            INSERT INTO user_cars (user_id, car_id, is_selected)
            VALUES (?, ?, 0)
        ''', (user_id, car_id))
        self.conn.commit()
    
    def select_car(self, user_id, car_id):
        self.cursor.execute("UPDATE user_cars SET is_selected = 0 WHERE user_id = ?", (user_id,))
        self.cursor.execute("UPDATE user_cars SET is_selected = 1 WHERE user_id = ? AND car_id = ?", (user_id, car_id))
        self.cursor.execute("UPDATE users SET current_car_id = ? WHERE user_id = ?", (car_id, user_id))
        self.conn.commit()
    
    def update_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def update_rating(self, user_id, amount):
        self.cursor.execute("UPDATE users SET rating = rating + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def update_followers(self, user_id, amount):
        self.cursor.execute("UPDATE users SET followers = followers + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def get_top_rating(self, limit=10):
        self.cursor.execute('''
            SELECT user_id, nickname, rating, wins, losses 
            FROM users 
            WHERE banned = 0 
            ORDER BY rating DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_money(self, limit=10):
        self.cursor.execute('''
            SELECT user_id, nickname, balance 
            FROM users 
            WHERE banned = 0 
            ORDER BY balance DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_hp(self, limit=10):
        self.cursor.execute('''
            SELECT u.user_id, u.nickname, 
            (c.hp + COALESCE(e.hp_bonus, 0) + COALESCE(t.hp_bonus, 0) + 
             COALESCE(ex.hp_bonus, 0) + COALESCE(r.hp_bonus, 0) + COALESCE(n.hp_bonus, 0)) as total_hp
            FROM users u
            JOIN user_cars uc ON u.current_car_id = uc.car_id AND u.user_id = uc.user_id
            JOIN cars_catalog c ON uc.car_id = c.id
            LEFT JOIN parts_engines e ON uc.engine_id = e.id
            LEFT JOIN parts_turbos t ON uc.turbo_id = t.id
            LEFT JOIN parts_exhausts ex ON uc.exhaust_id = ex.id
            LEFT JOIN parts_radiators r ON uc.radiator_id = r.id
            LEFT JOIN parts_nos n ON uc.nos_id = n.id
            WHERE u.banned = 0
            ORDER BY total_hp DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_accel(self, limit=10):
        self.cursor.execute('''
            SELECT u.user_id, u.nickname, c.accel
            FROM users u
            JOIN user_cars uc ON u.current_car_id = uc.car_id AND u.user_id = uc.user_id
            JOIN cars_catalog c ON uc.car_id = c.id
            WHERE u.banned = 0
            ORDER BY c.accel ASC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_top_followers(self, limit=10):
        self.cursor.execute('''
            SELECT user_id, nickname, followers
            FROM users 
            WHERE banned = 0 
            ORDER BY followers DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def use_promocode(self, user_id, code):
        self.cursor.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
        promo = self.cursor.fetchone()
        if not promo:
            return False, "Промокод не найден!"
        
        promo_code, reward, uses, max_uses = promo
        if uses >= max_uses:
            return False, "Промокод уже использован максимальное количество раз!"
        
        self.cursor.execute("SELECT promo_used FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        if user and code in (user[0] or "").split(","):
            return False, "Вы уже использовали этот промокод!"
        
        self.cursor.execute("UPDATE promocodes SET uses = uses + 1 WHERE code = ?", (code,))
        self.cursor.execute("UPDATE users SET balance = balance + ?, promo_used = COALESCE(promo_used, '') || ',' || ? WHERE user_id = ?", 
                           (reward, code, user_id))
        self.conn.commit()
        return True, reward

# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🏁 Гонка с ботом", callback_data="race_bot")],
        [InlineKeyboardButton("⚔️ Дуэль с игроком", callback_data="duel_start")],
        [InlineKeyboardButton("🏪 Автосалон", callback_data="dealership")],
        [InlineKeyboardButton("🔧 Тюнинг", callback_data="tuning")],
        [InlineKeyboardButton("🏆 Топы", callback_data="top_menu")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("🎁 Промокод", callback_data="promo")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_top_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating")],
        [InlineKeyboardButton("💰 По деньгам", callback_data="top_money")],
        [InlineKeyboardButton("🐎 По л.с.", callback_data="top_hp")],
        [InlineKeyboardButton("⚡ По разгону", callback_data="top_accel")],
        [InlineKeyboardButton("📱 По подписчикам", callback_data="top_followers")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_dealership_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇪🇺 Европейские", callback_data="market_europe")],
        [InlineKeyboardButton("🇯🇵 Азиатские", callback_data="market_asia")],
        [InlineKeyboardButton("🇺🇸 Американские", callback_data="market_america")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tuning_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔧 Двигатели", callback_data="tuning_engine")],
        [InlineKeyboardButton("💨 Турбины", callback_data="tuning_turbo")],
        [InlineKeyboardButton("🎵 Выхлопы", callback_data="tuning_exhaust")],
        [InlineKeyboardButton("❄️ Радиаторы", callback_data="tuning_radiator")],
        [InlineKeyboardButton("💥 Закись азота", callback_data="tuning_nos")],
        [InlineKeyboardButton("🏎️ Подвеска", callback_data="tuning_suspension")],
        [InlineKeyboardButton("🛞 Покрышки", callback_data="tuning_tires")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = context.bot_data['db']
    
    # Проверка бана
    user_data = db.get_user(user.id)
    if user_data and user_data[9]:  # banned
        await update.message.reply_text("⛔ Вы забанены в боте!")
        return ConversationHandler.END
    
    if not user_data:
        await update.message.reply_text(
            f"🏎️ *Добро пожаловать в Racing Bot, {user.first_name}!*\n\n"
            "Стань лучшим уличным гонщиком! Зарабатывай деньги, улучшай машину, "
            "соревнуйся с другими игроками и покоряй топы!\n\n"
            "📝 *Для начала придумай себе никнейм (только буквы, цифры и _)*:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return CHOOSE_NAME
    else:
        await update.message.reply_text(
            f"🏎️ *С возвращением, {user_data[2]}!*\n\n"
            "Выберите действие:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return MAIN_MENU

async def choose_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_а-яА-ЯёЁ\s]{3,20}$', nickname):
        await update.message.reply_text(
            "❌ Некорректный никнейм! Используйте только буквы, цифры и _ (от 3 до 20 символов).\n"
            "Попробуйте ещё раз:"
        )
        return CHOOSE_NAME
    
    user = update.effective_user
    db = context.bot_data['db']
    
    db.create_user(user.id, user.username or "", nickname)
    
    # Обучение
    await update.message.reply_text(
        f"✅ *Отлично, {nickname}!*\n\n"
        "Давай пройдём обучение. Я расскажу, как устроена игра.\n\n"
        "Сейчас тебе нужно выбрать свою первую машину. У тебя есть 3 варианта:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Показываем первую машину
    context.user_data['tutorial_car_index'] = 0
    context.user_data['tutorial_cars'] = [
        ("mitsubishi_lancer", "Mitsubishi Lancer X", 150, 8.5, 210),
        ("opel_insignia", "Opel Insignia OPC", 325, 5.8, 270),
        ("cadillac_cts", "Cadillac CTS", 335, 5.6, 260)
    ]
    
    await show_tutorial_car(update, context)
    return CHOOSE_CAR

async def show_tutorial_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['tutorial_car_index']
    cars = context.user_data['tutorial_cars']
    car = cars[index]
    
    text = f"🚗 *{car[1]}*\n\n"
    text += f"🐎 Мощность: {car[2]} л.с.\n"
    text += f"⚡ Разгон 0-100: {car[3]} сек\n"
    text += f"💨 Макс. скорость: {car[4]} км/ч\n"
    
    keyboard = []
    row = []
    if index > 0:
        row.append(InlineKeyboardButton("◀️ Назад", callback_data="tutorial_prev"))
    row.append(InlineKeyboardButton("✅ Выбрать", callback_data=f"tutorial_select_{index}"))
    if index < len(cars) - 1:
        row.append(InlineKeyboardButton("▶️ Далее", callback_data="tutorial_next"))
    keyboard.append(row)
    
    # Здесь можно добавить фото машины
    # await update.message.reply_photo(photo=open(f"cars/{car[0]}.jpg", "rb"), caption=text, ...)
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def tutorial_car_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "tutorial_prev":
        context.user_data['tutorial_car_index'] -= 1
        await show_tutorial_car(query, context)
    elif data == "tutorial_next":
        context.user_data['tutorial_car_index'] += 1
        await show_tutorial_car(query, context)
    elif data.startswith("tutorial_select_"):
        index = int(data.split("_")[2])
        car = context.user_data['tutorial_cars'][index]
        db = context.bot_data['db']
        user = update.effective_user
        
        # Добавляем машину в гараж
        db.add_user_car(user.id, car[0])
        db.select_car(user.id, car[0])
        
        await query.edit_message_text(
            f"🎉 *Отлично! Вы выбрали {car[1]}!*\n\n"
            "Теперь давай попробуем первую гонку. Нажми кнопку «Готов», "
            "чтобы подготовиться к старту.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏁 Готов", callback_data="race_ready")
            ]])
        )
        return RACE_WAIT

async def race_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⏳ *Приготовьтесь!*\n\n"
        "Когда появится кнопка «СТАРТ», нажмите её ровно через 5 секунд! "
        "Если нажмёте раньше — фальстарт, позже — опоздание.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Запускаем таймер
    context.user_data['race_start_time'] = time.time()
    context.user_data['race_timer_started'] = True
    
    # Через 3 секунды покажем кнопку
    await asyncio.sleep(3)
    
    await query.edit_message_text(
        "🏁 *ВНИМАНИЕ!*\n\n"
        "Нажмите СТАРТ ровно через 5 секунд после появления кнопки!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🚦 СТАРТ", callback_data="race_start")
        ]])
    )
    context.user_data['race_button_time'] = time.time()
    return RACE_START

async def race_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    press_time = time.time()
    button_time = context.user_data.get('race_button_time', press_time)
    diff = press_time - button_time
    
    user = update.effective_user
    db = context.bot_data['db']
    user_data = db.get_user(user.id)
    
    if diff < 5:
        await query.edit_message_text(
            f"❌ *ФАЛЬСТАРТ!*\n\n"
            f"Вы нажали слишком рано (через {diff:.1f} сек). "
            f"Нужно было ровно через 5 секунд.\n\n"
            f"Попробуйте ещё раз в следующей гонке!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В меню", callback_data="main_menu")
            ]])
        )
        return MAIN_MENU
    elif diff > 6:
        await query.edit_message_text(
            f"⚠️ *Поздний старт!*\n\n"
            f"Вы нажали через {diff:.1f} сек. Задержка на старте!\n\n"
            f"Но вы всё равно проехали дистанцию...",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            f"✅ *Отличный старт!*\n\n"
            f"Вы нажали ровно через {diff:.1f} сек!\n\n"
            f"Машина рвёт с места!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Симуляция гонки
    car = db.get_user_car(user.id)
    if car:
        car_hp = car[7]  # hp из cars_catalog
        # Добавляем бонусы от запчастей (упрощённо)
        race_time = max(3, 10 - (car_hp / 100))
    else:
        race_time = 7
    
    await asyncio.sleep(2)
    
    # Финиш
    reward = random.randint(5000, 15000)
    followers = random.randint(10, 50)
    
    db.update_balance(user.id, reward)
    db.update_followers(user.id, followers)
    db.cursor.execute("UPDATE users SET wins = wins + 1 WHERE user_id = ?", (user.id,))
    db.conn.commit()
    
    text = f"🏁 *ФИНИШ!*\n\n"
    text += f"⏱️ Время заезда: {race_time:.2f} сек\n"
    text += f"💰 Награда: {reward} $\n"
    text += f"📱 Подписчики: +{followers}\n\n"
    text += f"🎉 *Обучение завершено!*\n\n"
    text += f"Теперь вы можете участвовать в гонках, покупать новые машины, "
    text += f"улучшать их и соревноваться с другими игроками!"
    
    await query.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )
    
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *Главное меню*\nВыберите действие:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return MAIN_MENU
    elif data == "race_bot":
        return await start_bot_race(update, context)
    elif data == "duel_start":
        return await duel_start(update, context)
    elif data == "dealership":
        await query.edit_message_text(
            "🏪 *Автосалон*\nВыберите рынок:",
            reply_markup=get_dealership_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return DEALERSHIP_MENU
    elif data == "tuning":
        await query.edit_message_text(
            "🔧 *Тюнинг*\nВыберите категорию запчастей:",
            reply_markup=get_tuning_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return TUNING_MENU
    elif data == "top_menu":
        await query.edit_message_text(
            "🏆 *Топы игроков*\nВыберите категорию:",
            reply_markup=get_top_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data.startswith("top_"):
        return await show_top(update, context)
    elif data == "profile":
        return await show_profile(update, context)
    elif data == "promo":
        await query.edit_message_text(
            "🎁 *Активация промокода*\n\n"
            "Отправьте промокод в чат:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]])
        )
        return PROMO_CODE
    elif data == "help":
        await query.edit_message_text(
            "ℹ️ *Помощь*\n\n"
            "🏁 *Гонка с ботом* - зарабатывайте деньги и подписчиков\n"
            "⚔️ *Дуэль* - соревнуйтесь с другими игроками\n"
            "🏪 *Автосалон* - покупайте новые машины\n"
            "🔧 *Тюнинг* - улучшайте характеристики\n"
            "🏆 *Топы* - следите за рейтингом\n\n"
            "📝 *Промокоды:* WELCOME2024, RACINGBOT, SPEED, FOLLOWERS, RICH\n\n"
            "👑 *Администраторы:* @username1, @username2",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    return MAIN_MENU

async def start_bot_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏁 *Гонка с ботом*\n\n"
        "Нажмите «Готов», чтобы начать заезд!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏁 Готов", callback_data="race_ready")
        ]])
    )
    return RACE_WAIT

async def duel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚔️ *Дуэль с игроком*\n\n"
        "Отправьте @username игрока, которого хотите вызвать на дуэль.\n"
        "Ставка: 5000 $ с каждого.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Отмена", callback_data="main_menu")
        ]])
    )
    return DUEL_SEARCH

async def duel_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("@"):
        await update.message.reply_text(
            "❌ Некорректный формат! Отправьте @username.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Отмена", callback_data="main_menu")
            ]])
        )
        return DUEL_SEARCH
    
    username = text[1:]
    db = context.bot_data['db']
    
    # Ищем пользователя по username
    db.cursor.execute("SELECT user_id, nickname FROM users WHERE username = ?", (username,))
    opponent = db.cursor.fetchone()
    
    if not opponent:
        await update.message.reply_text(
            "❌ Игрок не найден в боте!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Отмена", callback_data="main_menu")
            ]])
        )
        return DUEL_SEARCH
    
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if user_data[3] < 5000:  # balance
        await update.message.reply_text(
            "❌ У вас недостаточно денег для ставки (нужно 5000 $)!",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    # Создаём дуэль
    db.cursor.execute('''
        INSERT INTO duels (challenger_id, opponent_id, status, time)
        VALUES (?, ?, 'pending', ?)
    ''', (user.id, opponent[0], int(time.time())))
    db.conn.commit()
    duel_id = db.cursor.lastrowid
    
    await update.message.reply_text(
        f"⚔️ *Вызов отправлен!*\n\n"
        f"Ожидаем ответа от {opponent[1]}...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем уведомление оппоненту
    try:
        await context.bot.send_message(
            opponent[0],
            f"⚔️ *Вас вызывают на дуэль!*\n\n"
            f"Игрок {user_data[2]} вызывает вас на гонку.\n"
            f"Ставка: 5000 $\n\n"
            f"Принять вызов?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Принять", callback_data=f"duel_accept_{duel_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"duel_decline_{duel_id}")]
            ])
        )
    except:
        pass
    
    await update.message.reply_text(
        "✅ Вызов отправлен! Ожидайте ответа.",
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU

async def duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("duel_accept_"):
        duel_id = int(data.split("_")[2])
        db = context.bot_data['db']
        
        db.cursor.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
        duel = db.cursor.fetchone()
        if not duel or duel[3] != 'pending':
            await query.edit_message_text("❌ Дуэль уже неактивна!")
            return
        
        # Проверяем балансы
        challenger = db.get_user(duel[1])
        opponent = db.get_user(duel[2])
        
        if challenger[3] < 5000 or opponent[3] < 5000:
            await query.edit_message_text("❌ У одного из игроков недостаточно денег!")
            return
        
        # Списываем ставку
        db.update_balance(duel[1], -5000)
        db.update_balance(duel[2], -5000)
        
        # Обновляем статус
        db.cursor.execute("UPDATE duels SET status = 'accepted' WHERE id = ?", (duel_id,))
        db.conn.commit()
        
        # Запускаем дуэль для обоих
        for user_id in [duel[1], duel[2]]:
            await context.bot.send_message(
                user_id,
                "⚔️ *Дуэль начинается!*\n\n"
                "Нажмите «Готов», когда будете готовы к старту.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏁 Готов", callback_data=f"duel_ready_{duel_id}")
                ]])
            )
    
    elif data.startswith("duel_decline_"):
        duel_id = int(data.split("_")[2])
        db = context.bot_data['db']
        db.cursor.execute("UPDATE duels SET status = 'declined' WHERE id = ?", (duel_id,))
        db.conn.commit()
        
        await query.edit_message_text("❌ Вы отклонили вызов.")
        
        # Уведомляем вызывающего
        db.cursor.execute("SELECT challenger_id FROM duels WHERE id = ?", (duel_id,))
        duel = db.cursor.fetchone()
        if duel:
            try:
                await context.bot.send_message(duel[0], "❌ Ваш вызов на дуэль был отклонён.")
            except:
                pass

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    db = context.bot_data['db']
    
    if data == "top_rating":
        tops = db.get_top_rating(10)
        text = "🏆 *ТОП-10 ПО РЕЙТИНГУ*\n\n"
        for i, row in enumerate(tops, 1):
            text += f"{i}. {row[1]} - {row[2]} ⭐ (Побед: {row[3]}, Поражений: {row[4]})\n"
    
    elif data == "top_money":
        tops = db.get_top_money(10)
        text = "💰 *ТОП-10 ПО ДЕНЬГАМ*\n\n"
        for i, row in enumerate(tops, 1):
            text += f"{i}. {row[1]} - {row[2]:,} $\n"
    
    elif data == "top_hp":
        tops = db.get_top_hp(10)
        text = "🐎 *ТОП-10 ПО МОЩНОСТИ*\n\n"
        for i, row in enumerate(tops, 1):
            text += f"{i}. {row[1]} - {row[2]} л.с.\n"
    
    elif data == "top_accel":
        tops = db.get_top_accel(10)
        text = "⚡ *ТОП-10 ПО РАЗГОНУ*\n\n"
        for i, row in enumerate(tops, 1):
            text += f"{i}. {row[1]} - {row[2]} сек (0-100)\n"
    
    elif data == "top_followers":
        tops = db.get_top_followers(10)
        text = "📱 *ТОП-10 ПО ПОДПИСЧИКАМ*\n\n"
        for i, row in enumerate(tops, 1):
            text += f"{i}. {row[1]} - {row[2]} подписчиков\n"
    
    else:
        return
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="top_menu")
        ]])
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = context.bot_data['db']
    user_data = db.get_user(user.id)
    
    if not user_data:
        return
    
    car = db.get_user_car(user.id)
    car_name = car[6] if car else "Нет машины"
    car_hp = car[7] if car else 0
    
    text = f"👤 *Профиль {user_data[2]}*\n\n"
    text += f"🆔 ID: `{user.id}`\n"
    text += f"💰 Баланс: {user_data[3]:,} $\n"
    text += f"⭐ Рейтинг: {user_data[4]}\n"
    text += f"📱 Подписчики: {user_data[5]}\n"
    text += f"🏆 Побед: {user_data[6]}, Поражений: {user_data[7]}\n"
    text += f"🚗 Машина: {car_name}\n"
    text += f"🐎 Мощность: {car_hp} л.с.\n"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
        ]])
    )

async def promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    user = update.effective_user
    db = context.bot_data['db']
    
    success, result = db.use_promocode(user.id, code)
    
    if success:
        await update.message.reply_text(
            f"🎉 *Промокод активирован!*\n\n"
            f"На ваш счёт зачислено {result} $.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ {result}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]])
        )
    
    return MAIN_MENU

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к админ-панели!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "👑 *Админ-команды:*\n"
            "/admin ban [user_id] - забанить\n"
            "/admin unban [user_id] - разбанить\n"
            "/admin give [user_id] [amount] - выдать деньги\n"
            "/admin rating [user_id] [amount] - изменить рейтинг\n"
            "/admin promo [code] [reward] [max_uses] - добавить промокод",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    db = context.bot_data['db']
    cmd = args[0].lower()
    
    if cmd == "ban" and len(args) > 1:
        user_id = int(args[1])
        db.cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        db.conn.commit()
        await update.message.reply_text(f"✅ Пользователь {user_id} забанен.")
    
    elif cmd == "unban" and len(args) > 1:
        user_id = int(args[1])
        db.cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
        db.conn.commit()
        await update.message.reply_text(f"✅ Пользователь {user_id} разбанен.")
    
    elif cmd == "give" and len(args) > 2:
        user_id = int(args[1])
        amount = int(args[2])
        db.update_balance(user_id, amount)
        await update.message.reply_text(f"✅ Пользователю {user_id} выдано {amount} $.")
    
    elif cmd == "rating" and len(args) > 2:
        user_id = int(args[1])
        amount = int(args[2])
        db.update_rating(user_id, amount)
        await update.message.reply_text(f"✅ Рейтинг пользователя {user_id} изменён на {amount}.")
    
    elif cmd == "promo" and len(args) > 3:
        code = args[1].upper()
        reward = int(args[2])
        max_uses = int(args[3])
        db.cursor.execute(
            "INSERT OR REPLACE INTO promocodes (code, reward, max_uses) VALUES (?, ?, ?)",
            (code, reward, max_uses)
        )
        db.conn.commit()
        await update.message.reply_text(f"✅ Промокод {code} добавлен (награда: {reward}, использований: {max_uses}).")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ==================== ЗАПУСК БОТА ====================
def main():
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()
    
    # Инициализируем базу данных
    db = Database()
    application.bot_data['db'] = db
    
    # ConversationHandler для регистрации и основного меню
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_name)],
            CHOOSE_CAR: [CallbackQueryHandler(tutorial_car_callback, pattern='^tutorial_')],
            RACE_WAIT: [CallbackQueryHandler(race_ready, pattern='^race_ready$')],
            RACE_START: [CallbackQueryHandler(race_start, pattern='^race_start$')],
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler)],
            DUEL_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, duel_search_handler)],
            PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, promo_handler)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(duel_callback, pattern='^duel_'))
    application.add_handler(CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|race_bot|duel_start|dealership|tuning|top_menu|top_|profile|promo|help)$'))
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("=" * 60)
    print("🚗 RACING BOT ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎁 Промокоды: WELCOME2024, RACINGBOT, SPEED, FOLLOWERS, RICH")
    print("⚔️ Дуэли включены, время реакции: 5-6 секунд")
    print("💰 Улучшенная экономика, 5 видов топов")
    print("⚙️ Магазин запчастей, тюнинг машин")
    print("=" * 60)
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
