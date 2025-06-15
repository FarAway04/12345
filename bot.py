import os
import json
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ✅ Environment variable dan o'qish
API_TOKEN = os.environ.get("API_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CHANNELS = os.environ.get("CHANNELS", "").split(",")  # Masalan: @MyChannel1,@MyChannel2

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = 'movies.json'

# JSON mavjud bo'lmasa yaratadi
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


# 👑 Admin menyu
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kinolar", "📢 Kanallar")
    kb.add("👤 Adminlar", "📊 Statistika")
    return kb


# 🎞 Kino bo'limi
def kino_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Kino qo'shish", "🗑 Kino o'chirish")
    kb.add("🔙 Ortga")
    return kb


# 👤 Adminlar bo'limi
def adminlar_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Admin qo'shish", "➖ Admin o'chirish")
    kb.add("🔙 Ortga")
    return kb


# ✅ Majburiy obuna Inline tugma
def sub_keyboard():
    data = load_data()
    ikb = InlineKeyboardMarkup(row_width=1)
    for ch in data['channels']:
        ikb.add(InlineKeyboardButton(f"{ch}", url=f"https://t.me/{ch.replace('@','')}"))
    ikb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return ikb


# 🔍 Obuna tekshiradi
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


# 🚀 /start
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


# ✅ Tekshirish tugmasi
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.answer("✅ Obuna tekshirildi! Endi kino kodini yuboring!")
    else:
        await call.message.answer("❗ Hali hamma kanallarga obuna bo‘lmadingiz.", reply_markup=sub_keyboard())


# 🔑 Kino kod yuborish (USER)
@dp.message_handler(lambda msg: msg.text not in ["🎬 Kinolar", "📢 Kanallar", "👤 Adminlar", "📊 Statistika",
                                                  "➕ Kino qo'shish", "🗑 Kino o'chirish", 
                                                  "➕ Admin qo'shish", "➖ Admin o'chirish", "🔙 Ortga"])
async def user_search_movie(message: types.Message):
    user_id = message.from_user.id
    if user_id in load_data()['admins']:
        return  # Admin bo'lsa bu qism ishlamaydi
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


# 🎬 Kinolar
@dp.message_handler(lambda msg: msg.text == "🎬 Kinolar")
async def kinolar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        await message.answer("Kinolar bo‘limi:", reply_markup=kino_menu())


# 📢 Kanallar
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


# 👤 Adminlar
@dp.message_handler(lambda msg: msg.text == "👤 Adminlar")
async def adminlar(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        await message.answer("Adminlar bo‘limi:", reply_markup=adminlar_menu())


# 📊 Statistika
@dp.message_handler(lambda msg: msg.text == "📊 Statistika")
async def statistika(message: types.Message):
    if message.from_user.id in load_data()['admins']:
        data = load_data()
        await message.answer(
            f"👥 Foydalanuvchilar: {len(data['users'])}\n"
            f"🎬 Kinolar: {len(data['movies'])}\n"
            f"👑 Adminlar: {len(data['admins'])}"
        )


# ➕ Kino qo'shish
@dp.message_handler(lambda msg: msg.text == "➕ Kino qo'shish")
async def add_movie_step1(message: types.Message):
    await message.answer("Yangi kino kodi?")
    dp.register_message_handler(add_movie_step2, state="*")


async def add_movie_step2(message: types.Message):
    message.bot['new_code'] = message.text.strip()
    await message.answer("Kino faylini yuboring:")
    dp.register_message_handler(add_movie_save, content_types=['document'], state="*")


async def add_movie_save(message: types.Message):
    data = load_data()
    code = message.bot['new_code']
    file_id = message.document.file_id
    data['movies'].append({"code": code, "file_id": file_id})
    save_data(data)
    await message.answer(f"✅ Kino qo'shildi: {code}")


# 🗑 Kino o'chirish
@dp.message_handler(lambda msg: msg.text == "🗑 Kino o'chirish")
async def delete_movie_step1(message: types.Message):
    await message.answer("O'chiriladigan kino kodini yuboring:")
    dp.register_message_handler(delete_movie_save, state="*")


async def delete_movie_save(message: types.Message):
    data = load_data()
    code = message.text.strip()
    data['movies'] = [m for m in data['movies'] if m['code'] != code]
    save_data(data)
    await message.answer(f"✅ Kino o'chirildi: {code}")


# ➕ Admin qo'shish
@dp.message_handler(lambda msg: msg.text == "➕ Admin qo'shish")
async def add_admin_step1(message: types.Message):
    await message.answer("Yangi admin ID yuboring:")
    dp.register_message_handler(add_admin_save, state="*")


async def add_admin_save(message: types.Message):
    data = load_data()
    new_id = int(message.text.strip())
    if new_id not in data['admins']:
        data['admins'].append(new_id)
        save_data(data)
        await message.answer(f"✅ Admin qo'shildi: {new_id}")
    else:
        await message.answer("Bu ID allaqachon admin.")


# ➖ Admin o'chirish
@dp.message_handler(lambda msg: msg.text == "➖ Admin o'chirish")
async def delete_admin_step1(message: types.Message):
    await message.answer("O'chiriladigan admin ID yuboring:")
    dp.register_message_handler(delete_admin_save, state="*")


async def delete_admin_save(message: types.Message):
    data = load_data()
    del_id = int(message.text.strip())
    if del_id in data['admins']:
        data['admins'].remove(del_id)
        save_data(data)
        await message.answer(f"✅ Admin o'chirildi: {del_id}")
    else:
        await message.answer("Bu ID admin emas.")


# 🔙 Ortga
@dp.message_handler(lambda msg: msg.text == "🔙 Ortga")
async def back_to_menu(message: types.Message):
    await message.answer("👑 Admin menyu:", reply_markup=admin_menu())


# 🚀 Ishga tushirish
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
