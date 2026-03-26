import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройки поиска (радиус в метрах)
RADIUS = 5000 

def get_nearby_places(lat, lon):
    """Запрос к Overpass API для поиска мест"""
    # Запрос ищет музеи, кинотеатры, достопримечательности и рестораны
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["tourism"~"museum|viewpoint|attraction"](around:{RADIUS},{lat},{lon});
      node["amenity"~"cinema|restaurant|arts_centre"](around:{RADIUS},{lat},{lon});
      way["tourism"~"museum|viewpoint|attraction"](around:{RADIUS},{lat},{lon});
    );
    out center 15;
    """
    
    response = requests.get(overpass_url, params={'data': overpass_query})
    if response.status_status != 200:
        return None
    
    data = response.json()
    places = []
    
    for element in data.get('elements', []):
        name = element.get('tags', {}).get('name', 'Интересное место')
        # Получаем координаты (у 'way' они в 'center')
        p_lat = element.get('lat') or element.get('center', {}).get('lat')
        p_lon = element.get('lon') or element.get('center', {}).get('lon')
        
        # Формируем ссылку на Google Maps для удобства
        gmaps_link = f"https://www.google.com/maps?q={p_lat},{p_lon}"
        places.append(f"📍 **{name}**\n🔗 [Открыть в картах]({gmaps_link})")
    
    return places

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Создаем кнопку для отправки геолокации
    kb = [
        [types.KeyboardButton(text="📍 Найти места рядом", request_location=True)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Отправь мне свою геолокацию, и я найду интересные места в радиусе 5 км.",
        reply_markup=keyboard
    )

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    wait_msg = await message.answer("🔍 Ищу самое интересное поблизости...")
    
    places = get_nearby_places(lat, lon)
    
    if not places:
        await wait_msg.edit_text("К сожалению, ничего не нашлось или сервис временно недоступен.")
        return

    # Разбиваем список, чтобы не превысить лимит сообщения в TG
    response_text = "✨ **Вот что есть поблизости:**\n\n" + "\n\n".join(places[:10])
    await wait_msg.edit_text(response_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())