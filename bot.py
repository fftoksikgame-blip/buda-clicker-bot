import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

BOT_TOKEN = "8116737200:AAGoOIBsT_89PIL1Yhz3Jikr7NwMdtrMAQY"
WEBAPP_URL = "https://fftoksikgame-blip.github.io/buda-clicker-app/"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== ОДНА КНОПКА ДЛЯ ЗАПУСКА ИГРЫ =====
def game_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 ИГРАТЬ В БУДУ", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True,
        input_field_placeholder="Нажми кнопку, чтобы играть..."
    )
    return keyboard

# ===== ТОЛЬКО /START =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Короткое приветствие — всё остальное в игре
    await message.answer(
        f"🚀 **Привет, {first_name}!**\n\n"
        f"👉 Нажми кнопку внизу, чтобы открыть **Буду Кликер**.\n"
        f"Там ты найдешь топ игроков, настройки и всё остальное.",
        reply_markup=game_keyboard(),
        parse_mode="Markdown"
    )

# ===== НИКАКИХ ДРУГИХ КОМАНД =====
# Весь функционал (баланс, топ, рефералы) теперь внутри игры

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
