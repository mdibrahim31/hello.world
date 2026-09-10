"""
Telegram Bot Script for E-Commerce Order System
Responds to /start with an interactive button to launch the Telegram Mini App.
Compatible with python-telegram-bot v20+ with fallback mode.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEB_APP_URL = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://your-app-domain.com"))

def run_ptb_bot():
    """Runs the bot using modern python-telegram-bot (v20+)."""
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        first_name = user.first_name if user else "Customer"
        
        # Create Telegram WebApp button
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🛍️ Open Store & Place Order",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Open in Web Browser",
                    url=WEB_APP_URL
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            f"👋 *Welcome, {first_name}!*\n\n"
            "Welcome to our *E-Commerce Storefront*!\n"
            "Click the button below to launch our interactive Telegram Mini App "
            "where you can browse products, select quantities, and place your order directly inside Telegram.\n\n"
            "✨ *Features:*\n"
            "• Instant Mini App order form\n"
            "• Auto-filled customer info\n"
            "• Real-time order status tracking\n"
            "• Instant Telegram alert notification"
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "ℹ️ *Store Bot Help*\n\n"
            "/start - Launch the E-Commerce Web App\n"
            "/help - Show this instruction manual\n"
            "/status - Check your current chat ID for alerts\n\n"
            f"Your Telegram Chat ID is: `{update.effective_chat.id}`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        await update.message.reply_text(
            f"✅ *Bot Active*\n\n"
            f"📍 *Your Chat ID:* `{chat_id}`\n"
            f"🔗 *Web App URL:* {WEB_APP_URL}\n\n"
            "💡 _Use this Chat ID in TELEGRAM_CHAT_ID to receive real-time order alerts!_",
            parse_mode="Markdown"
        )

    async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Triggered if the Mini App sends data back via Telegram.WebApp.sendData()"""
        try:
            raw_data = update.message.web_app_data.data
            order_data = json.loads(raw_data)
            await update.message.reply_text(
                f"🎉 *Thank you for your order!*\n\n"
                f"📦 Item: *{order_data.get('product_name')}*\n"
                f"🔢 Qty: *{order_data.get('quantity')}*\n"
                f"📞 Contact: `{order_data.get('phone_number')}`\n\n"
                "We are processing your order and will contact you shortly!",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"Order data received! Thank you.")

    print(f"🚀 Initializing python-telegram-bot...")
    print(f"🔗 Web App URL configured: {WEB_APP_URL}")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    print("🤖 Bot is now polling for Telegram updates... Press Ctrl+C to stop.")
    app.run_polling()

def run_urllib_fallback():
    """Fallback standard-library long-polling runner if python-telegram-bot package is not installed."""
    print("ℹ️ python-telegram-bot not installed. Running lightweight standard library polling runner...")
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("💡 Set TELEGRAM_BOT_TOKEN in .env or run with: TELEGRAM_BOT_TOKEN=your_token python bot.py")
        return

    offset = 0
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    print(f"🤖 Bot listening for /start via Telegram Bot API...")
    print(f"🔗 Mini App URL: {WEB_APP_URL}")

    while True:
        try:
            req_url = f"{base_url}/getUpdates?offset={offset}&timeout=20"
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req, timeout=25) as res:
                body = json.loads(res.read().decode("utf-8"))
                if body.get("ok"):
                    for update in body.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message")
                        if not message:
                            continue
                        
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "")

                        if text.startswith("/start"):
                            reply_payload = {
                                "chat_id": chat_id,
                                "text": (
                                    "👋 *Welcome to our E-Commerce Store!*\n\n"
                                    "Tap the button below to launch the store Mini App:"
                                ),
                                "parse_mode": "Markdown",
                                "reply_markup": {
                                    "inline_keyboard": [
                                        [
                                            {
                                                "text": "🛍️ Open Store Mini App",
                                                "web_app": {"url": WEB_APP_URL}
                                            }
                                        ],
                                        [
                                            {
                                                "text": "🌐 Open in Web Browser",
                                                "url": WEB_APP_URL
                                            }
                                        ]
                                    ]
                                }
                            }
                            send_req = urllib.request.Request(
                                f"{base_url}/sendMessage",
                                data=json.dumps(reply_payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"}
                            )
                            urllib.request.urlopen(send_req, timeout=10)
                        elif text.startswith("/status") or text.startswith("/id"):
                            status_payload = {
                                "chat_id": chat_id,
                                "text": f"📍 *Your Telegram Chat ID:* `{chat_id}`\n\nUse this ID in `TELEGRAM_CHAT_ID` to receive order notifications!",
                                "parse_mode": "Markdown"
                            }
                            send_req = urllib.request.Request(
                                f"{base_url}/sendMessage",
                                data=json.dumps(status_payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"}
                            )
                            urllib.request.urlopen(send_req, timeout=10)
        except KeyboardInterrupt:
            print("\nBot stopped.")
            break
        except Exception as e:
            # print retry wait
            pass

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN is not set.")
        print("Please configure TELEGRAM_BOT_TOKEN to connect your Telegram Bot.")
        print("Usage: TELEGRAM_BOT_TOKEN=123456:ABC... WEB_APP_URL=https://... python bot.py")

    try:
        import telegram
        run_ptb_bot()
    except ImportError:
        run_urllib_fallback()
