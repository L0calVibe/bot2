import os
import asyncio
import requests
import googlemaps
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
gmaps = googlemaps.Client(key=GOOGLE_KEY) if GOOGLE_KEY else None

class Form(StatesGroup):
    waiting_for_location = State()
    category_selection = State()

# Словарь соответствия категорий для Google и Overpass
CATEGORIES = {
    "culture": {"label": "🏛 Культура и история", "google": "tourist_attraction|museum", "osm": "museum|viewpoint|attraction|castle|historic"},
    "food": {"label": "🍴 Еда и досуг", "google": "restaurant|cafe|bar", "osm": "restaurant|cafe|bar|cinema|theatre"},
    "nature": {"label": "🌳 Парки и природа", "google": "park", "osm": "park|garden|zoo"}
}

def get_google_places(lat, lon, category_key):
    """Поиск через Google Places API"""
    if not gmaps: return None
    try:
        # Радиус 2000 метров
        res = gmaps.places_nearby(location=(lat, lon), radius=2000, 
                                  type=CATEGORIES[category_key]['google'].split('|')[0])
        places = []
        for p in res.get('results', [])[:5]:
            name = p.get('name')
            # Google дает больше инфо, можно вытащить рейтинг
            rating = p.get('rating', 'нет')
            vicinity = p.get('vicinity', '')
            p_lat, p_lon = p['geometry']['location']['lat'], p['geometry']['location']['lng']
            link = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
            
            # Попытка найти "историю" или описание через Google (упрощенно)
            desc = f"📍 {vicinity}\n⭐ Рейтинг: {rating}"
            places.append(f"**{name}**\n{desc}\n🔗 [Карта]({link})")
        return places
    except Exception as e:
        print(f"Google Error: {e}")
        return None

def get_osm_places(lat, lon, category_key):
    """Запасной поиск через Overpass (OSM)"""
    osm_type = CATEGORIES[category_key]['osm']
    query = f"""
    [out:json][timeout:25];
    (node["tourism"~"{osm_type}"](around:2000,{lat},{lon});
     node["amenity"~"{osm_type}"](around:2000,{lat},{lon});
     node["leisure"~"{osm_type}"](around:2000,{lat},{lon});
     node["historic"](around:2000,{lat},{lon}););
    out center 10;
    """
    try:
        response = requests.get("http://overpass-api.de/api/interpreter", params={'data': query}, timeout=15)
        data = response.json()
        places = []
        for el in data.get('elements', [])[:7]:
            tags = el.get('tags', {})
            name = tags.get('name', 'Без названия')
            p_lat = el.get('lat') or el.get('center', {}).get('lat')
            p_lon = el.get('lon') or el.get('center', {}).get('lon')
            link = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
            
            # Добавляем тип объекта как мини-описание
            obj_type = tags.get('historic', tags.get('tourism', tags.get('amenity', 'место')))
            places.append(f"**{name}**\nℹ️ Тип: {obj_type}\n🔗 [Карта]({link})")
        return places
    except:
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [[types.KeyboardButton(text="📍 Отправить локацию", request_location=True)]]
    await message.answer("Пришли локацию, и выбери, что именно мы будем искать в радиусе 2 км.", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.location)
async def handle_location(message: types.Message, state: FSMContext):
    # Сохраняем координаты в память бота
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    
    builder = InlineKeyboardBuilder()
    for key, val in CATEGORIES.items():
        builder.button(text=val['label'], callback_data=f"cat_{key}")
    builder.adjust(1)
    
    await message.answer("Отлично! Что именно ищем?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    cat_key = callback.data.split("_")[1]
    data = await state.get_data()
    lat, lon = data.get('lat'), data.get('lon')
    
    await callback.message.edit_text(f"🔍 Ищу {CATEGORIES[cat_key]['label']} в радиусе 2 км...")
    
    # 1. Пробуем Google
    places = get_google_places(lat, lon, cat_key)
    method = "Google Maps"
    
    # 2. Если Google не выдал ничего или ошибка — используем OSM
    if not places:
        places = get_osm_places(lat, lon, cat_key)
        method = "OpenStreetMap (бесплатно)"
        
    if not places:
        await callback.message.answer("К сожалению, в этом радиусе ничего не найдено.")
        return

    response_text = f"✨ **Результаты ({method}):**\n\n" + "\n\n".join(places)
    await callback.message.answer(response_text, parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
