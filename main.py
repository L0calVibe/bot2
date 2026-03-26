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

def get_places_categorized(lat, lon):
    url = "http://overpass-api.de/api/interpreter"
    
    # Запрос ищет разные типы объектов
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"~"museum|viewpoint|attraction|gallery|castle"](around:5000,{lat},{lon});
      node["amenity"~"restaurant|cafe|cinema|theatre|arts_centre"](around:5000,{lat},{lon});
      node["leisure"~"park|garden|zoo"](around:5000,{lat},{lon});
      node["historic"](around:5000,{lat},{lon});
    );
    out center 20;
    """
    
    try:
        response = requests.get(url, params={'data': query}, timeout=20)
        if response.status_code != 200: return None
        
        data = response.json()
        # Словари для распределения по категориям
        categories = {
            "🏛 Культура и история": [],
            "🌳 Парки и отдых": [],
            "🍴 Еда и досуг": []
        }
        
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            name = tags.get('name')
            if not name: continue
            
            p_lat = element.get('lat') or element.get('center', {}).get('lat')
            p_lon = element.get('lon') or element.get('center', {}).get('lon')
            link = f"https://www.google.com/maps?q={p_lat},{p_lon}"
            
            place_info = f"• **{name}**\n  └ [Открыть карту]({link})"

            # Логика распределения по категориям
            if any(k in tags for k in ["tourism", "historic"]):
                categories["🏛 Культура и история"].append(place_info)
            elif any(k in tags for k in ["leisure"]):
                categories["🌳 Парки и отдых"].append(place_info)
            elif any(k in tags for k in ["amenity"]):
                categories["🍴 Еда и досуг"].append(place_info)

        # Формируем итоговый текст
        final_text = ""
        for cat_name, items in categories.items():
            if items:
                final_text += f"{cat_name}\n" + "\n".join(items[:5]) + "\n\n"
        
        return final_text if final_text else "Ничего не найдено рядом."
    except:
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [[types.KeyboardButton(text="📍 Найти интересное рядом", request_location=True)]]
    await message.answer("Привет! Нажми кнопку, и я разложу интересные места рядом по полочкам.", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.location)
async def handle_location(message: types.Message):
    wait_msg = await message.answer("🔍 Анализирую карту города...")
    
    result = get_places_categorized(message.location.latitude, message.location.longitude)
    
    if not result:
        await wait_msg.edit_text("Не удалось получить данные. Попробуй еще раз.")
        return

    await wait_msg.edit_text(f"🌟 **Что есть поблизости:**\n\n{result}", 
                             parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
