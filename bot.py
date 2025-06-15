import json
import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = 'TOKEN'  # <<< Shu yerga tokeningni yoz!
ADMIN_ID = 123456789  # <<< Shu yerga o'zingning Telegram ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

DATA_FILE = 'movies.json'

# Agar fayl yo'q bo'lsa - yaratish
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({"movies": [], "channels": [], "users": [], "admins": [ADMIN_ID]}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Admin menyu
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kinolar", "📢 Kanallar")
    kb.add("📊 Statistika")
    return kb

# Kino menyu
def kino_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Kino qo'shish")
    kb.add("🔙 Ortga")
    return kb

# Kanallar klaviaturasi
def sub_keyboard():
    data = load_data()
    ikb = InlineKeyboardMarkup(row_width=1)
    for ch in data['channels']:
        ikb.add(InlineKeyboardButton(f"{ch}", url=f"https://t.me/{ch.replace('@','')}"))
    ikb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return ikb

# Majburiy obunani tekshirish
async def is_subscribed(user_id):
    data = load_data()
    for ch in data['channels']:
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
    data = load_data()
    user_id = message.from_user.id
    if user_id not in data['users']:
        data['users'].append(user_id)
        save_data(data)

    if user_id in data['admins']:
        await message.answer("👑 Admin menyu:", reply_markup=admin_menu())
    else:
        if await is_subscribed(user_id):
            await message.answer("✅ Botga xush kelibsiz! Kino kodini yuboring:")
        else:
            await message.answer("Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=sub_keyboard())

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.answer("✅ Obuna tekshirildi! Endi kino kodini yuboring!")
    else:
        await call.message.answer("❗ Hali hamma kanallarga obuna bo‘lmadingiz.", reply_markup=sub_keyboard())

# States kino qo'shish uchun
class AddMovie(StatesGroup):
    waiting_for_code = State()
    waiting_for_file = State()

# Kinolar bo‘limi
@dp.message_handler(lambda msg: msg.text == "🎬 Kinolar")
async def kinolar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        await message.answer("Kinolar bo‘limi:", reply_markup=kino_menu())

# Kino qo‘shish
@dp.message_handler(lambda msg: msg.text == "➕ Kino qo'shish")
async def add_movie_step1(message: types.Message):
    await message.answer("Yangi kino kodi:")
    await AddMovie.waiting_for_code.set()

@dp.message_handler(state=AddMovie.waiting_for_code)
async def add_movie_step2(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("Endi kino faylni yuboring (video):")
    await AddMovie.waiting_for_file.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=AddMovie.waiting_for_file)
async def add_movie_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    code = data['code']
    file_id = message.video.file_id
    db = load_data()
    db['movies'].append({"code": code, "file_id": file_id})
    save_data(db)
    await message.answer(f"✅ Kino saqlandi: {code}")
    await state.finish()

# Ortga
@dp.message_handler(lambda msg: msg.text == "🔙 Ortga")
async def back_to_menu(message: types.Message):
    await message.answer("👑 Admin menyu:", reply_markup=admin_menu())

# Kanallar bo‘limi
@dp.message_handler(lambda msg: msg.text == "📢 Kanallar")
async def kanallar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        data = load_data()
        if data['channels']:
            ch_list = "\n".join(data['channels'])
            await message.answer(f"📢 Kanallar:\n{ch_list}\n\nYangi kanal qo'shish uchun @name yuboring.")
        else:
            await message.answer("📢 Kanallar ro'yxati bo'sh. @name yuboring — qo'shamiz.")
        dp.register_message_handler(add_channel, state="*")

async def add_channel(message: types.Message):
    data = load_data()
    ch = message.text.strip()
    if ch not in data['channels']:
        data['channels'].append(ch)
        save_data(data)
        await message.answer(f"✅ Kanal qo'shildi: {ch}")
    else:
        await message.answer("Bu kanal allaqachon mavjud.")

# Statistika
@dp.message_handler(lambda msg: msg.text == "📊 Statistika")
async def statistika(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        data = load_data()
        await message.answer(f"👥 Foydalanuvchilar: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}\n👑 Adminlar: {len(data['admins'])}")

# Kino kodi qidirish (user uchun)
@dp.message_handler()
async def user_search_movie(message: types.Message):
    user_id = message.from_user.id
    if user_id in load_data()['admins']:
        return
    if not await is_subscribed(user_id):
        await message.answer("Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=sub_keyboard())
        return

    code = message.text.strip()
    db = load_data()
    for m in db['movies']:
        if m['code'] == code:
            await message.answer("🎬 Kodingiz bo‘yicha kino:")
            await message.answer_video(m['file_id'])
            return
    await message.answer("❌ Bunday kod topilmadi.")

# Botni ishga tushurish
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
