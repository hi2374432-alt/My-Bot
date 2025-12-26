import telebot
from telebot import types
from PIL import Image
import os
import qrcode
import time
import asyncio
import edge_tts # Real Voice ke liye
import pyshorteners

# ==========================================
# 👇 TERI DETAILS (PRE-FILLED)
# ==========================================

API_TOKEN = "7873592641:AAGtXYGIb4K95012QOHIcrZBILRJYTj8DhI"
ADMIN_ID = 7197775068
CHANNEL_USERNAME = "@MyProConverter"
ADMIN_USERNAME = "@iDivaaaa"

UPI_ID = "vickyedit@ybl"
PRICE_TAG = "Rs 79/ Month"
FREE_LIMIT = 2

# ==========================================
# 🛑 MAIN LOGIC
# ==========================================

bot = telebot.TeleBot(API_TOKEN)
shortener = pyshorteners.Shortener()

user_states = {}
user_limits = {}
premium_users = []
user_queues = {}

# --- REAL VOICE FUNCTION (ASYNC) ---
async def generate_real_voice(text, filename):
    # Voice Options: en-US-AriaNeural (Woman), en-US-GuyNeural (Man)
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(filename)

# --- MENU ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📸 Images to PDF", callback_data="mode_pdf")
    btn2 = types.InlineKeyboardButton("🗣️ Real AI Voice", callback_data="mode_speak")
    btn3 = types.InlineKeyboardButton("🔗 URL Shortener", callback_data="mode_short")
    btn4 = types.InlineKeyboardButton("🔳 QR Generator", callback_data="mode_qr")
    btn5 = types.InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")
    markup.add(btn1, btn2, btn3, btn4)
    markup.add(btn5)
    return markup

# --- CHECKS ---
def check_access(user_id):
    if user_id == ADMIN_ID or user_id in premium_users: return True
    usage = user_limits.get(user_id, 0)
    return usage < FREE_LIMIT

def increase_usage(user_id):
    if user_id not in premium_users and user_id != ADMIN_ID:
        user_limits[user_id] = user_limits.get(user_id, 0) + 1

def is_subscribed(user_id):
    try:
        if user_id == ADMIN_ID: return True
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        if status in ['creator', 'administrator', 'member']: return True
        return False
    except: return False 

def send_force_join(chat_id):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
    btn2 = types.InlineKeyboardButton("✅ Checked", callback_data="check_join")
    markup.add(btn, btn2)
    bot.send_message(chat_id, "⚠️ Join our channel first!", reply_markup=markup)

# --- START ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    if not is_subscribed(message.from_user.id): return send_force_join(message.chat.id)
    user_states[message.from_user.id] = None
    status = "💎 Premium" if message.from_user.id in premium_users else "👤 Free"
    bot.send_message(message.chat.id, f"🤖 **Pro Bot Menu**\nStatus: {status}", reply_markup=main_menu())

# --- BUTTONS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "check_join":
        if is_subscribed(user_id): 
            bot.answer_callback_query(call.id, "Success!")
            bot.send_message(call.message.chat.id, "Menu:", reply_markup=main_menu())
        else: bot.answer_callback_query(call.id, "Not Joined!", show_alert=True)
        return

    if call.data == "buy_premium":
        user_states[user_id] = "waiting_payment_proof"
        bot.send_message(call.message.chat.id, f"💎 **Premium**\nPay {PRICE_TAG} to `{UPI_ID}`\nSend screenshot here.")
        return

    if call.data.startswith("approve_"):
        if user_id != ADMIN_ID: return 
        target = int(call.data.split("_")[1])
        if target not in premium_users: premium_users.append(target)
        bot.send_message(target, "🎉 You are now Premium!")
        bot.edit_message_caption("✅ Approved", call.message.chat.id, call.message.message_id)

    if call.data.startswith("reject_"):
        if user_id != ADMIN_ID: return
        target = int(call.data.split("_")[1])
        bot.send_message(target, f"❌ Payment Rejected.\nContact: {ADMIN_USERNAME}")
        bot.edit_message_caption("❌ Rejected", call.message.chat.id, call.message.message_id)

    if call.data.startswith("mode_"):
        user_states[user_id] = call.data.replace("mode_", "")
        if user_states[user_id] == "pdf":
            user_queues[user_id] = []
            bot.send_message(call.message.chat.id, "📸 **PDF Mode:** Send photos. Type /done to finish.")
        else:
            bot.send_message(call.message.chat.id, f"✅ **{user_states[user_id].upper()} Mode On!** Send text/input.")
        bot.answer_callback_query(call.id)

# --- PHOTOS ---
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id): return send_force_join(message.chat.id)

    if user_states.get(user_id) == "waiting_payment_proof":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅", callback_data=f"approve_{user_id}"), types.InlineKeyboardButton("❌", callback_data=f"reject_{user_id}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"💰 Pay Check: {user_id}", reply_markup=markup)
        user_states[user_id] = None
        bot.reply_to(message, "Sent to Admin...")
        return

    if not check_access(user_id): return bot.reply_to(message, "🛑 Limit Over!")
    
    if user_states.get(user_id) == "pdf":
        if user_id not in user_queues: user_queues[user_id] = []
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        fname = f"img_{user_id}_{int(time.time())}.jpg"
        with open(fname, 'wb') as f: f.write(downloaded)
        user_queues[user_id].append(fname)
        bot.reply_to(message, f"Saved ({len(user_queues[user_id])}). Send more or /done")
    else:
        bot.reply_to(message, "⚠️ Select tool from Menu first.", reply_markup=main_menu())

# --- TEXT ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    if message.text.startswith("/"): return
    if not is_subscribed(user_id): return send_force_join(message.chat.id)
    if not check_access(user_id): return bot.reply_to(message, "🛑 Limit Over!")

    mode = user_states.get(user_id)
    if not mode: return bot.reply_to(message, "⚠️ Select Option.", reply_markup=main_menu())

    if mode == "speak":
        bot.reply_to(message, "🗣️ Generating Real Voice... (Wait)")
        try:
            fname = f"voice_{user_id}.mp3"
            asyncio.run(generate_real_voice(message.text, fname))
            with open(fname, 'rb') as f: bot.send_audio(message.chat.id, f, title="AI Human Voice")
            os.remove(fname)
            increase_usage(user_id)
        except Exception as e: bot.reply_to(message, f"Error: {e}")

    elif mode == "short":
        try: bot.reply_to(message, f"Link: {shortener.tinyurl.short(message.text)}"); increase_usage(user_id)
        except: bot.reply_to(message, "Invalid Link")

    elif mode == "qr":
        img = qrcode.make(message.text)
        img.save(f"qr_{user_id}.png")
        with open(f"qr_{user_id}.png", 'rb') as f: bot.send_photo(message.chat.id, f)
        os.remove(f"qr_{user_id}.png")
        increase_usage(user_id)

# --- SUPER PDF FIX ---
@bot.message_handler(commands=['done'])
def make_pdf(message):
    user_id = message.from_user.id
    if user_id not in user_queues or not user_queues[user_id]:
        return bot.reply_to(message, "❌ No photos! Send photos again.")
    
    bot.reply_to(message, "🔄 Creating PDF...")
    try:
        image_list = []
        # LOAD AND CLOSE STRATEGY
        for f in user_queues[user_id]:
            img = Image.open(f)
            img.load() # Memory mein load karo
            img_copy = img.copy() # Copy banao
            img.close() # Asli file TURANT band karo
            image_list.append(img_copy.convert('RGB'))

        pdf_name = f"Doc_{user_id}.pdf"
        image_list[0].save(pdf_name, save_all=True, append_images=image_list[1:])
        
        with open(pdf_name, 'rb') as f: bot.send_document(message.chat.id, f)
        
        # Cleanup (Ab delete hoga kyunki close kar diya tha)
        for f in user_queues[user_id]: 
            try: os.remove(f)
            except: pass
        try: os.remove(pdf_name)
        except: pass
        
        user_queues[user_id] = []
        user_states[user_id] = None
        bot.send_message(message.chat.id, "✅ Done! Menu:", reply_markup=main_menu())
        increase_usage(user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")
        user_queues[user_id] = []

print("✅ ULTRA PRO BOT STARTED...")
bot.polling()