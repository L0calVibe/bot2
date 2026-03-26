import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

# Ключи из Environment на Render
TOKEN = os.getenv("BOT_TOKEN")
G_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_places(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=5000&type=tourist_attraction&key={G_KEY}&language=ru"
    try:
        data = requests.get(url).json()
        if data.get("status") != "OK": return None
        
        res = []
        for item in data.get("results", [])[:8]:
            name = item.get("name")
            rating = item.get("rating", "—")
            addr = item.get("vicinity", "Адрес не указан")
            is_open = "✅ Открыто" if item.get("opening_hours", {}).get("open_now") else "❌ Закрыто"
            link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&query_place_id={item.get('place_id')}"
            
            res.append(f"🏛 **{name}**\n⭐ {rating}\n🕒 {is_open}\n📍 {addr}\n🔗 [В карты]({link})")
        return res
    except: return None

@dp.message(CommandStart())
async def start(m: types.Message):
    kb = [[types.KeyboardButton(text="📍 Найти места", request_location=True)]]
    await m.answer("Нажми кнопку, чтобы найти интересное рядом!", 
                   reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.location)
async def loc(m: types.Message):
    wait = await m.answer("🔍 Ищу лучшие места...")
    p = get_places(m.location.latitude, m.location.longitude)
    if not p:
        await wait.edit_text("Ничего не нашлось. Проверь API ключ Google!")
        return
    await wait.edit_text("🌟 **Интересное рядом:**\n\n" + "\n\n".join(p), parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    # Эта команда ОЧЕНЬ важна для устранения твоей ошибки Conflict
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
