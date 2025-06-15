import os
import json
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

# 🌟 ENVIRONMENT:
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNELS = os.getenv("CHANNELS").split(",")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

DATA_FILE = 'movies.json'

# JSON faylni tayyorlash
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "movies": [],
        }, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# FSM STATES
class AddMovie(StatesGroup):
    code = State()
    file = State()

class DeleteMovie(StatesGroup):
    code = State()

class EditMovie(StatesGroup):
    code = State()
    file = State()

class AddAdmin(StatesGroup):
    id = State()

class DeleteAdmin(StatesGroup):
    id = State()

class AddChannel(StatesGroup):
    name = State()

class DeleteChannel(StatesGroup):
    name = State()

class EditChannel(StatesGroup):
    old_name = State()
    new_name = State()

# Keyboardlar
def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kino qo'shish", "🗑 Kino o'chirish", "✏️ Kino tahrirlash")
    kb.add("➕ Admin qo'shish", "➖ Admin o'chirish")
    kb.add("➕ Kanal qo'shish", "➖ Kanal o'chirish", "✏️ Kanal tahrirlash")
    kb.add("📊 Statistika")
    return kb

def sub_keyboard():
    ikb = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        if ch.startswith("-100"):
            continue  # private kanalni url qilib bo‘lmaydi
        ikb.add(types.InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
    ikb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return ikb

async def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except:
            return False
    return True

# START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("👑 Admin menyu:", reply_markup=admin_menu())
    else:
        if await is_subscribed(user_id):
            await message.answer("✅ Xush kelibsiz! Kino kodini yuboring!")
        else:
            await message.answer("❗ Kanallarga obuna bo'ling:", reply_markup=sub_keyboard())

# SUBSCRIBE CHECK
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.answer("✅ Obuna tekshirildi! Endi kino kodini yuboring!")
    else:
        await call.message.answer("❗ Hali hamma kanallarga obuna bo‘lmadingiz.", reply_markup=sub_keyboard())

# Kino qidirish
@dp.message_handler(lambda msg: msg.text not in [
    "🎬 Kino qo'shish", "🗑 Kino o'chirish", "✏️ Kino tahrirlash",
    "➕ Admin qo'shish", "➖ Admin o'chirish",
    "➕ Kanal qo'shish", "➖ Kanal o'chirish", "✏️ Kanal tahrirlash",
    "📊 Statistika"
])
async def user_search_movie(message: types.Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        return
    if not await is_subscribed(user_id):
        await message.answer("❗ Avval kanallarga obuna bo'ling:", reply_markup=sub_keyboard())
        return

    data = load_data()
    code = message.text.strip()
    for m in data['movies']:
        if m['code'] == code:
            await bot.send_document(message.chat.id, m['file_id'])
            return
    await message.answer("❌ Bunday kod topilmadi.")

# Admin menyu
@dp.message_handler(lambda msg: msg.text == "🎬 Kino qo'shish")
async def add_movie_start(message: types.Message):
    await message.answer("Kino kodi?")
    await AddMovie.code.set()

@dp.message_handler(state=AddMovie.code)
async def add_movie_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("Kino faylini yuboring:")
    await AddMovie.file.set()

@dp.message_handler(content_types=['document'], state=AddMovie.file)
async def add_movie_file(message: types.Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    code = user_data['code']
    file_id = message.document.file_id
    data['movies'].append({"code": code, "file_id": file_id})
    save_data(data)
    await message.answer(f"✅ Qo'shildi: {code}")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: types.Message):
    await message.answer("O'chiriladigan kino kodi?")
    await DeleteMovie.code.set()

@dp.message_handler(state=DeleteMovie.code)
async def delete_movie_code(message: types.Message, state: FSMContext):
    data = load_data()
    code = message.text.strip()
    data['movies'] = [m for m in data['movies'] if m['code'] != code]
    save_data(data)
    await message.answer(f"✅ O'chirildi: {code}")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "✏️ Kino tahrirlash")
async def edit_movie_start(message: types.Message):
    await message.answer("Tahrirlanadigan kino kodi?")
    await EditMovie.code.set()

@dp.message_handler(state=EditMovie.code)
async def edit_movie_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("Yangi faylni yubor:")
    await EditMovie.file.set()

@dp.message_handler(content_types=['document'], state=EditMovie.file)
async def edit_movie_file(message: types.Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    code = user_data['code']
    for m in data['movies']:
        if m['code'] == code:
            m['file_id'] = message.document.file_id
    save_data(data)
    await message.answer(f"✅ Tahrirlandi: {code}")
    await state.finish()

# Admin qo'shish/o'chirish - faqat 1 admin
@dp.message_handler(lambda msg: msg.text == "➕ Admin qo'shish")
async def add_admin(message: types.Message):
    await message.answer("Yangi admin ID ni yoz, lekin hozir faqat 1 admin ruxsat!")

@dp.message_handler(lambda msg: msg.text == "➖ Admin o'chirish")
async def del_admin(message: types.Message):
    await message.answer("Asosiy adminni o'chirib bo‘lmaydi!")

# Kanal qo'shish/o'chirish/tahrirlash - ENV orqali boshqar!
@dp.message_handler(lambda msg: msg.text == "➕ Kanal qo'shish")
async def add_channel(message: types.Message):
    await message.answer("Render Environment'dan `CHANNELS` ni o'zgartir! Kod avtomatik foydalanadi.")

@dp.message_handler(lambda msg: msg.text == "➖ Kanal o'chirish")
async def del_channel(message: types.Message):
    await message.answer("Render Environment'dan `CHANNELS` ni o'zgartir!")

@dp.message_handler(lambda msg: msg.text == "✏️ Kanal tahrirlash")
async def edit_channel(message: types.Message):
    await message.answer("Render Environment'dan `CHANNELS` ni tahrir qil!")

# Statistika
@dp.message_handler(lambda msg: msg.text == "📊 Statistika")
async def stats(message: types.Message):
    data = load_data()
    await message.answer(f"🎬 Kinolar: {len(data['movies'])}\n👑 Admin: {ADMIN_ID}\nKanallar: {', '.join(CHANNELS)}")

# Run
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
