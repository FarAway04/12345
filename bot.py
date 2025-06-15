import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json
import os

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

MOVIES_FILE = "movies.json"

# JSON ni tayyorlash
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": [], "users": [], "admins": [ADMIN_ID]}, f)

def load_data():
    with open(MOVIES_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

# Menyular
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎬 Kinolar"))
    kb.add(KeyboardButton("👤 Adminlar"))
    kb.add(KeyboardButton("📊 Statistika"))
    kb.add(KeyboardButton("📢 Kanallar"))
    return kb

def kinolar_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎥 Kino qo‘shish"))
    kb.add(KeyboardButton("🗑 Kino o‘chirish"))
    kb.add(KeyboardButton("✏️ Kino tahrirlash"))
    kb.add(KeyboardButton("🔙 Ortga"))
    return kb

def adminlar_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Admin qo‘shish"))
    kb.add(KeyboardButton("➖ Admin o‘chirish"))
    kb.add(KeyboardButton("🔙 Ortga"))
    return kb

# HOLATLAR
class AdminState(StatesGroup):
    waiting_for_new_admin = State()
    waiting_for_delete_admin = State()

# START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    data = load_data()
    user_id = message.from_user.id
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# Tugmalar
@dp.message_handler(lambda m: m.text == "🎬 Kinolar")
async def kinolar(message: types.Message):
    await message.answer("Kinolar bo‘limi:", reply_markup=kinolar_menu())

@dp.message_handler(lambda m: m.text == "👤 Adminlar")
async def adminlar(message: types.Message):
    await message.answer("Adminlar bo‘limi:", reply_markup=adminlar_menu())

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def statistika(message: types.Message):
    data = load_data()
    await message.answer(
        f"👥 Userlar: {len(data['users'])}\n"
        f"🎬 Kinolar: {len(data['movies'])}\n"
        f"👑 Adminlar: {len(data['admins'])}"
    )

@dp.message_handler(lambda m: m.text == "📢 Kanallar")
async def kanallar(message: types.Message):
    await message.answer("Kanallar bo‘limi hali tayyor emas.")

@dp.message_handler(lambda m: m.text == "🔙 Ortga")
async def ortga(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# ADMIN QO‘SHISH
@dp.message_handler(lambda m: m.text == "➕ Admin qo‘shish")
async def admin_qoshish(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Ruxsat yo‘q!")
        return
    await message.answer("Yangi adminning ID sini yuboring:")
    await AdminState.waiting_for_new_admin.set()

@dp.message_handler(state=AdminState.waiting_for_new_admin)
async def save_new_admin(message: types.Message, state: FSMContext):
    try:
        new_id = int(message.text)
        data = load_data()
        if new_id not in data["admins"]:
            data["admins"].append(new_id)
            save_data(data)
            await message.answer(f"✅ Admin qo‘shildi: {new_id}")
        else:
            await message.answer("❗ Bu ID allaqachon admin.")
    except ValueError:
        await message.answer("❗ Noto‘g‘ri ID. Raqam yuboring.")
    await state.finish()

# ADMIN O‘CHIRISH
@dp.message_handler(lambda m: m.text == "➖ Admin o‘chirish")
async def admin_ochirish(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Ruxsat yo‘q!")
        return
    await message.answer("O‘chiriladigan adminning ID sini yuboring:")
    await AdminState.waiting_for_delete_admin.set()

@dp.message_handler(state=AdminState.waiting_for_delete_admin)
async def delete_admin(message: types.Message, state: FSMContext):
    try:
        del_id = int(message.text)
        data = load_data()
        if del_id in data["admins"]:
            data["admins"].remove(del_id)
            save_data(data)
            await message.answer(f"✅ Admin o‘chirildi: {del_id}")
        else:
            await message.answer("❗ Bu ID admin emas.")
    except ValueError:
        await message.answer("❗ Noto‘g‘ri ID. Raqam yuboring.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
