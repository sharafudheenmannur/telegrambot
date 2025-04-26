import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random
import os

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Store users waiting, chatting, and referrals
waiting_users = []
active_chats = {}
chat_logs = {}
blocked_users = set()
user_points = {}
user_referrals = {}

# Admin ID (Replace with your Telegram User ID)
ADMIN_CHAT_ID = 608729807  # Replace with your actual admin ID

# Global announcement
announcement_message = "No announcements available."

# Function to extract user details
def get_user_info(user):
    return f"👤 Name: {user.first_name} {user.last_name or ''}\n🔹 Username: @{user.username or 'N/A'}\n🔢 User ID: {user.id}"

# Generate referral link
def get_referral_link(user_id):
    return f"https://t.me/Anonymous_chat_international_bot?start={user_id}"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if user.id in blocked_users:
        await update.message.reply_text("🚫 You are blocked from using this bot.")
        return

    args = context.args
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        if referrer_id != user.id and referrer_id not in blocked_users:
            user_points[referrer_id] = user_points.get(referrer_id, 0) + 10

    keyboard = ReplyKeyboardMarkup([
        ["📢 Announcements", "🔍 Find"],
        ["🔗 Get Referral Link", "💰 Balance"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        f"Hi {user.first_name}! Welcome to the Woodiee Anonymous Dating Bot.",
        reply_markup=keyboard
    )

    # Notify admin
    user_info = get_user_info(user)
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 New User Joined:\n{user_info}")

# Find a random user to chat with
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id in blocked_users:
        await update.message.reply_text("🚫 You are blocked from using this bot.")
        return

    if user_id in active_chats:
        await update.message.reply_text("❗ You are already in a chat! Use '❌ Stop Chat' to end it first.")
        return

    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        chat_logs[user_id] = []
        chat_logs[partner_id] = []

        keyboard = ReplyKeyboardMarkup([
            ["❌ Stop Chat", "🚨 Report User"]
        ], resize_keyboard=True)

        await context.bot.send_message(chat_id=user_id, text="✅ You are now connected! Say Hi!", reply_markup=keyboard)
        await context.bot.send_message(chat_id=partner_id, text="✅ You are now connected! Say Hi!", reply_markup=keyboard)

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🔗 New Chat Started:\nUser 1: {user_id}\nUser 2: {partner_id}")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("🔍 Searching for a partner... Please wait.")

# Forward messages between users and handle main menu
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    text = update.message.text

    if user_id in blocked_users:
        await update.message.reply_text("🚫 You are blocked from using this bot.")
        return

    if text == "📢 Announcements":
        await update.message.reply_text(announcement_message)
        return

    if text == "🔍 Find":
        await find(update, context)
        return

    if text == "🔗 Get Referral Link":
        link = get_referral_link(user_id)
        await update.message.reply_text(f"🔗 🌟 Find Your Perfect Anonymous Match with Woodiee Dating Bot! 🌟 {link}")
        return

    if text == "💰 Balance":
        points = user_points.get(user_id, 0)
        await update.message.reply_text(f"💰 Your current balance: {points} points")
        return

    if user_id in active_chats:
        if text == "❌ Stop Chat":
            await stop_chat(user_id, context)
            return

        if text == "🚨 Report User":
            await report_user(user_id, context)
            return

        partner_id = active_chats[user_id]
        chat_logs[user_id].append(f"You: {text}")
        chat_logs[partner_id].append(f"Partner: {text}")

        await context.bot.send_message(chat_id=partner_id, text=text)
    else:
        await update.message.reply_text("❗ You're not in a chat. Use '🔍 Find' to start chatting.")

# Save and return chat log file
def save_chat_log(user_id, partner_id):
    log_file = f"chat_log_{user_id}_{partner_id}.txt"
    with open(log_file, "w") as f:
        f.write("\n".join(chat_logs.get(user_id, [])))
    return log_file

# Stop the chat and return to main menu
async def stop_chat(user_id, context):
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)

        log_file = save_chat_log(user_id, partner_id)

        main_menu_keyboard = ReplyKeyboardMarkup([
            ["📢 Announcements", "🔍 Find"],
            ["🔗 Get Referral Link", "💰 Balance"]
        ], resize_keyboard=True)

        await context.bot.send_message(chat_id=user_id, text="❌ Chat ended.", reply_markup=main_menu_keyboard)
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner left the chat.", reply_markup=main_menu_keyboard)

        try:
            await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=open(log_file, "rb"), caption=f"📄 Chat Log: {user_id} and {partner_id}")
        finally:
            os.remove(log_file)

# Report a user and end the chat
async def report_user(user_id, context):
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        log_file = save_chat_log(user_id, partner_id)

        try:
            await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=open(log_file, "rb"),
                                            caption=f"🚨 User Report:\n{user_id} reported {partner_id}\nUse /block {partner_id} to block this user.")
        finally:
            os.remove(log_file)

        await stop_chat(user_id, context)

# Update announcement (admin only)
async def update_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global announcement_message
    if update.effective_user.id == ADMIN_CHAT_ID:
        announcement_message = " ".join(context.args)
        await update.message.reply_text("✅ Announcement updated.")
    else:
        await update.message.reply_text("❌ You are not authorized to perform this action.")

# Main function to start the bot
def main():
    TOKEN = "8155381284:AAFmWGj12M68fOxYz2p6Qp1A5ggCOq185KU"  # Your real bot token
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update_announcement", update_announcement))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()