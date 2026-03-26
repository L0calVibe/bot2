import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Загружаем переменные из .env (локально) или из настроек Render
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Радиус поиска в метрах
RADIUS = 5000 

def get_nearby_places(lat, lon):
    """Запрос к базе данных OpenStreetMap для поиска мест"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Мы ищем: музеи, памятники, рестораны, кинотеатры и парки
    overpass_query = f"""
    [out:json];
    (
      node["tourism"~"museum|viewpoint|attraction|monument"](around:{RADIUS},{lat},{lon});
      node["amenity"~"cinema|restaurant|arts_centre|theatre"](around:{RADIUS},{lat},{lon});
      node["leisure"~"park"](around:{RADIUS},{lat},{lon});
      way["tourism"~"museum|viewpoint|attraction|monument"](around:{RADIUS},{lat},{lon});
    );
    out center 15;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=15)
        if response.status_code != 200:
            return None
        
        data = response.json()
        places = []
        
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            name = tags.get('name')
            if not name: continue
            
            # Координаты места
            p_lat = element.get('lat') or element.get('center', {}).get('lat')
            p_lon = element.get('lon') or element.get('center', {}).get('lon')
            
            # Удобная ссылка для перехода в навигатор
            gmaps_link = f"https://www.google.com/maps?q={p_lat},{p_lon}"
            places.append(f"📍 **{name}**\n🔗 [Открыть в картах]({gmaps_link})")
        
        return places
    except Exception:
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Создаем кнопку запроса местоположения
    kb = [[types.KeyboardButton(text="📍 Найти интересное рядом", request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Я помогу найти интересные места поблизости (музеи, парки, рестораны).\n\n"
        "Просто нажми кнопку ниже, чтобы отправить свою локацию.",
        reply_markup=keyboard
    )

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    wait_msg = await message.answer("🔍 Ищу лучшие места в радиусе 5 км...")
    
    places = get_nearby_places(lat, lon)
    
    if not places:
        await wait_msg.edit_text("К сожалению, поблизости ничего не найдено. Попробуй позже!")
        return

    # Показываем первые 10 результатов
    response_text = "✨ **Вот что я нашел:**\n\n" + "\n\n".join(places[:10])
    await wait_msg.edit_text(response_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
