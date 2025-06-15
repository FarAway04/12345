import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import os

# 📌 TOKEN va ADMIN_ID ni Render environment variables dan oladi:
API_TOKEN = os.environ.get("API_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# 🔑 Majburiy kanal (istasa)
CHANNELS = ["@MyKinoTv_Channel"]

# 🔑 Log sozlash
logging.basicConfig(level=logging.INFO)

# 🔑 Bot va dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 🔑 JSON fayl nomi
MOVIES_FILE = "movies.json"

# 🔑 Agar JSON yo'q bo'lsa, yarat
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": CHANNELS, "users": []}, f)

# 🔑 Tugmalar
def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎬 Kino olish"))
    if is_admin:
        kb.add(KeyboardButton("➕ Kino qo'shish"))
        kb.add(KeyboardButton("📊 Statistika"))
    return kb

# 🔑 Majburiy obuna tekshirish
async def check_subs(user_id):
    data = load_data()
    for ch in data["channels"]:
        member = await bot.get_chat_member(ch, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return False
    return True

# 🔑 JSON yuklash
def load_data():
    with open(MOVIES_FILE, "r") as f:
        return json.load(f)

# 🔑 JSON saqlash
def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

# 🔑 START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    data = load_data()
    if user_id not in data.get("users", []):
        data["users"].append(user_id)
        save_data(data)
    if not await check_subs(user_id):
        text = "Botdan foydalanish uchun kanallarga obuna bo‘ling:"
        kb = InlineKeyboardMarkup()
        for ch in data["channels"]:
            kb.add(InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        await message.answer(text, reply_markup=kb)
    else:
        is_admin = user_id == ADMIN_ID
        await message.answer("Asosiy menyu:", reply_markup=main_menu(is_admin))

# 🔑 Tekshirish tugmasi
@dp.callback_query_handler(lambda c: c.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await check_subs(call.from_user.id):
        is_admin = call.from_user.id == ADMIN_ID
        await call.message.answer("✅ Obuna tekshirildi!", reply_markup=main_menu(is_admin))
    else:
        await call.message.answer("❌ Hali ham obuna bo‘lmadingiz.")

# 🔑 Kino qo‘shish
@dp.message_handler(lambda m: m.text == "➕ Kino qo'shish")
async def add_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🎬 Kino faylini yuboring.")
    dp.register_message_handler(save_file, content_types=types.ContentType.VIDEO, state="save_file")

async def save_file(message: types.Message):
    data = load_data()
    data["temp_file"] = message.video.file_id
    save_data(data)
    await message.answer("📄 Kino ma’lumotini yuboring.")
    dp.register_message_handler(save_info, state="save_info")

async def save_info(message: types.Message):
    data = load_data()
    file_id = data.pop("temp_file")
    info = message.text
    movies = data["movies"]
    code = len(movies) + 1
    movies.append({"code": code, "file_id": file_id, "info": info})
    save_data(data)
    await message.answer(f"✅ Kino qo'shildi! Kodi: {code}")

# 🔑 Kino olish
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
    await message.answer("❌ Bunday kod topilmadi!")

# 🔑 Statistika
@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    await message.answer(f"👥 Userlar: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}")

# 🔑 Botni ishga tushirish
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
