import threading
import telebot
from telebot import types
import requests
import time
import os
import re
import json
import random
from datetime import datetime
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot yoniq va nazorat ostida! "

def run_web():
    app.run(host='0.0.0.0', port=8080)

users_data = {}

# Asosiy menyu
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("Manual (Qo'lda)")
    btn2 = types.KeyboardButton("Avtomatlashtirish")
    btn3 = types.KeyboardButton("Sozlamalar")
    markup.add(btn1, btn2, btn3)
    return markup

# Qo'lda boshqarish menyusi
def get_manual_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Boshlash", callback_data="start_manual"),
               types.InlineKeyboardButton("To'xtatish", callback_data="stop_manual"))
    return markup

# Sozlamalar menyusi
def get_settings_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Akkaunt haqida", callback_data="acc_info"))
    markup.add(types.InlineKeyboardButton("Qo'llanma", callback_data="manual_guide"))
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
            return {"url": url, "headers": headers, "data": data, "is_running": False, "mode": None}
    except:
        return None
    return None

def perform_task(chat_id, duration):
    user = users_data.get(chat_id)
    if not user: return
    
    end_time = time.time() + duration
    session = requests.Session()
    
    while time.time() < end_time and user.get("is_running"):
        try:
            session.post(user["url"], headers=user["headers"], json=user["data"], timeout=5)
            time.sleep(random.uniform(0.1, 0.5)) # Har bir so'rov orasida kichik tasodifiy tanaffus
        except:
            break

def automation_logic(chat_id):
    while True:
        user = users_data.get(chat_id)
        if not user or user.get("mode") != "auto": break
        
        now = datetime.now().hour
        # Ertalab soat 6 va 11 oralig'ida ishlash
        if 6 <= now <= 11:
            duration = random.randint(5, 9) # 5-9 sekund davomiylik
            user["is_running"] = True
            perform_task(chat_id, duration)
            user["is_running"] = False
            
            # Keyingi urinishgacha tasodifiy vaqt kutish (masalan 1-5 minut)
            time.sleep(random.randint(60, 300))
        else:
            # Ish vaqti bo'lmasa, 10 minut kutib qayta tekshirish
            time.sleep(600)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Xush kelibsiz! Botdan foydalanish uchun avval cURL yuboring, so'ng menyudan foydalaning.",
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda message: message.text.startswith("curl "))
def handle_curl(message):
    parsed = parse_curl(message.text)
    if parsed:
        users_data[message.chat.id] = parsed
        bot.reply_to(message, "✅ Sozlamalar saqlandi!")
    else:
        bot.reply_to(message, "❌ cURL noto'g'ri shaklda.")

@bot.message_handler(func=lambda m: m.text in ["Manual (Qo'lda)", "Avtomatlashtirish", "Sozlamalar"])
def handle_main_menu(message):
    chat_id = message.chat.id
    if message.text == "Manual (Qo'lda)":
        bot.send_message(chat_id, "Boshqarish tugmalari:", reply_markup=get_manual_menu())
    elif message.text == "Avtomatlashtirish":
        if chat_id not in users_data:
            bot.send_message(chat_id, "Avval cURL yuboring!")
            return
        users_data[chat_id]["mode"] = "auto"
        threading.Thread(target=automation_logic, args=(chat_id,), daemon=True).start()
        bot.send_message(chat_id, "🤖 Avtomatlashtirish yoqildi (06:00 - 11:00 oralig'ida ishlaydi).")
    elif message.text == "Sozlamalar":
        bot.send_message(chat_id, "Sozlamalar bo'limi:", reply_markup=get_settings_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    user = users_data.get(chat_id)

    if call.data == "start_manual":
        if user:
            user["is_running"] = True
            user["mode"] = "manual"
            threading.Thread(target=perform_task, args=(chat_id, 3600), daemon=True).start()
            bot.answer_callback_query(call.id, "Jarayon boshlandi!")
        else:
            bot.answer_callback_query(call.id, "Ma'lumot topilmadi!")

    elif call.data == "stop_manual":
        if user:
            user["is_running"] = False
            user["mode"] = None
            bot.answer_callback_query(call.id, "To'xtatildi!")

    elif call.data == "acc_info":
        info = f"ID: {chat_id}\nHolat: {'Faol' if user else 'Nofaol'}"
        bot.send_message(chat_id, info)

    elif call.data == "manual_guide":
        guide_text = ("This bot is created for testing purposes only. "
                      "We are not responsible for any of your actions or their consequences.")
        bot.send_message(chat_id, f"ℹ️ **Disclaimer:**\n\n{guide_text}", parse_mode="Markdown")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.polling(none_stop=True)
