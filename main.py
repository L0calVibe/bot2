import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def get_from_google(lat, lon):
    """Первый этап: Поиск через Google Places (с рейтингами)"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius": 5000,
        "key": GOOGLE_API_KEY,
        "language": "ru"
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("status") == "OK":
            places = []
            for item in res.get("results", [])[:5]: # Берем ТОП-5 от Google
                name = item.get("name")
                rating = item.get("rating", "—")
                place_id = item.get("place_id")
                link = f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
                places.append(f"🌟 **{name}**\n⭐ Рейтинг: {rating}\n🔗 [В Google Карты]({link})")
            return places
    except:
        return None
    return None

def get_from_osm(lat, lon):
    """Второй этап: Резервный поиск через OpenStreetMap (если Google молчит)"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (node["tourism"~"museum|viewpoint|attraction"](around:5000,{lat},{lon});
     node["amenity"~"restaurant|cafe"](around:5000,{lat},{lon}););
    out center 5;
    """
    try:
        res = requests.get(overpass_url, params={'data': query}, timeout=10).json()
        places = []
        for el in res.get('elements', []):
            name = el.get('tags', {}).get('name')
            if name:
                p_lat, p_lon = el.get('lat') or el.get('center', {}).get('lat'), el.get('lon') or el.get('center', {}).get('lon')
                link = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
                places.append(f"📍 **{name}** (OSM)\n🔗 [На карту]({link})")
        return places
    except:
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [[types.KeyboardButton(text="📍 Найти места", request_location=True)]]
    await message.answer("Привет! Я найду лучшее рядом, используя Google и OSM.", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.location)
async def handle_loc(message: types.Message):
    lat, lon = message.location.latitude, message.location.longitude
    msg = await message.answer("🔎 Собираю данные из всех систем...")
    
    # Сначала пробуем Google
    google_results = get_from_google(lat, lon)
    # Затем OSM для массовки
    osm_results = get_from_osm(lat, lon)
    
    all_results = (google_results or []) + (osm_results or [])
    
    if not all_results:
        await msg.edit_text("Ничего не найдено даже в резервной системе. 🤷‍♂️")
        return

    res_text = "✨ **Вот что удалось найти:**\n\n" + "\n\n".join(all_results[:10])
    await msg.edit_text(res_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    await bot.delete_webhook(drop_pending_updates=True) # Чиним Conflict
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
