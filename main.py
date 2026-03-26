import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

# Ключи подтянутся из настроек Render
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_places_google(lat, lon):
    """Запрос к Google Places API для поиска лучших мест с рейтингом"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{lat},{lon}",
        "radius": 5000,
        "type": "tourist_attraction", 
        "key": GOOGLE_API_KEY,
        "language": "ru"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") != "OK":
            return None
        
        results = []
        # Берем 10 самых популярных мест
        for item in data.get("results", [])[:10]:
            name = item.get("name")
            rating = item.get("rating", "—")
            user_ratings = item.get("user_ratings_total", 0)
            address = item.get("vicinity", "Адрес не указан")
            
            # Проверка, открыто ли сейчас
            opening_hours = item.get("opening_hours", {})
            status = "✅ Открыто" if opening_hours.get("open_now") else "❌ Сейчас закрыто"
            
            place_id = item.get("place_id")
            # Ссылка на страницу места с отзывами и фото
            gmaps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&query_place_id={place_id}"
            
            results.append(
                f"🏛 **{name}**\n"
                f"⭐ Рейтинг: {rating} ({user_ratings} отз.)\n"
                f"🕒 {status}\n"
                f"📍 {address}\n"
                f"🔗 [Подробнее в Google Картах]({gmaps_link})"
            )
            
        return results
    except Exception as e:
        print(f"Ошибка Google API: {e}")
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [[types.KeyboardButton(text="📍 Найти интересное поблизости", request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Я помогу найти лучшие места вокруг тебя (музеи, парки, рестораны).\n\n"
        "Просто нажми кнопку ниже, чтобы отправить локацию.",
        reply_markup=keyboard
    )

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    wait_msg = await message.answer("📡 Обращаюсь к Google Maps, выбираю лучшее...")
    
    places = get_places_google(lat, lon)
    
    if not places:
        await wait_msg.edit_text("Google не нашел ничего подходящего в радиусе 5 км.")
        return

    response_text = "🌟 **Топ мест рядом с тобой:**\n\n" + "\n\n───────────────\n\n".join(places)
    await wait_msg.edit_text(response_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    # Эта строка решает проблему конфликта токена из твоих логов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
