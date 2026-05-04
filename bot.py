import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import database
from agent import process_message

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_TELEGRAM_USER_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != AUTHORIZED_USER_ID and AUTHORIZED_USER_ID != "your_telegram_user_id_here":
        await update.message.reply_text("You are not authorized to use this bot.")
        return
        
    keyboard = [
        [KeyboardButton("📝 Pending Tasks"), KeyboardButton("🌐 Website Status")],
        [KeyboardButton("🧠 Search Knowledge"), KeyboardButton("💸 Expense Summary")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Hi Mohan, I am your personal AI assistant. Send /help for more info.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != AUTHORIZED_USER_ID and AUTHORIZED_USER_ID != "your_telegram_user_id_here":
        return

    help_text = """
I can help with:
1. Memory
2. To-do list
3. Reminders
4. Website status checks
5. Knowledge base
6. Email drafts

Send a message like:
- Remember my website is techwithktg.com
- Add task renew domain tomorrow
- Check my website techwithktg.com
- Draft email to client
"""
    await update.message.reply_text(help_text)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != AUTHORIZED_USER_ID and AUTHORIZED_USER_ID != "your_telegram_user_id_here":
        return
        
    current = database.get_setting("active_model", "gemini-3.1-flash-lite-preview")
    
    keyboard = [
        [InlineKeyboardButton("Gemini 3.1 Flash Lite Preview", callback_data="model:gemini-3.1-flash-lite-preview")],
        [InlineKeyboardButton("Gemma 4 31B IT", callback_data="model:gemma-4-31b-it")],
        [InlineKeyboardButton("Gemma 4 26B IT", callback_data="model:gemma-4-26-it")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Current model is: {current}\n\nSelect a new model:", 
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if str(query.from_user.id) != AUTHORIZED_USER_ID and AUTHORIZED_USER_ID != "your_telegram_user_id_here":
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer()
    
    data = query.data
    if data.startswith("model:"):
        new_model = data.split(":", 1)[1]
        database.set_setting("active_model", new_model)
        await query.edit_message_text(text=f"✅ Model successfully changed to: {new_model}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != AUTHORIZED_USER_ID and AUTHORIZED_USER_ID != "your_telegram_user_id_here":
        await update.message.reply_text("Unauthorized user.")
        return

    # Send a temporary "thinking" message
    processing_msg = await update.message.reply_text("🤔 Thinking...")
    
    # Keep the typing indicator active
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    user_text = update.message.text
    
    # Run the synchronous LLM function in a separate thread so it doesn't block the bot
    response_text = await asyncio.to_thread(process_message, user_text)
    
    # Edit the temporary message with the final response
    await processing_msg.edit_text(response_text)

def main():
    database.init_db()
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("Error: TELEGRAM_BOT_TOKEN is missing from .env")
        return
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
