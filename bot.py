import logging
import sqlite3
import asyncio
import random
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- НАСТРОЙКИ ---
TOKEN = "7969118140:AAHu0KE7nHpm03k12tMlaLJlMt43rfG_ITw"
ADMINS = [5189651311, 5887846215]
DB_NAME = "racing_game.db"

# Состояния диалога
REGISTER, TUTORIAL, GARAGE, SHOP_MARKETS, SHOP_MODELS, TUNING_PARTS, RACE_WAIT = range(7)

# --- БАЗА ДАННЫХ ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Игроки
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            nickname TEXT,
            balance INTEGER DEFAULT 50000,
            followers INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            selected_car_id INTEGER
        )''')
        # Машины игрока
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            model_name TEXT,
            hp INTEGER,
            accel REAL,
            top_speed INTEGER,
            photo_url TEXT
        )''')
        # Промокоды
        cursor.execute('''CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            reward INTEGER,
            used_by TEXT
        )''')
        self.conn.commit()

    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return cursor.fetchone()

    def add_user(self, user_id, username, nickname):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, nickname) VALUES (?, ?, ?)", 
                       (user_id, username, nickname))
        self.conn.commit()

db = Database()

# --- ДАННЫЕ ИГРЫ ---
CARS_DATA = {
    "Lancer X Sportback": {"hp": 168, "accel": 8.2, "price": 0, "photo": "https://example.com/lancer.jpg"},
    "Opel Insignia OPC": {"hp": 325, "accel": 6.0, "price": 0, "photo": "https://example.com/opel.jpg"},
    "Cadillac CTS": {"hp": 311, "accel": 6.3, "price": 0, "photo": "https://example.com/cadillac.jpg"}
}

# Список всех машин из твоего запроса (упрощенно для примера структуры)
MARKETS = {
    "Европейский": ["Volkswagen Golf", "BMW 5 Series", "Audi Q7", "Ferrari Roma", "Lamborghini Aventador", "Lada Granta"],
    "Азиатский": ["Toyota Supra", "Nissan Skyline GT-R", "Honda Civic", "Subaru Impreza", "Hyundai Tucson"],
    "Американский": ["Ford Mustang", "Chevrolet Corvette", "Dodge Challenger", "Tesla Model S"]
}

# --- ЛОГИКА БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Добро пожаловать в Racing Bot! 🏎\nВведите ваш никнейм для регистрации:")
        return REGISTER
    await main_menu(update)
    return ConversationHandler.END

async def register_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text
    db.add_user(update.effective_user.id, update.effective_user.username, nickname)
    
    # Приветствие и обучение
    text = f"Рад познакомиться, {nickname}!\n\nДавай пройдем обучение. Тебе нужно выбрать первую машину."
    # Путь к фото обучения
    photo_url = "https://example.com/tutorial_start.jpg" # ЗАМЕНИ НА СВОЮ
    
    keyboard = [[InlineKeyboardButton("Начать выбор машин 🚗", callback_query_data="tuto_cars")]]
    await update.message.reply_photo(photo=photo_url, caption=text, reply_markup=InlineKeyboardMarkup(keyboard))
    return TUTORIAL

async def tutorial_car_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    car_list = list(CARS_DATA.keys())
    index = context.user_data.get("tuto_idx", 0)
    car_name = car_list[index]
    car = CARS_DATA[car_name]

    text = f"Машина: {car_name}\nМощность: {car['hp']} л.с.\nРазгон до 100: {car['accel']} сек."
    
    btns = []
    if index > 0: btns.append(InlineKeyboardButton("⬅️ Назад", callback_query_data="tuto_prev"))
    btns.append(InlineKeyboardButton("✅ Выбрать", callback_query_data=f"tuto_select_{car_name}"))
    if index < len(car_list) - 1: btns.append(InlineKeyboardButton("Вперед ➡️", callback_query_data="tuto_next"))
    
    keyboard = [btns]
    await query.edit_message_media(
        media=InputMediaPhoto(car['photo'], caption=text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def tuto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    idx = context.user_data.get("tuto_idx", 0)

    if data == "tuto_next":
        context.user_data["tuto_idx"] = idx + 1
        await tutorial_car_choice(update, context)
    elif data == "tuto_prev":
        context.user_data["tuto_idx"] = idx - 1
        await tutorial_car_choice(update, context)
    elif data.startswith("tuto_select_"):
        car_name = data.replace("tuto_select_", "")
        # Сохраняем машину в базу
        cursor = db.conn.cursor()
        cursor.execute("INSERT INTO user_cars (user_id, model_name, hp, accel, top_speed) VALUES (?,?,?,?,?)",
                       (query.from_user.id, car_name, CARS_DATA[car_name]['hp'], CARS_DATA[car_name]['accel'], 220))
        car_id = cursor.lastrowid
        cursor.execute("UPDATE users SET selected_car_id = ? WHERE user_id = ?", (car_id, query.from_user.id))
        db.conn.commit()
        
        await query.message.reply_text("Отличный выбор! Машина в гараже. Известность не за горами! 🏆\nТеперь попробуем первую гонку. Нажми 'Готов'.")
        # Тут переход к логике обучения гонке...
        keyboard = [[InlineKeyboardButton("Готов!", callback_query_data="race_ready")]]
        await query.message.reply_markup(InlineKeyboardMarkup(keyboard))

async def race_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Гонка начинается... Жди сигнала СТАРТ!")
    
    await asyncio.sleep(5) # Интервал 5 секунд
    
    keyboard = [[InlineKeyboardButton("🚀 СТАРТ!", callback_query_data="race_click")]]
    context.user_data["start_time"] = time.time()
    await query.message.reply_text("ЖМИ СЕЙЧАС!", reply_markup=InlineKeyboardMarkup(keyboard))

async def race_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    click_time = time.time() - context.user_data.get("start_time", 0)
    
    if click_time < 0.1: # Нажал слишком быстро (фальстарт)
        await query.edit_message_text("❌ Фальстарт! Вы проиграли.")
    elif 0.1 <= click_time <= 1.5: # Попал в окно (идеально 5-6 сек после готовности)
        await query.edit_message_text(f"🔥 Мощный старт! ({click_time:.2f} сек)")
        # Имитация езды 500 метров
        await asyncio.sleep(3)
        await query.message.reply_text("🏁 Финиш! Ты победил. Награда: 5000$ и 10 подписчиков.")
        # Начисление денег в БД...
    else:
        await query.edit_message_text(f"🐌 Задержался на старте... ({click_time:.2f} сек)")
        await asyncio.sleep(4)
        await query.message.reply_text("🏁 Ты финишировал, но мог бы быстрее!")

# --- ГЛАВНОЕ МЕНЮ ---
async def main_menu(update: Update):
    text = "🏎 ГЛАВНОЕ МЕНЮ\nВыберите действие:"
    keyboard = [
        [InlineKeyboardButton("🏁 Гонка", callback_query_data="menu_race"), InlineKeyboardButton("🚗 Гараж", callback_query_data="menu_garage")],
        [InlineKeyboardButton("💰 Магазин", callback_query_data="menu_shop"), InlineKeyboardButton("🏆 Топы", callback_query_data="menu_top")],
        [InlineKeyboardButton("🎁 Промокод", callback_query_data="menu_promo")]
    ]
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- АДМИН ПАНЕЛЬ ---
async def admin_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    # Команда /give user_id amount
    _, uid, amt = update.message.text.split()
    cursor = db.conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    db.conn.commit()
    await update.message.reply_text("Деньги выданы!")

# --- ЗАПУСК ---
def main():
    # Исправляем ошибку с pool_timeout — просто удаляем её из параметров
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_nickname)],
            TUTORIAL: [CallbackQueryHandler(tuto_callback)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("give", admin_give))
    # Обработка нажатий кнопок меню
    application.add_handler(CallbackQueryHandler(race_ready, pattern="race_ready"))
    application.add_handler(CallbackQueryHandler(race_click, pattern="race_click"))

    print("==============================")
    print("🚗 БОТ ЗАПУЩЕН И ГОТОВ К ГОНКАМ")
    print("==============================")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
