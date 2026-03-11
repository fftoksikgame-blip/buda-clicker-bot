import asyncio
import logging
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, db

# ===== ТВОИ ДАННЫЕ (ЗАМЕНИ НА СВОИ) =====
BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"
ADMIN_ID = 2048960464  # твой Telegram ID

# ===== FIREBASE (ВСТАВЬ СВОЙ КЛЮЧ И URL) =====
FIREBASE_CONFIG_JSON = '{"type": "service_account", "project_id": "buda-clicker", "private_key_id": "...", "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n", "client_email": "...", "client_id": "...", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "...", "universe_domain": "googleapis.com"}'
FIREBASE_DATABASE_URL = "https://buda-clicker-default-rtdb.europe-west1.firebasedatabase.app/"  # твой URL

# ===== ИНИЦИАЛИЗАЦИЯ =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Firebase
try:
    cred = credentials.Certificate(json.loads(FIREBASE_CONFIG_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
    db_ref = db.reference('/')
    users_ref = db_ref.child('users')
    logs_ref = db_ref.child('logs')
    logging.info("✅ Firebase подключен")
except Exception as e:
    logging.error(f"❌ Ошибка подключения Firebase: {e}")
    raise

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
        # Новый пользователь
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

    # Реферальная система
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if referrer_id != user_id:
            referrer_ref = users_ref.child(referrer_id)
            # Увеличиваем счетчик рефералов и баланс реферера
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
        f"Это Буда Кликер — жми кнопку внизу, чтобы начать.",
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
    if not top_list:
        await message.answer("🏆 Топ пока пуст. Тыкай Буду первым!")
        return
    text = "🏆 **Топ игроков:**\n\n"
    for i, player in enumerate(top_list[:10], 1):
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
    users_ref.child(user_id).update({'premium': True})
    logs_ref.push({
        'userId': user_id,
        'action': 'premium_purchased',
        'timestamp': datetime.now().isoformat()
    })
    await message.answer("💎 **Ты теперь Премиум-тыкатель!**", parse_mode="Markdown")

# ===== АДМИН-ПАНЕЛЬ (только для ADMIN_ID) =====
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
        "/setpremium ID — выдать премиум\n"
        "/stats — статистика пользователей\n"
        "/user ID — информация о пользователе\n"
        "/logs — последние действия"
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
        # Добавляем монеты через транзакцию
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

@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    logs_snapshot = logs_ref.order_by_key().limit_to_last(10).get()
    if not logs_snapshot:
        await message.answer("Логов пока нет.")
        return
    text = "📋 **Последние действия:**\n\n"
    # Сортируем по убыванию ключа (чем больше ключ, тем новее запись)
    for key, log in sorted(logs_snapshot.items(), reverse=True)[:10]:
        text += f"• {log.get('action')} от {log.get('userId')} [{log.get('timestamp')}]\n"
    await message.answer(text, parse_mode="Markdown")

# ===== ПОЛУЧЕНИЕ ДАННЫХ ИЗ ИГРЫ (КЛИКИ) =====
@dp.message(lambda message: message.web_app_data is not None)
async def web_app_data_handler(message: types.Message):
    user_id = str(message.from_user.id)
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        logging.info(f"📦 Получены данные от {user_id}: action={action}")

        user_ref = users_ref.child(user_id)

        if action in ['click', 'sync']:
            balance = data.get('balance')
            total_clicks = data.get('totalClicks')
            total_earned = data.get('totalEarned')
            # Обновляем все поля
            user_ref.update({
                'balance': balance,
                'clicks': total_clicks,
                'earned': total_earned
            })
            logging.info(f"✅ Обновлены данные {user_id}: клики={total_clicks}, баланс={balance}")
        elif action == 'upgrade':
            balance = data.get('balance')
            user_ref.update({'balance': balance})
            logging.info(f"✅ Обновлён баланс {user_id} после улучшения: {balance}")

    except Exception as e:
        logging.error(f"❌ Ошибка обработки данных от {user_id}: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
