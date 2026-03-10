import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== FIREBASE ИНИЦИАЛИЗАЦИЯ =====
firebase_config_json = os.environ.get('FIREBASE_CONFIG')
if not firebase_config_json:
    raise Exception("❌ Переменная окружения FIREBASE_CONFIG не найдена! Проверь .env файл.")

config_dict = json.loads(firebase_config_json)
cred = credentials.Certificate(config_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://buda-clicker-default-rtdb.europe-west1.firebasedatabase.app/'  # твой URL
})
db_ref = db.reference('/')

# ===== КЛАВИАТУРА =====
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 ИГРАТЬ", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👥 Рефералы")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="💎 Премиум")]
        ],
        resize_keyboard=True
    )
    return keyboard

# ===== КОМАНДА /START =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "NoName"
    first_name = message.from_user.first_name or "NoName"

    # Проверка, есть ли пользователь в Firebase
    user_ref = db_ref.child('users').child(user_id)
    user_data = user_ref.get()
    if not user_data:
        user_ref.set({
            'name': first_name,
            'username': username,
            'clicks': 0,
            'balance': 0,
            'earned': 0,
            'referrals': 0,
            'premium': False
        })

    # Реферальная система
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if referrer_id != user_id:
            referrer_ref = db_ref.child('users').child(referrer_id)
            referrer_ref.child('referrals').transaction(lambda current: (current or 0) + 1)
            referrer_ref.child('balance').transaction(lambda current: (current or 0) + 100)

    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"Это Буда Кликер — жми кнопку внизу, чтобы начать.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ===== БАЛАНС =====
@dp.message(lambda msg: msg.text == "💰 Баланс")
async def handle_balance(message: types.Message):
    user_id = str(message.from_user.id)
    user_ref = db_ref.child('users').child(user_id)
    user_data = user_ref.get()
    if user_data:
        await message.answer(
            f"💰 **Баланс:** {user_data.get('balance', 0)} монет\n"
            f"👆 **Кликов:** {user_data.get('clicks', 0)}\n"
            f"📈 **Всего заработано:** {user_data.get('earned', 0)}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Данные не найдены. Нажми /start")

# ===== РЕФЕРАЛЫ =====
@dp.message(lambda msg: msg.text == "👥 Рефералы")
async def handle_ref(message: types.Message):
    user_id = str(message.from_user.id)
    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    user_ref = db_ref.child('users').child(user_id)
    user_data = user_ref.get()
    referrals = user_data.get('referrals', 0) if user_data else 0
    await message.answer(
        f"👥 **Твои рефералы:** {referrals}\n"
        f"• +100 монет за друга\n\n"
        f"👇 **Твоя ссылка:**\n`{ref_link}`",
        parse_mode="Markdown"
    )

# ===== ТОП =====
@dp.message(lambda msg: msg.text == "🏆 Топ")
async def handle_top(message: types.Message):
    users_snapshot = db_ref.child('users').get()
    if not users_snapshot:
        await message.answer("🏆 Топ пока пуст. Тыкай Буду первым!")
        return
    top_list = []
    for uid, data in users_snapshot.items():
        clicks = data.get('clicks', 0)
        if clicks > 0:
            top_list.append({
                'name': data.get('name', 'Unknown'),
                'clicks': clicks,
                'balance': data.get('balance', 0)
            })
    top_list.sort(key=lambda x: x['clicks'], reverse=True)
    top_list = top_list[:10]
    if not top_list:
        await message.answer("🏆 Топ пока пуст. Тыкай Буду первым!")
        return
    text = "🏆 **Топ игроков:**\n\n"
    for i, player in enumerate(top_list, 1):
        text += f"{i}. {player['name']} — {player['clicks']} кликов (💰 {player['balance']})\n"
    await message.answer(text, parse_mode="Markdown")

# ===== ПРЕМИУМ (ЗВЁЗДЫ) =====
@dp.message(lambda msg: msg.text == "💎 Премиум")
async def handle_premium(message: types.Message):
    prices = [types.LabeledPrice(label="Премиум на месяц", amount=100)]
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title="💎 Премиум Буда Кликер",
        description="Премиум: x2 монет, +50 энергии",
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
    user_id = str(message.from_user.id)
    db_ref.child('users').child(user_id).update({'premium': True})
    await message.answer("💎 **Ты теперь Премиум-тыкатель!**", parse_mode="Markdown")

# ===== ПОЛУЧЕНИЕ ДАННЫХ ИЗ ИГРЫ =====
@dp.message(lambda message: message.web_app_data is not None)
async def web_app_data_handler(message: types.Message):
    user_id = str(message.from_user.id)
    data = json.loads(message.web_app_data.data)
    action = data.get('action')
    user_ref = db_ref.child('users').child(user_id)
    if action in ['click', 'sync']:
        balance = data.get('balance')
        total_clicks = data.get('totalClicks')
        total_earned = data.get('totalEarned')
        user_ref.update({
            'balance': balance,
            'clicks': total_clicks,
            'earned': total_earned
        })
    elif action == 'upgrade':
        balance = data.get('balance')
        user_ref.update({'balance': balance})

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
