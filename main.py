import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

# Берем только токен бота из Environment на Render
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_places_free(lat, lon):
    """Поиск через бесплатный Overpass API (OpenStreetMap)"""
    url = "http://overpass-api.de/api/interpreter"
    
    # Ищем: достопримечательности, парки, кафе и замки в радиусе 5 км
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"~"museum|viewpoint|attraction|castle"](around:5000,{lat},{lon});
      node["amenity"~"restaurant|cafe|cinema"](around:5000,{lat},{lon});
      node["leisure"~"park"](around:5000,{lat},{lon});
    );
    out center 15;
    """
    
    try:
        response = requests.get(url, params={'data': query}, timeout=20)
        if response.status_code != 200:
            return None
        
        data = response.json()
        places = []
        
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            name = tags.get('name')
            if not name: continue
            
            p_lat = element.get('lat') or element.get('center', {}).get('lat')
            p_lon = element.get('lon') or element.get('center', {}).get('lon')
            
            # Ссылка на Google Карты для навигации
            link = f"https://www.google.com/maps?q={p_lat},{p_lon}"
            places.append(f"📍 **{name}**\n🔗 [Открыть в картах]({link})")
            
        return places
    except:
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [[types.KeyboardButton(text="📍 Найти места поблизости", request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Привет! Отправь мне свою локацию, и я найду интересные места рядом (бесплатно и без ключей Google).", reply_markup=keyboard)

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    wait_msg = await message.answer("🔍 Ищу интересное рядом...")
    places = get_places_free(lat, lon)
    
    if not places:
        await wait_msg.edit_text("Ничего не нашлось. Попробуй нажать кнопку еще раз чуть позже.")
        return

    res_text = "✨ **Вот что есть в радиусе 5 км:**\n\n" + "\n\n".join(places[:10])
    await wait_msg.edit_text(res_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    # Эта строка УБИВАЕТ ошибку Conflict из твоих логов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
