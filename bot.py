"""
Telegram Bot Script for E-Commerce Order System & Supabase Integration
Features:
1. /start: Interactive menu offering "Register", "Search Image", and Storefront
2. Registration Flow (4 Steps):
   - Name -> Phone -> Image Title -> Photo Upload -> Supabase Storage ('user-images') & Database ('users')
3. Search Flow:
   - Type/Send Image Name -> Query Supabase 'users' -> Return User, Phone, and Photo
4. Storefront Mini App, /orders, /admin, /status, /cancel, /help
5. Dual mode: python-telegram-bot (v20+) or lightweight standard-library polling
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com")).strip()

import database
import supabase_client
import bot_workflow

def run_ptb_bot():
    """Runs the bot using python-telegram-bot (v20+)."""
    import asyncio
    from telegram import Update, BotCommand, MenuButtonWebApp, WebAppInfo
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
        ContextTypes, MessageHandler, filters
    )

    async def post_init(application):
        """Sets up Telegram bot menu commands and persistent webapp menu button on launch."""
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            print("✅ Telegram webhook cleared (drop_pending_updates=True)")
        except Exception as e:
            print(f"Notice clearing webhook: {e}")

        try:
            commands = [
                BotCommand("start", "🚀 Main menu: Register, Search & Store"),
                BotCommand("register", "📝 Register user profile & upload image"),
                BotCommand("search", "🔍 Search Supabase by Image Name"),
                BotCommand("orders", "📦 View my recent orders"),
                BotCommand("admin", "👑 Admin order summary"),
                BotCommand("tables", "🗄️ Database tables overview"),
                BotCommand("migrate", "⚡ Create & initialize 14 DB tables"),
                BotCommand("cancel", "❌ Cancel current step"),
                BotCommand("help", "ℹ️ Bot guide & all commands"),
                BotCommand("status", "📍 Check chat ID & Supabase status")
            ]
            await application.bot.set_my_commands(commands)
            print("✅ Bot commands registered in Telegram menu.")

            if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
                await application.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="Shop", web_app=WebAppInfo(url=WEB_APP_URL))
                )
                print(f"✅ Persistent 'Shop' MenuButton linked to: {WEB_APP_URL}")
        except Exception as e:
            print(f"Notice during bot command registration: {e}")

    async def unified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dispatches update to the unified bot_workflow engine."""
        try:
            update_dict = update.to_dict()
            await asyncio.to_thread(
                bot_workflow.handle_update,
                update_dict,
                bot_token=TELEGRAM_BOT_TOKEN,
                web_url=WEB_APP_URL
            )
        except Exception as e:
            print(f"⚠️ Error in unified_handler: {e}")

    print(f"🚀 Initializing python-telegram-bot...")
    print(f"🔗 Web App URL configured: {WEB_APP_URL}")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start", unified_handler))
    app.add_handler(CommandHandler("register", unified_handler))
    app.add_handler(CommandHandler("search", unified_handler))
    app.add_handler(CommandHandler("cancel", unified_handler))
    app.add_handler(CommandHandler("orders", unified_handler))
    app.add_handler(CommandHandler("admin", unified_handler))
    app.add_handler(CommandHandler("tables", unified_handler))
    app.add_handler(CommandHandler("migrate", unified_handler))
    app.add_handler(CommandHandler("help", unified_handler))
    app.add_handler(CommandHandler("status", unified_handler))

    # Inline Keyboard Callbacks
    app.add_handler(CallbackQueryHandler(unified_handler))

    # Messages (Text, Photos, Documents)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, unified_handler))

    print("🤖 Bot is now polling for Telegram updates... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

def run_urllib_fallback():
    """Fallback standard-library long-polling runner if python-telegram-bot is unavailable."""
    print("ℹ️ Running lightweight standard library polling runner...")
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("💡 Set TELEGRAM_BOT_TOKEN in Render Environment Variables or in .env")
        return

    offset = 0
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    print(f"🤖 Bot listening for Telegram events via Bot API...")
    print(f"🔗 Mini App URL: {WEB_APP_URL}")

    # Clear prior webhook
    try:
        del_req = urllib.request.Request(f"{base_url}/deleteWebhook?drop_pending_updates=true")
        urllib.request.urlopen(del_req, timeout=5)
        print("✅ Telegram webhook cleared (drop_pending_updates=True)")
    except Exception as e:
        print(f"Webhook clear notice: {e}")

    # Register bot commands
    try:
        cmd_payload = {
            "commands": [
                {"command": "start", "description": "🚀 Main menu: Register, Search & Store"},
                {"command": "register", "description": "📝 Register user profile & upload image"},
                {"command": "search", "description": "🔍 Search Supabase by Image Name"},
                {"command": "orders", "description": "📦 View my recent orders"},
                {"command": "admin", "description": "👑 Admin order summary"},
                {"command": "cancel", "description": "❌ Cancel current step"},
                {"command": "help", "description": "ℹ️ Bot guide & all commands"},
                {"command": "status", "description": "📍 Check chat ID & Supabase status"}
            ]
        }
        cmd_req = urllib.request.Request(
            f"{base_url}/setMyCommands",
            data=json.dumps(cmd_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(cmd_req, timeout=5)
        print("✅ Telegram bot menu commands set via Bot API.")
    except Exception as e:
        print(f"Command registration notice: {e}")

    while True:
        try:
            req_url = f"{base_url}/getUpdates?offset={offset}&timeout=20"
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req, timeout=25) as res:
                body = json.loads(res.read().decode("utf-8"))
                if not body.get("ok"):
                    print(f"⚠️ Telegram getUpdates warning: {body.get('description')}")
                    time.sleep(3)
                    continue

                for update in body.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        bot_workflow.handle_update(update, bot_token=TELEGRAM_BOT_TOKEN, web_url=WEB_APP_URL)
                    except Exception as handle_err:
                        print(f"⚠️ Error processing update: {handle_err}")

        except KeyboardInterrupt:
            print("\nBot stopped.")
            break
        except Exception as e:
            print(f"⚠️ Telegram polling connection notice: {e}")
            time.sleep(3)

def main():
    try:
        database.init_db()
    except Exception as db_err:
        print(f"⚠️ [bot.py] database init notice: {db_err}")

    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN is not set.")
        print("Please configure TELEGRAM_BOT_TOKEN to connect your Telegram Bot.")

    try:
        import telegram
        run_ptb_bot()
    except ImportError:
        run_urllib_fallback()

if __name__ == "__main__":
    main()
