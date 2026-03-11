import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

load_dotenv()  # загружаем переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 2048960464))  # твой ID по умолчанию

if not BOT_TOKEN or not WEBAPP_URL:
    raise Exception("❌ BOT_TOKEN или WEBAPP_URL не заданы в .env")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== FIREBASE =====
firebase_config_json = os.getenv("FIREBASE_CONFIG")
if not firebase_config_json:
    raise Exception("❌ Переменная окружения FIREBASE_CONFIG не найдена! Добавь её в .env")

config_dict = json.loads(firebase_config_json)
cred = credentials.Certificate(config_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("FIREBASE_DATABASE_URL")  # тоже из .env
})
db_ref = db.reference('/')
users_ref = db_ref.child('users')
promos_ref = db_ref.child('promocodes')
logs_ref = db_ref.child('logs')

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

    user_ref = users_ref.child(user_id)
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
        logs_ref.push({
            'userId': user_id,
            'action': 'first_start',
            'timestamp': datetime.now().isoformat()
        })

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if referrer_id != user_id:
            referrer_ref = users_ref.child(referrer_id)
            referrer_ref.child('referrals').transaction(lambda current: (current or 0) + 1)
            referrer_ref.child('balance').transaction(lambda current: (current or 0) + 100)
            logs_ref.push({
                'userId': referrer_id,
                'action': 'referral_bonus',
                'from': user_id,
                'timestamp': datetime.now().isoformat()
            })

    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"Это Буда Кликер 2.0 — жми кнопку внизу, чтобы начать.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ===== БАЛАНС =====
@dp.message(lambda msg: msg.text == "💰 Баланс")
async def handle_balance(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = users_ref.child(user_id).get()
    if user_data:
        await message.answer(
            f"💰 **Баланс:** {user_data.get('balance', 0)} монет\n"
            f"👆 **Кликов:** {user_data.get('clicks', 0)}\n"
            f"📈 **Всего заработано:** {user_data.get('earned', 0)}\n"
            f"💎 **Премиум:** {'Да' if user_data.get('premium') else 'Нет'}",
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
    user_data = users_ref.child(user_id).get()
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
    users_snapshot = users_ref.order_by_child('clicks').limit_to_last(10).get()
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
    text = "🏆 **Топ игроков:**\n\n"
    for i, player in enumerate(top_list[:10], 1):
        text += f"{i}. {player['name']} — {player['clicks']} кликов (💰 {player['balance']})\n"
    await message.answer(text, parse_mode="Markdown")

# ===== ПРЕМИУМ =====
@dp.message(lambda msg: msg.text == "💎 Премиум")
async def handle_premium(message: types.Message):
    prices = [types.LabeledPrice(label="Премиум на месяц", amount=100)]
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title="💎 Премиум Буда Кликер",
        description="Премиум: x2 монет, +50 энергии, автокликер",
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
    users_ref.child(user_id).update({'premium': True})
    logs_ref.push({
        'userId': user_id,
        'action': 'premium_purchased',
        'timestamp': datetime.now().isoformat()
    })
    await message.answer("💎 **Ты теперь Премиум-тыкатель! Автокликер активирован.**", parse_mode="Markdown")

# ===== АДМИН-ПАНЕЛЬ =====
def is_admin(user_id):
    return user_id == ADMIN_ID

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    text = (
        "🔐 **Админ-панель**\n\n"
        "Команды:\n"
        "/givecoins ID сумма — выдать монеты\n"
        "/giveenergy ID количество — установить энергию\n"
        "/setpremium ID — выдать премиум\n"
        "/createpromo код сумма [лимит] — создать промокод\n"
        "/stats — статистика пользователей\n"
        "/user ID — информация о пользователе"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("givecoins"))
async def cmd_givecoins(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /givecoins ID сумма")
        return
    try:
        target_id = args[1]
        amount = int(args[2])
        users_ref.child(target_id).child('balance').transaction(lambda current: (current or 0) + amount)
        logs_ref.push({
            'adminId': message.from_user.id,
            'action': 'givecoins',
            'target': target_id,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        })
        await message.answer(f"✅ Пользователю {target_id} выдано {amount} монет.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("giveenergy"))
async def cmd_giveenergy(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /giveenergy ID количество")
        return
    try:
        target_id = args[1]
        energy = int(args[2])
        users_ref.child(target_id).update({'admin_energy': energy})
        await message.answer(f"✅ Энергия пользователя {target_id} установлена на {energy} (будет применена при следующем заходе).")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("setpremium"))
async def cmd_setpremium(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /setpremium ID")
        return
    target_id = args[1]
    users_ref.child(target_id).update({'premium': True})
    logs_ref.push({
        'adminId': message.from_user.id,
        'action': 'setpremium',
        'target': target_id,
        'timestamp': datetime.now().isoformat()
    })
    await message.answer(f"✅ Пользователь {target_id} теперь премиум.")

@dp.message(Command("createpromo"))
async def cmd_createpromo(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /createpromo код сумма [лимит]")
        return
    code = args[1].upper()
    amount = int(args[2])
    limit = int(args[3]) if len(args) > 3 else 1
    promos_ref.child(code).set({
        'amount': amount,
        'limit': limit,
        'used': 0,
        'created': datetime.now().isoformat()
    })
    await message.answer(f"✅ Промокод {code} создан на {amount} монет, лимит {limit} использований.")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    users_snapshot = users_ref.get()
    if not users_snapshot:
        await message.answer("Нет пользователей.")
        return
    total_users = len(users_snapshot)
    total_clicks = sum(u.get('clicks', 0) for u in users_snapshot.values())
    total_earned = sum(u.get('earned', 0) for u in users_snapshot.values())
    premium_count = sum(1 for u in users_snapshot.values() if u.get('premium'))
    await message.answer(
        f"📊 **Статистика:**\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"👆 Всего кликов: {total_clicks}\n"
        f"💰 Всего заработано: {total_earned}\n"
        f"💎 Премиум: {premium_count}",
        parse_mode="Markdown"
    )

@dp.message(Command("user"))
async def cmd_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /user ID")
        return
    target_id = args[1]
    user_data = users_ref.child(target_id).get()
    if not user_data:
        await message.answer("❌ Пользователь не найден.")
        return
    await message.answer(
        f"👤 **Информация о пользователе {target_id}**\n"
        f"Имя: {user_data.get('name')}\n"
        f"Клики: {user_data.get('clicks')}\n"
        f"Баланс: {user_data.get('balance')}\n"
        f"Заработано: {user_data.get('earned')}\n"
        f"Рефералов: {user_data.get('referrals')}\n"
        f"Премиум: {'Да' if user_data.get('premium') else 'Нет'}",
        parse_mode="Markdown"
    )

# ===== ПОЛУЧЕНИЕ ДАННЫХ ИЗ ИГРЫ =====
@dp.message(lambda message: message.web_app_data is not None)
async def web_app_data_handler(message: types.Message):
    user_id = str(message.from_user.id)
    data = json.loads(message.web_app_data.data)
    action = data.get('action')
    user_ref = users_ref.child(user_id)

    if action in ['click', 'auto_click', 'sync']:
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
