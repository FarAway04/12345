import logging
import os
import json

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# 🔑 Token va admin ID
API_TOKEN = os.environ.get("API_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

MOVIES_FILE = "movies.json"

# 🔑 Fayl mavjud bo‘lmasa yaratish
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": [], "users": []}, f)

# 🔑 JSON yuklash/saqlash
def load_data():
    with open(MOVIES_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

# 🔑 Asosiy menyu
def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎬 Kino olish"))
    if is_admin:
        kb.add(
            KeyboardButton("➕ Kino qo'shish"),
            KeyboardButton("➖ Kino o'chirish"),
            KeyboardButton("✏️ Kino tahrirlash"),
            KeyboardButton("⭐ Kino reyting"),
            KeyboardButton("📊 Statistika"),
            KeyboardButton("📢 Majburiy Kanal")
        )
    return kb

# 🔑 Obuna tekshir
async def check_subs(user_id):
    data = load_data()
    for ch in data["channels"]:
        member = await bot.get_chat_member(ch["username"], user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return False
    return True

# 🔑 START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    data = load_data()
    if user_id not in data.get("users", []):
        data["users"].append(user_id)
        save_data(data)
    if not await check_subs(user_id):
        text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:"
        kb = InlineKeyboardMarkup()
        for ch in data["channels"]:
            kb.add(InlineKeyboardButton(ch["username"], url=f"https://t.me/{ch['username'].replace('@','')}"))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer(
            "Asosiy menyu:",
            reply_markup=main_menu(user_id == ADMIN_ID)
        )

@dp.callback_query_handler(lambda c: c.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await check_subs(call.from_user.id):
        await call.message.answer(
            "✅ Obuna tekshirildi!",
            reply_markup=main_menu(call.from_user.id == ADMIN_ID)
        )
    else:
        await call.message.answer("❌ Hali ham obuna bo‘lmadingiz.")

# 🔑 Kino olish
@dp.message_handler(lambda m: m.text == "🎬 Kino olish")
async def get_movie(message: types.Message):
    await message.answer("Kino kodini kiriting:")

@dp.message_handler(lambda m: m.text.isdigit())
async def send_movie(message: types.Message):
    code = int(message.text)
    data = load_data()
    for m in data["movies"]:
        if m["code"] == code:
            await message.answer_video(m["file_id"], caption=m["info"])
            return
    await message.answer("❌ Bunday kod topilmadi!")

# 🔑 FSM States
class AddMovieState(StatesGroup):
    waiting_for_file = State()
    waiting_for_info = State()

# 🔑 Kino qo‘shish (FSM)
@dp.message_handler(lambda m: m.text == "➕ Kino qo'shish")
async def add_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🎬 Kino faylini yubor.")
    await AddMovieState.waiting_for_file.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=AddMovieState.waiting_for_file)
async def save_file(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("📄 Kino haqida ma’lumot yubor.")
    await AddMovieState.waiting_for_info.set()

@dp.message_handler(state=AddMovieState.waiting_for_info)
async def save_info(message: types.Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    file_id = user_data['file_id']
    info = message.text
    code = len(data["movies"]) + 1
    data["movies"].append({
        "code": code,
        "file_id": file_id,
        "info": info,
        "rating": 0
    })
    save_data(data)
    await message.answer(f"✅ Kino qo‘shildi! Kodi: {code}")
    await state.finish()

# 🔑 Kino o‘chirish
@dp.message_handler(lambda m: m.text == "➖ Kino o'chirish")
async def delete_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("O‘chirish uchun kino kodini yuboring:")

@dp.message_handler(lambda m: m.text.isdigit() and m.from_user.id == ADMIN_ID)
async def delete_movie_by_code(message: types.Message):
    data = load_data()
    code = int(message.text)
    movies = data["movies"]
    data["movies"] = [m for m in movies if m["code"] != code]
    save_data(data)
    await message.answer(f"✅ Kino {code} o‘chirildi!")

# 🔑 Kino tahrirlash
class EditMovieState(StatesGroup):
    waiting_for_code = State()
    waiting_for_info = State()

@dp.message_handler(lambda m: m.text == "✏️ Kino tahrirlash")
async def edit_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Tahrirlanadigan kino kodini yuboring:")
    await EditMovieState.waiting_for_code.set()

@dp.message_handler(state=EditMovieState.waiting_for_code)
async def edit_movie_info(message: types.Message, state: FSMContext):
    await state.update_data(code=int(message.text))
    await message.answer("Yangi ma’lumotni yuboring:")
    await EditMovieState.waiting_for_info.set()

@dp.message_handler(state=EditMovieState.waiting_for_info)
async def save_edited_info(message: types.Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    code = user_data['code']
    for m in data["movies"]:
        if m["code"] == code:
            m["info"] = message.text
    save_data(data)
    await message.answer(f"✅ Kino {code} ma’lumoti yangilandi!")
    await state.finish()

# 🔑 Kino reyting
@dp.message_handler(lambda m: m.text == "⭐ Kino reyting")
async def movie_rating(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Qaysi kino reytingini ko‘rishni xohlaysiz? Kino kodini yuboring:")

@dp.message_handler(lambda m: m.text.isdigit() and m.from_user.id == ADMIN_ID)
async def show_rating(message: types.Message):
    data = load_data()
    code = int(message.text)
    for m in data["movies"]:
        if m["code"] == code:
            await message.answer(f"Kino {code} reytingi: {m['rating']}")
            return
    await message.answer("❌ Bunday kod topilmadi!")

# 🔑 Statistika
@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    text = f"👥 Userlar: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Top 10 kinolar", callback_data="top10"))
    kb.add(InlineKeyboardButton("Ortga", callback_data="back"))
    await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "top10")
async def top10(call: types.CallbackQuery):
    data = load_data()
    movies = sorted(data["movies"], key=lambda x: x.get("rating", 0), reverse=True)[:10]
    text = "🎬 Top 10 kinolar:\n"
    for m in movies:
        text += f"{m['code']}: {m['info']} (Reyting: {m['rating']})\n"
    await call.message.answer(text)

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(call: types.CallbackQuery):
    await call.message.answer("Asosiy menyu", reply_markup=main_menu(True))

# 🔑 Majburiy kanal boshqarish
@dp.message_handler(lambda m: m.text == "📢 Majburiy Kanal")
async def channel_manage(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    text = "Hozirgi kanallar:\n"
    for ch in data["channels"]:
        text += f"{ch['id']}: {ch['username']}\n"
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Qo‘shish", callback_data="add_ch"),
        InlineKeyboardButton("➖ O‘chirish", callback_data="del_ch"),
    )
    await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "add_ch")
async def add_ch(call: types.CallbackQuery):
    await call.message.answer("Kanal username’ini yuboring:")

@dp.message_handler(lambda m: m.reply_to_message and "Kanal username" in m.reply_to_message.text)
async def save_ch(message: types.Message):
    data = load_data()
    username = message.text.strip()
    new_id = 1 if not data["channels"] else max([c["id"] for c in data["channels"]]) + 1
    data["channels"].append({"id": new_id, "username": username})
    save_data(data)
    await message.answer(f"✅ Kanal qo‘shildi: {username}")

@dp.callback_query_handler(lambda c: c.data == "del_ch")
async def del_ch(call: types.CallbackQuery):
    await call.message.answer("O‘chirmoqchi bo‘lgan kanal username yoki ID sini yuboring:")

@dp.message_handler(lambda m: m.reply_to_message and "O‘chirmoqchi" in m.reply_to_message.text)
async def delete_ch(message: types.Message):
    data = load_data()
    val = message.text.strip()
    if val.isdigit():
        data["channels"] = [c for c in data["channels"] if c["id"] != int(val)]
    else:
        data["channels"] = [c for c in data["channels"] if c["username"] != val]
    save_data(data)
    await message.answer("✅ Kanal o‘chirildi!")

# ✅ Botni ishga tushirish
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
