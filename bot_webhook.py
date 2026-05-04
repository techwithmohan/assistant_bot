import os
import asyncio
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

import database
# Import all the exact same handlers you already wrote in bot.py
from bot import start_command, help_command, model_command, button_callback, handle_message

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Flask
flask_app = Flask(__name__)

# Initialize DB
database.init_db()

# Initialize Telegram App
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("model", model_command))
telegram_app.add_handler(CallbackQueryHandler(button_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run initialize synchronously for the Flask context
async def init_telegram():
    await telegram_app.initialize()
    await telegram_app.start()

# For WSGI, it's safer to use an event loop that we manage
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_telegram())

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram will hit this URL with new messages."""
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        
        # Process the update using the async loop
        loop.run_until_complete(telegram_app.process_update(update))
        return 'ok', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Internal Server Error', 500

@flask_app.route('/', methods=['GET'])
def index():
    return "Bot is successfully running via Webhook on shared hosting!", 200

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
