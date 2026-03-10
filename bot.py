import asyncio
import logging
import json
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            total_clicks INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ===== КЛАВИАТУРА =====
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 ИГРАТЬ", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👥 Рефералы")],
            [KeyboardButton(text="🏆 Топ")]
        ],
        resize_keyboard=True
    )
    return keyboard

# ===== КОМАНДА /START =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass

    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    
    # Создаём пользователя
    cur.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, referrer_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, referrer_id))
    
    # Начисляем бонус рефереру
    if referrer_id and referrer_id != user_id:
        cur.execute('''
            UPDATE users 
            SET referrals = referrals + 1, balance = balance + 100 
            WHERE user_id = ?
        ''', (referrer_id,))
    
    conn.commit()
    conn.close()

    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"Это Буда Кликер — нажимай на фото, зарабатывай монеты и становись лучшим!",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ===== БАЛАНС =====
@dp.message(lambda msg: msg.text == "💰 Баланс")
async def handle_balance(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('SELECT balance, total_clicks, total_earned FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        await message.answer(
            f"💰 **Баланс:** {row[0]} монет\n"
            f"👆 **Кликов:** {row[1]}\n"
            f"📈 **Всего заработано:** {row[2]}",
            parse_mode="Markdown"
        )

# ===== РЕФЕРАЛЫ =====
@dp.message(lambda msg: msg.text == "👥 Рефералы")
async def handle_ref(message: types.Message):
    user_id = message.from_user.id
    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('SELECT referrals FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()

    referrals = row[0] if row else 0
    await message.answer(
        f"👥 **Твои рефералы:** {referrals}\n"
        f"• +100 монет за каждого друга\n\n"
        f"👇 **Твоя ссылка:**\n`{ref_link}`",
        parse_mode="Markdown"
    )

# ===== ТОП =====
@dp.message(lambda msg: msg.text == "🏆 Топ")
async def handle_top(message: types.Message):
    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT first_name, total_clicks, balance 
        FROM users 
        WHERE total_clicks > 0 
        ORDER BY total_clicks DESC 
        LIMIT 10
    ''')
    top = cur.fetchall()
    conn.close()

    if not top:
        text = "🏆 Топ пока пуст. Тыкай Буду первым!"
    else:
        text = "🏆 **Топ игроков:**\n\n"
        for i, (name, clicks, balance) in enumerate(top, 1):
            text += f"{i}. {name} — {clicks} кликов (💰 {balance})\n"
    
    await message.answer(text, parse_mode="Markdown")

# ===== ПОЛУЧЕНИЕ ДАННЫХ ИЗ ИГРЫ =====
@dp.message(lambda message: message.web_app_data is not None)
async def web_app_data_handler(message: types.Message):
    user_id = message.from_user.id
    data = json.loads(message.web_app_data.data)
    action = data.get('action')

    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()

    if action in ['click', 'sync']:
        balance = data.get('balance')
        total_clicks = data.get('totalClicks')
        total_earned = data.get('totalEarned')
        
        cur.execute('''
            UPDATE users 
            SET balance = ?, total_clicks = ?, total_earned = ? 
            WHERE user_id = ?
        ''', (balance, total_clicks, total_earned, user_id))

    elif action == 'upgrade':
        balance = data.get('balance')
        cur.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance, user_id))

    conn.commit()
    conn.close()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
