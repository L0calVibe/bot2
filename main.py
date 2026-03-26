import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Загружаем ключи из переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_places_google(lat, lon):
    """Запрос к Google Places API для поиска лучших мест поблизости"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{lat},{lon}",
        "radius": 5000,
        # Ищем достопримечательности, чтобы выбор был интересным
        "type": "tourist_attraction", 
        "key": GOOGLE_API_KEY,
        "language": "ru"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") != "OK":
            # Если по достопримечательностям пусто, попробуем поискать заведения
            params["type"] = "restaurant"
            response = requests.get(url, params=params)
            data = response.json()
            if data.get("status") != "OK":
                return None
        
        results = []
        # Берем до 10 самых качественных мест
        for item in data.get("results", [])[:10]:
            name = item.get("name")
            rating = item.get("rating", "—")
            user_ratings = item.get("user_ratings_total", 0)
            address = item.get("vicinity", "Адрес не указан")
            
            # Проверяем статус работы
            opening_hours = item.get("opening_hours", {})
            is_open = "✅ Открыто" if opening_hours.get("open_now") else "❌ Сейчас закрыто"
            
            # Формируем прямую ссылку на объект в Google
            place_id = item.get("place_id")
            gmaps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&query_place_id={place_id}"
            
            # Красивое оформление карточки места
            card = (
                f"🏛 **{name}**\n"
                f"⭐ Рейтинг: {rating} ({user_ratings} отз.)\n"
                f"🕒 {is_open}\n"
                f"📍 {address}\n"
                f"🔗 [Посмотреть фото и отзывы]({gmaps_link})"
            )
            results.append(card)
            
        return results
    except Exception as e:
        print(f"Ошибка Google API: {e}")
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Кнопка с запросом локации
    kb = [[types.KeyboardButton(text="📍 Найти интересное поблизости", request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Я помогу тебе найти лучшие места для прогулки и отдыха.\n\n"
        "Нажми кнопку ниже, чтобы отправить свою локацию и получить список топовых мест от Google Maps.",
        reply_markup=keyboard
    )

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Сообщение-статус, чтобы пользователь видел работу бота
    wait_msg = await message.answer("📡 Подключаюсь к Google Maps, выбираю лучшее...")
    
    places = get_places_google(lat, lon)
    
    if not places:
        await wait_msg.edit_text("К сожалению, Google не нашел ничего подходящего в радиусе 5 км. Попробуй позже!")
        return

    # Собираем все места в один текст с разделителями
    final_text = "🌟 **Топ мест рядом с тобой:**\n\n" + "\n\n───────────────\n\n".join(places)
    
    await wait_msg.edit_text(final_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
