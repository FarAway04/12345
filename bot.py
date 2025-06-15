import os
import json
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNELS = os.getenv("CHANNELS", "").split(",")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

DATA_FILE = 'movies.json'

# JSON tayyorlash
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "movies": [],
            "channels": CHANNELS,
            "users": [],
            "admins": [ADMIN_ID]
        }, f)


def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


# --- FSM STATES ---
class AddMovie(StatesGroup):
    code = State()
    file = State()

class DeleteMovie(StatesGroup):
    code = State()

class AddAdmin(StatesGroup):
    id = State()

class DeleteAdmin(StatesGroup):
    id = State()

class AddChannel(StatesGroup):
    name = State()


# --- Keyboards ---
def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kinolar", "📢 Kanallar")
    kb.add("👤 Adminlar", "📊 Statistika")
    return kb

def kino_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Kino qo'shish", "🗑 Kino o'chirish")
    kb.add("🔙 Ortga")
    return kb

def adminlar_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Admin qo'shish", "➖ Admin o'chirish")
    kb.add("🔙 Ortga")
    return kb

def sub_keyboard():
    data = load_data()
    ikb = types.InlineKeyboardMarkup(row_width=1)
    for ch in data['channels']:
        ikb.add(types.InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
    ikb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return ikb

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


# --- START ---
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
            await message.answer("✅ Botga xush kelibsiz! Kino kodini yuboring!")
        else:
            await message.answer("❗ Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=sub_keyboard())


# --- SUBSCRIBE CHECK ---
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.answer("✅ Obuna tekshirildi! Endi kino kodini yuboring!")
    else:
        await call.message.answer("❗ Hali hamma kanallarga obuna bo‘lmadingiz.", reply_markup=sub_keyboard())


# --- USER MOVIE CODE ---
@dp.message_handler(lambda msg: msg.text not in ["🎬 Kinolar", "📢 Kanallar", "👤 Adminlar", "📊 Statistika",
                                                  "➕ Kino qo'shish", "🗑 Kino o'chirish",
                                                  "➕ Admin qo'shish", "➖ Admin o'chirish", "🔙 Ortga"],
                    state="*")
async def user_search_movie(message: types.Message):
    user_id = message.from_user.id
    if user_id in load_data()['admins']:
        return  # Adminlar uchun yo‘q
    if not await is_subscribed(user_id):
        await message.answer("❗ Avval kanallarga obuna bo'ling:", reply_markup=sub_keyboard())
        return

    data = load_data()
    code = message.text.strip()
    for m in data['movies']:
        if m['code'] == code:
            await bot.send_document(message.chat.id, m['file_id'],
                                    caption="🎬 Boshqa kodlar kanalimizda!")
            return
    await message.answer("❌ Bunday kod topilmadi.")


# --- ADMIN MENU ---
@dp.message_handler(lambda msg: msg.text == "🎬 Kinolar")
async def kinolar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        await message.answer("Kinolar bo‘limi:", reply_markup=kino_menu())

@dp.message_handler(lambda msg: msg.text == "📢 Kanallar")
async def kanallar(message: types.Message, state: FSMContext):
    if message.from_user.id in load_data()['admins']:
        data = load_data()
        if data['channels']:
            ch_list = "\n".join(data['channels'])
            await message.answer(f"📢 Kanallar:\n{ch_list}\n\nYangi kanal qo'shish uchun @name yuboring.")
        else:
            await message.answer("📢 Kanallar ro'yxati bo'sh. @name yuboring — qo'shamiz.")
        await AddChannel.name.set()

@dp.message_handler(lambda msg: msg.text == "👤 Adminlar")
async def adminlar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        await message.answer("Adminlar bo‘limi:", reply_markup=adminlar_menu())

@dp.message_handler(lambda msg: msg.text == "📊 Statistika")
async def statistika(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        data = load_data()
        await message.answer(
            f"👥 Foydalanuvchilar: {len(data['users'])}\n"
            f"🎬 Kinolar: {len(data['movies'])}\n"
            f"👑 Adminlar: {len(data['admins'])}"
        )

# --- ADD MOVIE FSM ---
@dp.message_handler(lambda msg: msg.text == "➕ Kino qo'shish")
async def add_movie_start(message: types.Message):
    await message.answer("Yangi kino kodi?")
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
    await message.answer(f"✅ Kino qo'shildi: {code}")
    await state.finish()

# --- DELETE MOVIE FSM ---
@dp.message_handler(lambda msg: msg.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: types.Message):
    await message.answer("O'chiriladigan kino kodini yuboring:")
    await DeleteMovie.code.set()

@dp.message_handler(state=DeleteMovie.code)
async def delete_movie_code(message: types.Message, state: FSMContext):
    data = load_data()
    code = message.text.strip()
    data['movies'] = [m for m in data['movies'] if m['code'] != code]
    save_data(data)
    await message.answer(f"✅ Kino o'chirildi: {code}")
    await state.finish()

# --- ADD ADMIN FSM ---
@dp.message_handler(lambda msg: msg.text == "➕ Admin qo'shish")
async def add_admin_start(message: types.Message):
    await message.answer("Yangi admin ID yuboring:")
    await AddAdmin.id.set()

@dp.message_handler(state=AddAdmin.id)
async def add_admin_id(message: types.Message, state: FSMContext):
    data = load_data()
    new_id = int(message.text.strip())
    if new_id not in data['admins']:
        data['admins'].append(new_id)
        save_data(data)
        await message.answer(f"✅ Admin qo'shildi: {new_id}")
    else:
        await message.answer("Bu ID allaqachon admin.")
    await state.finish()

# --- DELETE ADMIN FSM ---
@dp.message_handler(lambda msg: msg.text == "➖ Admin o'chirish")
async def delete_admin_start(message: types.Message):
    await message.answer("O'chiriladigan admin ID yuboring:")
    await DeleteAdmin.id.set()

@dp.message_handler(state=DeleteAdmin.id)
async def delete_admin_id(message: types.Message, state: FSMContext):
    data = load_data()
    del_id = int(message.text.strip())
    if del_id in data['admins']:
        data['admins'].remove(del_id)
        save_data(data)
        await message.answer(f"✅ Admin o'chirildi: {del_id}")
    else:
        await message.answer("Bu ID admin emas.")
    await state.finish()

# --- ADD CHANNEL FSM ---
@dp.message_handler(state=AddChannel.name)
async def add_channel_name(message: types.Message, state: FSMContext):
    data = load_data()
    ch = message.text.strip()
    if ch not in data['channels']:
        data['channels'].append(ch)
        save_data(data)
        await message.answer(f"✅ Kanal qo'shildi: {ch}")
    else:
        await message.answer("Bu kanal allaqachon mavjud.")
    await state.finish()

# --- BACK ---
@dp.message_handler(lambda msg: msg.text == "🔙 Ortga")
async def back_to_menu(message: types.Message):
    await message.answer("👑 Admin menyu:", reply_markup=admin_menu())


# --- RUN ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
