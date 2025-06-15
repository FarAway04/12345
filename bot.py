import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
import json
import os

API_TOKEN = os.environ.get("API_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

MOVIES_FILE = "movies.json"

if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": [], "users": []}, f)

# 📌 Asosiy menyu
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

# 📌 JSON
def load_data():
    with open(MOVIES_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

# 📌 Obuna tekshir
async def check_subs(user_id):
    data = load_data()
    for ch in data["channels"]:
        member = await bot.get_chat_member(ch["username"], user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return False
    return True

# 📌 START
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

# 📌 Kino olish
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

# 📌 Kino qo'shish (Admin)
@dp.message_handler(lambda m: m.text == "➕ Kino qo'shish")
async def add_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Kino faylini yuboring.")
    dp.register_message_handler(save_file, content_types=types.ContentType.VIDEO, state="save_file")

async def save_file(message: types.Message):
    data = load_data()
    data["temp_file"] = message.video.file_id
    save_data(data)
    await message.answer("Kino haqida ma’lumot yuboring.")
    dp.register_message_handler(save_info, state="save_info")

async def save_info(message: types.Message):
    data = load_data()
    file_id = data.pop("temp_file")
    info = message.text
    code = len(data["movies"]) + 1
    data["movies"].append({"code": code, "file_id": file_id, "info": info, "rating": 0})
    save_data(data)
    await message.answer(f"✅ Kino qo‘shildi! Kodi: {code}")

# 📌 Kino o'chirish (Admin)
@dp.message_handler(lambda m: m.text == "➖ Kino o'chirish")
async def delete_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("O‘chirish uchun kino kodini yuboring:")
    dp.register_message_handler(delete_movie_by_code)

async def delete_movie_by_code(message: types.Message):
    data = load_data()
    code = int(message.text)
    movies = data["movies"]
    data["movies"] = [m for m in movies if m["code"] != code]
    save_data(data)
    await message.answer(f"✅ Kino {code} o‘chirildi!")

# 📌 Kino tahrirlash (Admin)
@dp.message_handler(lambda m: m.text == "✏️ Kino tahrirlash")
async def edit_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Tahrirlanadigan kino kodini yuboring:")
    dp.register_message_handler(edit_movie_info)

async def edit_movie_info(message: types.Message):
    data = load_data()
    code = int(message.text)
    data["edit_code"] = code
    save_data(data)
    await message.answer("Yangi ma’lumotni yuboring:")
    dp.register_message_handler(save_edited_info)

async def save_edited_info(message: types.Message):
    data = load_data()
    code = data.pop("edit_code")
    for m in data["movies"]:
        if m["code"] == code:
            m["info"] = message.text
    save_data(data)
    await message.answer(f"✅ Kino {code} ma’lumoti yangilandi!")

# 📌 Kino reyting
@dp.message_handler(lambda m: m.text == "⭐ Kino reyting")
async def movie_rating(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Qaysi kino reytingini ko‘rishni xohlaysiz? Kino kodini yuboring:")
    dp.register_message_handler(show_rating)

async def show_rating(message: types.Message):
    data = load_data()
    code = int(message.text)
    for m in data["movies"]:
        if m["code"] == code:
            await message.answer(f"Kino {code} reytingi: {m['rating']}")
            return
    await message.answer("❌ Bunday kod topilmadi!")

# 📌 Statistika
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

# 📌 Majburiy kanal (Admin)
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
    dp.register_message_handler(save_ch)

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
    dp.register_message_handler(delete_ch)

async def delete_ch(message: types.Message):
    data = load_data()
    val = message.text.strip()
    if val.isdigit():
        data["channels"] = [c for c in data["channels"] if c["id"] != int(val)]
    else:
        data["channels"] = [c for c in data["channels"] if c["username"] != val]
    save_data(data)
    await message.answer("✅ Kanal o‘chirildi!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
