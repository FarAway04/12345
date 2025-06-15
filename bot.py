import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

MOVIES_FILE = "movies.json"

# Agar fayl yo'q bo'lsa, yaratib qo'yadi
if not os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "w") as f:
        json.dump({"movies": [], "channels": [], "users": [], "admins": [ADMIN_ID]}, f)

def load_data():
    with open(MOVIES_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Asosiy menyu
def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if is_admin:
        kb.add(KeyboardButton("🎬 Kinolar"))
        kb.add(KeyboardButton("👤 Adminlar"))
        kb.add(KeyboardButton("📊 Statistika"))
        kb.add(KeyboardButton("📢 Kanallar"))
    return kb

# Majburiy obuna klaviaturasi
def check_subscribe_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    data = load_data()
    for ch in data["channels"]:
        kb.add(InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return kb

# START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    data = load_data()
    user_id = message.from_user.id
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    if user_id in data["admins"]:
        await message.answer("👑 Admin menyu:", reply_markup=main_menu(is_admin=True))
    else:
        await check_subscription(message)

async def check_subscription(message):
    data = load_data()
    if not data["channels"]:
        await message.answer("Kanallar sozlanmagan. Adminga murojaat qiling.")
        return

    text = "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:"
    await message.answer(text, reply_markup=check_subscribe_keyboard())

# Tekshirish tugmasi
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub(call: types.CallbackQuery):
    data = load_data()
    for ch in data["channels"]:
        member = await bot.get_chat_member(chat_id=ch, user_id=call.from_user.id)
        if member.status not in ["member", "creator", "administrator"]:
            await call.message.answer("❗ Hali hamma kanallarga obuna bo‘lmadingiz.\nObuna bo‘ling va yana tekshirib ko‘ring.", reply_markup=check_subscribe_keyboard())
            return
    await call.message.answer("✅ Obuna bo‘ldingiz! Endi kino kodini yuboring!")

# Kinoni qidirish
@dp.message_handler(lambda m: m.text not in ["🎬 Kinolar","👤 Adminlar","📊 Statistika","📢 Kanallar",
                                              "🎥 Kino qo‘shish","🗑 Kino o‘chirish","✏️ Kino tahrirlash",
                                              "➕ Admin qo‘shish","➖ Admin o‘chirish","🔙 Ortga"])
async def search_movie(message: types.Message):
    data = load_data()
    if message.from_user.id in data["admins"]:
        return  # Admin qidirish qismidan o'tmaydi

    # Majburiy obuna tekshirish
    for ch in data["channels"]:
        member = await bot.get_chat_member(chat_id=ch, user_id=message.from_user.id)
        if member.status not in ["member", "creator", "administrator"]:
            await check_subscription(message)
            return

    code = message.text.strip()
    for m in data["movies"]:
        if m["code"] == code:
            await message.answer(f"🎬 Kino topildi!\nLink: {m['link']}\n\nBoshqa kodlar kanalimizda joylangan!")
            return
    await message.answer("❌ Bunday kod topilmadi!")

# ADMIN QISMI
@dp.message_handler(lambda m: m.text == "🎬 Kinolar")
async def kinolar(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("🎥 Kino qo‘shish"))
        kb.add(KeyboardButton("🗑 Kino o‘chirish"))
        kb.add(KeyboardButton("✏️ Kino tahrirlash"))
        kb.add(KeyboardButton("🔙 Ortga"))
        await message.answer("Kinolar bo‘limi:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "👤 Adminlar")
async def adminlar(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("➕ Admin qo‘shish"))
        kb.add(KeyboardButton("➖ Admin o‘chirish"))
        kb.add(KeyboardButton("🔙 Ortga"))
        await message.answer("Adminlar bo‘limi:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def statistika(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        data = load_data()
        await message.answer(f"👥 Userlar: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}\n👑 Adminlar: {len(data['admins'])}")

@dp.message_handler(lambda m: m.text == "📢 Kanallar")
async def kanallar(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        data = load_data()
        if data["channels"]:
            text = "\n".join(data["channels"])
            await message.answer(f"📢 Kanallar:\n{text}\n\nYangi kanal qo‘shish uchun @name yuboring.")
        else:
            await message.answer("📢 Hozircha kanal yo‘q. @name yuboring — qo‘shib qo‘yamiz.")
        dp.register_message_handler(add_channel, state="*")

async def add_channel(message: types.Message):
    data = load_data()
    ch = message.text.strip()
    if ch not in data["channels"]:
        data["channels"].append(ch)
        save_data(data)
        await message.answer(f"✅ Kanal qo‘shildi: {ch}")
    else:
        await message.answer("❗ Bu kanal allaqachon mavjud.")

@dp.message_handler(lambda m: m.text == "🎥 Kino qo‘shish")
async def add_movie(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        await message.answer("Yangi kino kodini yuboring:")
        dp.register_message_handler(save_movie_code, state="*")

async def save_movie_code(message: types.Message):
    dp.register_message_handler(save_movie_link, state="*")
    message.bot['new_code'] = message.text.strip()
    await message.answer("Kino linkini yuboring:")

async def save_movie_link(message: types.Message):
    data = load_data()
    new_movie = {"code": message.bot['new_code'], "link": message.text.strip()}
    data["movies"].append(new_movie)
    save_data(data)
    await message.answer("✅ Kino qo‘shildi!")

@dp.message_handler(lambda m: m.text == "🗑 Kino o‘chirish")
async def delete_movie(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        await message.answer("O‘chiriladigan kino kodini yuboring:")
        dp.register_message_handler(do_delete_movie, state="*")

async def do_delete_movie(message: types.Message):
    data = load_data()
    code = message.text.strip()
    new_list = [m for m in data["movies"] if m["code"] != code]
    if len(new_list) != len(data["movies"]):
        data["movies"] = new_list
        save_data(data)
        await message.answer(f"✅ Kino o‘chirildi: {code}")
    else:
        await message.answer("❌ Bunday kod topilmadi.")

@dp.message_handler(lambda m: m.text == "✏️ Kino tahrirlash")
async def edit_movie(message: types.Message):
    if message.from_user.id in load_data()["admins"]:
        await message.answer("Tahrirlanadigan kino kodini yuboring:")
        dp.register_message_handler(do_edit_movie, state="*")

async def do_edit_movie(message: types.Message):
    dp.register_message_handler(do_edit_movie_link, state="*")
    message.bot['edit_code'] = message.text.strip()
    await message.answer("Yangi linkni yuboring:")

async def do_edit_movie_link(message: types.Message):
    data = load_data()
    found = False
    for m in data["movies"]:
        if m["code"] == message.bot['edit_code']:
            m["link"] = message.text.strip()
            found = True
            break
    if found:
        save_data(data)
        await message.answer("✅ Kino yangilandi!")
    else:
        await message.answer("❌ Bunday kod topilmadi!")

@dp.message_handler(lambda m: m.text == "➕ Admin qo‘shish")
async def add_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Yangi admin ID sini yuboring:")
        dp.register_message_handler(save_admin, state="*")

async def save_admin(message: types.Message):
    data = load_data()
    new_id = int(message.text.strip())
    if new_id not in data["admins"]:
        data["admins"].append(new_id)
        save_data(data)
        await message.answer(f"✅ Admin qo‘shildi: {new_id}")
    else:
        await message.answer("❗ Bu ID allaqachon admin.")

@dp.message_handler(lambda m: m.text == "➖ Admin o‘chirish")
async def delete_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("O‘chiriladigan admin ID sini yuboring:")
        dp.register_message_handler(do_delete_admin, state="*")

async def do_delete_admin(message: types.Message):
    data = load_data()
    del_id = int(message.text.strip())
    if del_id in data["admins"]:
        data["admins"].remove(del_id)
        save_data(data)
        await message.answer(f"✅ Admin o‘chirildi: {del_id}")
    else:
        await message.answer("❗ Bu ID admin emas.")

@dp.message_handler(lambda m: m.text == "🔙 Ortga")
async def ortga(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_menu(is_admin=True))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
