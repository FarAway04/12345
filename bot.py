import logging
import json
import os

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# === TOKEN VA ADMIN ===
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === BOT & DP ===
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# === JSON FILE ===
MOVIES_FILE = "movies.json"
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": [], "users": [], "admins": [ADMIN_ID]}, f)

def load_data():
    with open(MOVIES_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

# === FSM ===
class KinoState(StatesGroup):
    waiting_for_file = State()
    waiting_for_text = State()
    waiting_for_confirm = State()
    waiting_for_delete_id = State()
    waiting_for_edit_id = State()
    waiting_for_new_text = State()

class AdminState(StatesGroup):
    waiting_for_new_admin = State()
    waiting_for_delete_admin = State()

# === MENU ===
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

# === START ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    data = load_data()
    user_id = message.from_user.id
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# === MENYU ===
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

# === KINO QO‘SHISH ===
@dp.message_handler(lambda m: m.text == "🎥 Kino qo‘shish")
async def kino_qoshish(message: types.Message):
    await message.answer("🎬 Kino faylini yuboring:")
    await KinoState.waiting_for_file.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=KinoState.waiting_for_file)
async def receive_kino_file(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("📝 Endi kino matnini yuboring:")
    await KinoState.waiting_for_text.set()

@dp.message_handler(state=KinoState.waiting_for_text)
async def receive_kino_text(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Ha"), KeyboardButton("❌ Yo‘q"))
    kb.add(KeyboardButton("🔙 Ortga"))
    await message.answer("Tasdiqlaysizmi?", reply_markup=kb)
    await KinoState.waiting_for_confirm.set()

@dp.message_handler(lambda m: m.text in ["✅ Ha", "❌ Yo‘q"], state=KinoState.waiting_for_confirm)
async def confirm_kino(message: types.Message, state: FSMContext):
    if message.text == "✅ Ha":
        data = load_data()
        kino_data = await state.get_data()
        kino_id = len(data["movies"]) + 1
        data["movies"].append({
            "id": kino_id,
            "file_id": kino_data["file_id"],
            "caption": kino_data["caption"]
        })
        save_data(data)
        await message.answer(f"✅ Kino yuklandi! Kino kodi: {kino_id}", reply_markup=kinolar_menu())
    else:
        await message.answer("❌ Kino yuklash rad etildi.", reply_markup=kinolar_menu())
    await state.finish()

# === KINO O‘CHIRISH ===
@dp.message_handler(lambda m: m.text == "🗑 Kino o‘chirish")
async def kino_ochirish(message: types.Message):
    await message.answer("🗑 O‘chiriladigan kino ID’sini yuboring:")
    await KinoState.waiting_for_delete_id.set()

@dp.message_handler(state=KinoState.waiting_for_delete_id)
async def confirm_delete_kino(message: types.Message, state: FSMContext):
    try:
        del_id = int(message.text)
        data = load_data()
        movies = data["movies"]
        updated = [m for m in movies if m["id"] != del_id]
        if len(updated) != len(movies):
            data["movies"] = updated
            save_data(data)
            await message.answer(f"✅ Kino o‘chirildi: {del_id}", reply_markup=kinolar_menu())
        else:
            await message.answer("❗ Bunday ID topilmadi.", reply_markup=kinolar_menu())
    except ValueError:
        await message.answer("❗ ID raqam bo‘lishi kerak.")
    await state.finish()

# === KINO TAHRIRLASH ===
@dp.message_handler(lambda m: m.text == "✏️ Kino tahrirlash")
async def kino_tahrirlash(message: types.Message):
    await message.answer("✏️ Tahrirlanadigan kino ID’sini yuboring:")
    await KinoState.waiting_for_edit_id.set()

@dp.message_handler(state=KinoState.waiting_for_edit_id)
async def get_edit_id(message: types.Message, state: FSMContext):
    try:
        edit_id = int(message.text)
        data = load_data()
        if any(m["id"] == edit_id for m in data["movies"]):
            await state.update_data(edit_id=edit_id)
            await message.answer("✏️ Yangi matnni yuboring:")
            await KinoState.waiting_for_new_text.set()
        else:
            await message.answer("❗ Bunday ID topilmadi.", reply_markup=kinolar_menu())
            await state.finish()
    except ValueError:
        await message.answer("❗ ID raqam bo‘lishi kerak.")
        await state.finish()

@dp.message_handler(state=KinoState.waiting_for_new_text)
async def save_new_text(message: types.Message, state: FSMContext):
    new_caption = message.text
    data = await state.get_data()
    all_data = load_data()
    for m in all_data["movies"]:
        if m["id"] == data["edit_id"]:
            m["caption"] = new_caption
    save_data(all_data)
    await message.answer(f"✅ Kino tahrirlandi: {data['edit_id']}", reply_markup=kinolar_menu())
    await state.finish()

# === ADMIN QO‘SHISH ===
@dp.message_handler(lambda m: m.text == "➕ Admin qo‘shish")
async def admin_qoshish(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Ruxsat yo‘q!")
        return
    await message.answer("Yangi adminning ID sini yuboring:")
    await AdminState.waiting_for_new_admin.set()

@dp.message_handler(state=AdminState.waiting_for_new_admin)
async def save_new_admin(message: types.Message, state: FSMContext):
    new_id = int(message.text)
    data = load_data()
    if new_id not in data["admins"]:
        data["admins"].append(new_id)
        save_data(data)
        await message.answer(f"✅ Admin qo‘shildi: {new_id}")
    else:
        await message.answer("❗ Bu ID allaqachon admin.")
    await state.finish()

# === ADMIN O‘CHIRISH ===
@dp.message_handler(lambda m: m.text == "➖ Admin o‘chirish")
async def admin_ochirish(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Ruxsat yo‘q!")
        return
    await message.answer("O‘chiriladigan adminning ID sini yuboring:")
    await AdminState.waiting_for_delete_admin.set()

@dp.message_handler(state=AdminState.waiting_for_delete_admin)
async def delete_admin(message: types.Message, state: FSMContext):
    del_id = int(message.text)
    data = load_data()
    if del_id in data["admins"]:
        data["admins"].remove(del_id)
        save_data(data)
        await message.answer(f"✅ Admin o‘chirildi: {del_id}")
    else:
        await message.answer("❗ Bu ID admin emas.")
    await state.finish()

# === START POLLING ===
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
