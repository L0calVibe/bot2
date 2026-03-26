import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройки поиска
RADIUS = 5000  # Радиус в метрах (5 км)

def get_nearby_places(lat, lon):
    """Функция запроса к картам OpenStreetMap (Overpass API)"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Запрос ищет: достопримечательности, музеи, рестораны, парки и исторические места
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["tourism"~"museum|viewpoint|attraction|monument"](around:{RADIUS},{lat},{lon});
      node["amenity"~"cinema|restaurant|cafe|arts_centre"](around:{RADIUS},{lat},{lon});
      node["leisure"~"park|garden"](around:{RADIUS},{lat},{lon});
      node["historic"](around:{RADIUS},{lat},{lon});
      way["tourism"~"museum|viewpoint|attraction"](around:{RADIUS},{lat},{lon});
    );
    out center 15;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=20)
        
        # Проверка: если сервер ответил успешно (код 200)
        if response.status_code == 200:
            data = response.json()
            places = []
            
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                name = tags.get('name')
                
                # Если у места есть название, добавляем его в список
                if name:
                    p_lat = element.get('lat') or element.get('center', {}).get('lat')
                    p_lon = element.get('lon') or element.get('center', {}).get('lon')
                    
                    # Создаем прямую ссылку на Google Maps
                    gmaps_link = f"https://www.google.com/maps?q={p_lat},{p_lon}"
                    places.append(f"📍 **{name}**\n🔗 [Открыть в Google Картах]({gmaps_link})")
            
            return places
        else:
            return None
    except Exception as e:
        print(f"Ошибка при запросе к картам: {e}")
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Кнопка для запроса локации
    kb = [[types.KeyboardButton(text="📍 Найти интересные места", request_location=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Нажми на кнопку ниже, и я покажу, что интересного есть в радиусе 5 км от тебя.",
        reply_markup=keyboard
    )

@dp.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    
    msg = await message.answer("🔍 Ищу интересные локации поблизости...")
    
    # Запускаем поиск
    places = get_nearby_places(lat, lon)
    
    if not places:
        await msg.edit_text("Ничего не нашлось. Попробуй нажать кнопку еще раз или сменить местоположение.")
        return

    # Формируем ответ (берем первые 10 мест)
    result_text = "✨ **Вот что я нашел рядом с тобой:**\n\n" + "\n\n".join(places[:10])
    await msg.edit_text(result_text, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
