import asyncio
import logging
import json
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from database import init_db, get_user, update_user, add_purchase, get_top_users

BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()

# Промокоды (в реальном проекте лучше хранить в БД)
VALID_PROMOS = {
    "BUDAPROMO": 500,
    "BUDA100": 100,
    "STARTER": 50
}

def get_fatness_stage(clicks):
    if clicks >= 1_000_000:
        return "🌍 Буда-планета"
    elif clicks >= 500_000:
        return "🛢️ Буда-бочка"
    elif clicks >= 100_000:
        return "🐷 Буда-телепузик"
    elif clicks >= 10_000:
        return "⚪ Буда-колобок"
    elif clicks >= 1_000:
        return "🥟 Буда-пухлик"
    elif clicks >= 100:
        return "🍩 Буда-пончик"
    else:
        return "😤 Буда-спичка"

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 ИГРАТЬ В БУДУ", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👥 Рефералы")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="💎 Премиум")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие..."
    )
    return keyboard

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

    user = get_user(user_id, username, first_name, referrer_id)
    fatness = get_fatness_stage(user['total_clicks'])

    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"Это кликер **толстого друга Буды**!\n\n"
        f"📊 **Твоя статистика:**\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"👆 Кликов: {user['total_clicks']}\n"
        f"🍔 Стадия: {fatness}\n"
        f"👥 Рефералов: {user['referrals']}",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text == "💰 Баланс")
async def handle_balance(message: types.Message):
    user = get_user(message.from_user.id)
    fatness = get_fatness_stage(user['total_clicks'])
    await message.answer(
        f"💰 **Твой баланс:** {user['balance']} монет\n"
        f"👆 **Кликов:** {user['total_clicks']}\n"
        f"🍔 **Буда:** {fatness}",
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text == "👥 Рефералы")
async def handle_ref(message: types.Message):
    user_id = message.from_user.id
    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    await message.answer(
        f"👥 **Реферальная система**\n\n"
        f"• **100 монет** за друга\n"
        f"• **10%** от их покупок\n\n"
        f"👇 **Твоя ссылка:**\n"
        f"`{ref_link}`",
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text == "🏆 Топ")
async def handle_top(message: types.Message):
    top_users = get_top_users(10)
    if not top_users:
        text = "🏆 Топ пока пуст. Тыкай Буду первым!"
    else:
        text = "🏆 **Топ тыкателей:**\n\n"
        for i, (name, clicks, balance) in enumerate(top_users, 1):
            fatness = get_fatness_stage(clicks)
            text += f"{i}. {name} — {clicks} {fatness} (💰 {balance})\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "💎 Премиум")
async def handle_premium(message: types.Message):
    prices = [types.LabeledPrice(label="Премиум на месяц", amount=100)]
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title="💎 Премиум Буда Кликер",
        description="Премиум: x2 монет, +50 энергии, скины, без рекламы",
        payload="premium_month",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(lambda message: message.successful_payment is not None)
async def payment_handler(message: types.Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload == "premium_month":
        from datetime import datetime, timedelta
        expire_date = datetime.now() + timedelta(days=30)
        update_user(user_id, premium=True, premium_expire=expire_date)
        add_purchase(user_id, "premium_month", 100)
        await message.answer(
            "💎 **Ты теперь Премиум-тыкатель!**",
            parse_mode="Markdown"
        )

# ===== ПОЛУЧЕНИЕ ДАННЫХ ИЗ MINI APP =====
@dp.message(lambda message: message.web_app_data is not None)
async def web_app_data_handler(message: types.Message):
    user_id = message.from_user.id
    data = json.loads(message.web_app_data.data)
    action = data.get('action')

    conn = sqlite3.connect('buda.db')
    cur = conn.cursor()

    if action == 'click':
        earned = data.get('earned', 0)
        total_clicks = data.get('totalClicks')
        total_earned = data.get('totalEarned')
        crit_count = data.get('critCount')

        cur.execute('''
            UPDATE users 
            SET total_clicks = ?, balance = balance + ?, total_earned = ?, crit_count = ?
            WHERE user_id = ?
        ''', (total_clicks, earned, total_earned, crit_count, user_id))
        conn.commit()

    elif action == 'sync':
        total_clicks = data.get('totalClicks')
        balance = data.get('balance')
        total_earned = data.get('totalEarned')
        crit_count = data.get('critCount')

        cur.execute('''
            UPDATE users 
            SET total_clicks = ?, balance = ?, total_earned = ?, crit_count = ?
            WHERE user_id = ?
        ''', (total_clicks, balance, total_earned, crit_count, user_id))
        conn.commit()

    elif action == 'upgrade':
        balance = data.get('balance')
        cur.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance, user_id))
        conn.commit()

    elif action == 'promo':
        code = data.get('code')
        if code in VALID_PROMOS:
            bonus = VALID_PROMOS[code]
            cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (bonus, user_id))
            conn.commit()
            await message.answer(f"✅ Промокод активирован! Ты получил {bonus} монет.")
        else:
            await message.answer("❌ Неверный промокод.")

    conn.close()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
