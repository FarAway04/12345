import logging
import json
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = "BOT_TOKENINGNI_BU_YERGA_QO'Y"
ADMIN_ID = 5088940828
CHANNELS = ["@MyKinoTv_Channel"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

MOVIES_FILE = "movies.json"
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": CHANNELS, "users": []}, f)


def load_data():
    with open(MOVIES_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)


# === FSM ===
class AddMovie(StatesGroup):
    waiting_for_video = State()
    waiting_for_info = State()

class ManageChannel(StatesGroup):
    add_channel = State()
    del_channel = State()

# === Menyu ===
def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎬 Kino olish"))
    if is_admin:
        kb.add(KeyboardButton("➕ Kino qo'shish"))
        kb.add(KeyboardButton("📊 Statistika"))
        kb.add(KeyboardButton("📣 Majburiy obuna"))
    return kb

async def check_subscriptions(user_id):
    for ch in load_data()["channels"]:
        member = await bot.get_chat_member(ch, user_id)
        if member.status not in ["member", "creator", "administrator"]:
            return False
    return True

# === START ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    data = load_data()
    if user_id not in data.get("users", []):
        data["users"].append(user_id)
        save_data(data)

    if not await check_subscriptions(user_id):
        text = "👋 Salom!\n\nBotdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:"
        btn = InlineKeyboardMarkup(row_width=1)
        for ch in data["channels"]:
            btn.add(InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
        btn.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs"))
        await message.answer(text, reply_markup=btn)
    else:
        is_admin = user_id == ADMIN_ID
        await message.answer("Asosiy menyu:", reply_markup=main_menu(is_admin))


@dp.callback_query_handler(lambda c: c.data == "check_subs")
async def check_subs(call: types.CallbackQuery):
    if await check_subscriptions(call.from_user.id):
        is_admin = call.from_user.id == ADMIN_ID
        await call.message.answer("✅ Obuna tekshirildi!", reply_markup=main_menu(is_admin))
    else:
        await call.message.answer("❌ Hali ham barcha kanallarga obuna bo‘lmadingiz!")

# === Kino qo'shish ===
@dp.message_handler(lambda m: m.text == "➕ Kino qo'shish")
async def add_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🎬 Kino faylini yuboring.")
    await AddMovie.waiting_for_video.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=AddMovie.waiting_for_video)
async def get_movie_file(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("📄 Endi kino ma'lumotlarini yuboring.")
    await AddMovie.waiting_for_info.set()

@dp.message_handler(state=AddMovie.waiting_for_info)
async def get_movie_info(message: types.Message, state: FSMContext):
    data = load_data()
    state_data = await state.get_data()
    file_id = state_data['file_id']
    info = message.text
    code = len(data["movies"]) + 1
    data["movies"].append({"code": code, "file_id": file_id, "info": info})
    save_data(data)
    await message.answer(f"✅ Kino qo'shildi! Kodi: {code}")
    await state.finish()

# === Kino olish ===
@dp.message_handler(lambda m: m.text == "🎬 Kino olish")
async def get_movie(message: types.Message):
    await message.answer("🎥 Kino kodini kiriting:")

@dp.message_handler(lambda m: m.text.isdigit())
async def send_movie(message: types.Message):
    code = int(message.text)
    data = load_data()
    for m in data["movies"]:
        if m["code"] == code:
            await message.answer_video(m["file_id"], caption=m["info"])
            return
    await message.answer("❌ Bunday kodli kino topilmadi!")

# === Statistika ===
@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    await message.answer(f"👥 Userlar: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}")

# === Majburiy obuna boshqarish ===
@dp.message_handler(lambda m: m.text == "📣 Majburiy obuna")
async def manage_subs(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Kanal qo'shish"), KeyboardButton("➖ Kanal o'chirish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    await message.answer("Majburiy obunani boshqarish:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "➕ Kanal qo'shish")
async def add_channel(message: types.Message):
    await message.answer("📣 Kanal usernameni yuboring: @namuna")
    await ManageChannel.add_channel.set()

@dp.message_handler(state=ManageChannel.add_channel)
async def save_channel(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    data = load_data()
    if ch not in data["channels"]:
        data["channels"].append(ch)
        save_data(data)
        await message.answer("✅ Kanal qo‘shildi!")
    else:
        await message.answer("❗ Bu kanal avvaldan bor.")
    await state.finish()

@dp.message_handler(lambda m: m.text == "➖ Kanal o'chirish")
async def remove_channel(message: types.Message):
    await message.answer("❌ O‘chirish uchun kanal usernameni yuboring: @namuna")
    await ManageChannel.del_channel.set()

@dp.message_handler(state=ManageChannel.del_channel)
async def delete_channel(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    data = load_data()
    if ch in data["channels"]:
        data["channels"].remove(ch)
        save_data(data)
        await message.answer("✅ Kanal o‘chirildi.")
    else:
        await message.answer("❗ Bu kanal topilmadi.")
    await state.finish()

@dp.message_handler(lambda m: m.text == "⬅️ Orqaga")
async def back(message: types.Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer("Asosiy menyu:", reply_markup=main_menu(is_admin))

# === Run ===
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
