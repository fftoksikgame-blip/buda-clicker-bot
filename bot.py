import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import init_db, get_user, update_user, add_purchase, get_top_users

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"  # Токен от BotFather
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"
# Когда зальёшь на сервер, замени на: "https://твой-сайт.ру"

# ===== НАСТРОЙКИ =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
init_db()

def get_fatness_stage(clicks):
    """Определяет стадию толстоты Буды по количеству кликов"""
    if clicks >= 1_000_000:
        return {"name": "Буда-планета", "emoji": "🌍", "level": 7}
    elif clicks >= 500_000:
        return {"name": "Буда-бочка", "emoji": "🛢️", "level": 6}
    elif clicks >= 100_000:
        return {"name": "Буда-телепузик", "emoji": "🐷", "level": 5}
    elif clicks >= 10_000:
        return {"name": "Буда-колобок", "emoji": "⚪", "level": 4}
    elif clicks >= 1_000:
        return {"name": "Буда-пухлик", "emoji": "🥟", "level": 3}
    elif clicks >= 100:
        return {"name": "Буда-пончик", "emoji": "🍩", "level": 2}
    else:
        return {"name": "Буда-спичка", "emoji": "😤", "level": 1}

def main_keyboard():
    """Создаёт главную клавиатуру (без WebApp для локального теста)"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
            [InlineKeyboardButton(text="🏆 Топ", callback_data="top")],
            [InlineKeyboardButton(text="💎 Премиум", callback_data="premium")]
        ]
    )
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Проверка реферального кода
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None  # Нельзя рефернуть себя
        except:
            pass
    
    # Получаем или создаём пользователя
    user = get_user(user_id, username, first_name, referrer_id)
    
    # Определяем стадию толстоты
    fatness = get_fatness_stage(user['total_clicks'])
    
    # Отправляем приветствие
    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"Это кликер **толстого друга Буды**!\n"
        f"Тыкай по нему, смотри как он толстеет и зарабатывай монеты.\n\n"
        f"📊 **Твоя статистика:**\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"👆 Кликов: {user['total_clicks']}\n"
        f"🍔 Стадия Буды: {fatness['emoji']} {fatness['name']}\n"
        f"👥 Рефералов: {user['referrals']}\n\n"
        f"👇 **Жми кнопку ниже, чтобы начать тыкать Буду!**",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Показать баланс"""
    user = get_user(message.from_user.id)
    fatness = get_fatness_stage(user['total_clicks'])
    
    await message.answer(
        f"💰 **Твой баланс:** {user['balance']} монет\n"
        f"👆 **Всего кликов:** {user['total_clicks']}\n"
        f"🍔 **Буда сейчас:** {fatness['emoji']} {fatness['name']}\n"
        f"⚡ **Энергия:** {user['energy']}/{user['max_energy']}",
        parse_mode="Markdown"
    )

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    """Показать топ игроков"""
    top_users = get_top_users(10)
    
    if not top_users:
        text = "🏆 Топ пока пуст. Тыкай Буду первым!"
    else:
        text = "🏆 **Топ тыкателей Буды:**\n\n"
        for i, (name, clicks, balance) in enumerate(top_users, 1):
            fatness = get_fatness_stage(clicks)
            text += f"{i}. {name} — {clicks} тыков {fatness['emoji']}\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "balance")
async def callback_balance(callback: types.CallbackQuery):
    await cmd_balance(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ref")
async def callback_ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.me()).username
    
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    await callback.message.answer(
        f"👥 **Реферальная система**\n\n"
        f"Приглашай друзей и получай:\n"
        f"• **100 монет** за каждого друга\n"
        f"• **10%** от их покупок (навсегда)\n\n"
        f"👇 **Твоя ссылка:**\n"
        f"`{ref_link}`\n\n"
        f"Отправь её друзьям!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "top")
async def callback_top(callback: types.CallbackQuery):
    await cmd_top(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "premium")
async def callback_premium(callback: types.CallbackQuery):
    """Покупка премиума за Telegram Stars"""
    prices = [types.LabeledPrice(label="Премиум на месяц", amount=100)]  # 100 Stars
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💎 Премиум Буда Кликер",
        description="Премиум даёт:\n• x2 монет за клик\n• +50 энергии\n• Уникальные скины\n• Без рекламы",
        payload="premium_month",
        provider_token="",  # Для Stars оставляем пустым
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(lambda message: message.successful_payment is not None)
async def payment_handler(message: types.Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    if payload == "premium_month":
        # Активируем премиум на 30 дней
        from datetime import datetime, timedelta
        expire_date = datetime.now() + timedelta(days=30)
        
        update_user(user_id, premium=True, premium_expire=expire_date)
        add_purchase(user_id, "premium_month", 100)
        
        await message.answer(
            "💎 **Поздравляю! Ты теперь Премиум-тыкатель!**\n\n"
            "Все бонусы активированы. Иди тыкать Буду!",
            parse_mode="Markdown"
        )

async def main():
    print("🤖 Будapь запущен! Жму ссылки...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())