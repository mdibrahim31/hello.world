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
WEB_APP_URL = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))

import database

def get_start_keyboard():
    """Generates the interactive keyboard for the /start command."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="🛍️ Open Store & Place Order",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ],
        [
            InlineKeyboardButton(text="📦 My Orders", callback_data="cmd_orders"),
            InlineKeyboardButton(text="ℹ️ Help & Guide", callback_data="cmd_help")
        ],
        [
            InlineKeyboardButton(
                text="🌐 Open in Web Browser",
                url=WEB_APP_URL
            )
        ]
    ])

def format_welcome_message(first_name="Customer", username=""):
    """Creates a formatted greeting message for /start."""
    user_handle = f" (@{username})" if username else ""
    return (
        f"👋 *Welcome to our Storefront, {first_name}!*{user_handle}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛍️ Browse products, choose quantities, and place your order directly inside Telegram!\n\n"
        "✨ *How to order:*\n"
        "1. Tap *'🛍️ Open Store & Place Order'* below to launch the Mini App.\n"
        "2. Choose your items & enter your delivery phone number.\n"
        "3. Tap *'Place Order'* — you'll receive real-time status updates!\n\n"
        "💡 *User Commands:*\n"
        "• `/start` - Launch storefront Mini App and menu\n"
        "• `/orders` - View your order history & status\n"
        "• `/help` - Store guide and customer support\n"
        "• `/status` - Check your Telegram Chat ID"
    )

def run_ptb_bot():
    """Runs the bot using modern python-telegram-bot (v20+)."""
    from telegram import Update, BotCommand, MenuButtonWebApp, WebAppInfo
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
        ContextTypes, MessageHandler, filters
    )

    async def post_init(application):
        """Sets up Telegram bot menu commands and persistent webapp menu button on launch."""
        try:
            # Clear any previously configured webhook so long-polling updates work without conflict
            await application.bot.delete_webhook(drop_pending_updates=True)
            print("✅ Telegram webhook cleared (drop_pending_updates=True)")
        except Exception as e:
            print(f"Notice clearing webhook: {e}")

        try:
            # 1. Register command list in Telegram menu
            commands = [
                BotCommand("start", "🛍️ Open Store & Place Order"),
                BotCommand("orders", "📦 View my recent orders"),
                BotCommand("help", "ℹ️ Store guide & support"),
                BotCommand("status", "📍 Check chat ID & bot status")
            ]
            await application.bot.set_my_commands(commands)
            print("✅ Bot commands registered: /start, /orders, /help, /status")

            # 2. Set persistent bottom chat menu button
            if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
                await application.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="Shop", web_app=WebAppInfo(url=WEB_APP_URL))
                )
                print(f"✅ Persistent 'Shop' MenuButton linked to: {WEB_APP_URL}")
        except Exception as e:
            print(f"Notice during bot command registration: {e}")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        first_name = user.first_name if user else "Customer"
        username = user.username if user else ""

        # Check for deep-linking parameters (e.g. /start item_1)
        args = context.args
        deep_param = args[0] if args else None

        welcome_text = format_welcome_message(first_name, username)
        if deep_param:
            welcome_text += f"\n\n🎯 _Catalog reference: `{deep_param}`_"

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_start_keyboard(),
            parse_mode="Markdown"
        )

    async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id) if user else ""
        first_name = user.first_name if user else "Customer"

        orders = database.get_orders_by_telegram_user(user_id) if user_id else []

        if not orders:
            msg = (
                f"📦 *No Orders Found for {first_name}*\n\n"
                "You haven't placed any orders yet. Tap below to browse products and place your first order!"
            )
        else:
            order_lines = []
            for o in orders[:5]:
                status_emoji = "✅" if o.get("status") == "confirmed" else "🚚" if o.get("status") == "delivered" else "⏳"
                order_lines.append(
                    f"• `{o.get('order_number')}`: *{o.get('product_name')}* (x{o.get('quantity')})\n"
                    f"  💰 ${float(o.get('total_price', 0)):.2f} — {status_emoji} {o.get('status', 'pending').upper()}"
                )
            msg = (
                f"📦 *Your Recent Orders ({len(orders)}):*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                + "\n\n".join(order_lines) +
                "\n━━━━━━━━━━━━━━━━━━━━━━\n"
                "Tap below to open the storefront anytime:"
            )

        await update.message.reply_text(
            msg,
            reply_markup=get_start_keyboard(),
            parse_mode="Markdown"
        )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        help_text = (
            "ℹ️ *Storefront Bot Help & Guide*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "• `/start` - Launch storefront Mini App and view welcome menu\n"
            "• `/orders` - View your order history & live statuses\n"
            "• `/help` - View this help message\n"
            "• `/status` - Check your Chat ID for notification configuration\n\n"
            f"📍 *Your Chat ID:* `{chat_id}`\n"
            f"🔗 *Store URL:* {WEB_APP_URL}\n\n"
            "💡 _Need assistance? Place your order via the Mini App and our team will contact you via phone or Telegram._"
        )
        await update.message.reply_text(help_text, reply_markup=get_start_keyboard(), parse_mode="Markdown")

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        await update.message.reply_text(
            f"✅ *Bot Online & Active*\n\n"
            f"📍 *Your Chat ID:* `{chat_id}`\n"
            f"🔗 *Storefront URL:* {WEB_APP_URL}\n\n"
            "💡 _Add this Chat ID to TELEGRAM_CHAT_ID on Render or in Bot Setup to receive instant order alerts!_",
            parse_mode="Markdown"
        )

    async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "cmd_orders":
            user_id = str(query.from_user.id)
            orders = database.get_orders_by_telegram_user(user_id) if user_id else []
            if not orders:
                await query.edit_message_text(
                    "📦 *No Orders Found*\n\nYou have not placed any orders yet. Tap below to launch the store and place your first order:",
                    reply_markup=get_start_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                lines = [f"• `{o.get('order_number')}`: *{o.get('product_name')}* (${float(o.get('total_price', 0)):.2f}) - {o.get('status', 'pending').upper()}" for o in orders[:5]]
                await query.edit_message_text(
                    "📦 *Your Recent Orders:*\n\n" + "\n".join(lines),
                    reply_markup=get_start_keyboard(),
                    parse_mode="Markdown"
                )
        elif data == "cmd_help":
            await query.edit_message_text(
                f"ℹ️ *How to Order:*\n1. Tap '🛍️ Open Store & Place Order' below.\n2. Choose product & enter your contact.\n3. Submit to receive real-time updates!\n\nStore URL: {WEB_APP_URL}",
                reply_markup=get_start_keyboard(),
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
        except Exception:
            await update.message.reply_text("Order data received! Thank you.")

    print(f"🚀 Initializing python-telegram-bot...")
    print(f"🔗 Web App URL configured: {WEB_APP_URL}")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    print("🤖 Bot is now polling for Telegram updates... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

def run_urllib_fallback():
    """Fallback standard-library long-polling runner if python-telegram-bot package is not installed."""
    print("ℹ️ python-telegram-bot not installed. Running lightweight standard library polling runner...")
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("💡 Set TELEGRAM_BOT_TOKEN in Render Environment Variables or in .env")
        return

    offset = 0
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    print(f"🤖 Bot listening for /start via Telegram Bot API...")
    print(f"🔗 Mini App URL: {WEB_APP_URL}")

    # Ensure any prior webhook is deleted so getUpdates does not fail with 409 Conflict
    try:
        del_req = urllib.request.Request(f"{base_url}/deleteWebhook?drop_pending_updates=true")
        urllib.request.urlopen(del_req, timeout=5)
        print("✅ Telegram webhook cleared (drop_pending_updates=True)")
    except Exception as e:
        print(f"Webhook clear notice: {e}")

    # Register bot menu commands with Telegram API
    try:
        cmd_payload = {
            "commands": [
                {"command": "start", "description": "🛍️ Open Store & Place Order"},
                {"command": "orders", "description": "📦 View my recent orders"},
                {"command": "help", "description": "ℹ️ Store guide & support"},
                {"command": "status", "description": "📍 Check chat ID & bot status"}
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
                    import time
                    time.sleep(3)
                    continue

                for update in body.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if not message:
                        continue
                        
                        chat_id = message["chat"]["id"]
                        user = message.get("from", {})
                        first_name = user.get("first_name", "Customer")
                        username = user.get("username", "")
                        user_id = str(user.get("id", ""))
                        text = message.get("text", "").strip()

                        if text.startswith("/start"):
                            reply_payload = {
                                "chat_id": chat_id,
                                "text": format_welcome_message(first_name, username),
                                "parse_mode": "Markdown",
                                "reply_markup": {
                                    "inline_keyboard": [
                                        [
                                            {
                                                "text": "🛍️ Open Store & Place Order",
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
                        elif text.startswith("/orders"):
                            orders = database.get_orders_by_telegram_user(user_id) if user_id else []
                            if not orders:
                                orders_text = f"📦 *No Orders Found for {first_name}*\n\nYou haven't placed any orders yet. Tap below to visit our store!"
                            else:
                                o_lines = [f"• `{o.get('order_number')}`: *{o.get('product_name')}* (${float(o.get('total_price', 0)):.2f}) - {o.get('status', 'pending').upper()}" for o in orders[:5]]
                                orders_text = f"📦 *Your Recent Orders:*\n\n" + "\n".join(o_lines)
                            
                            orders_payload = {
                                "chat_id": chat_id,
                                "text": orders_text,
                                "parse_mode": "Markdown",
                                "reply_markup": {
                                    "inline_keyboard": [
                                        [{"text": "🛍️ Open Store", "web_app": {"url": WEB_APP_URL}}]
                                    ]
                                }
                            }
                            send_req = urllib.request.Request(
                                f"{base_url}/sendMessage",
                                data=json.dumps(orders_payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"}
                            )
                            urllib.request.urlopen(send_req, timeout=10)
                        elif text.startswith("/help"):
                            help_payload = {
                                "chat_id": chat_id,
                                "text": (
                                    "ℹ️ *Storefront Bot Help*\n\n"
                                    "• `/start` - Launch storefront Mini App\n"
                                    "• `/orders` - View your order history\n"
                                    "• `/help` - Help & guide\n"
                                    "• `/status` - View Chat ID\n\n"
                                    f"📍 Chat ID: `{chat_id}`"
                                ),
                                "parse_mode": "Markdown",
                                "reply_markup": {
                                    "inline_keyboard": [
                                        [{"text": "🛍️ Open Store", "web_app": {"url": WEB_APP_URL}}]
                                    ]
                                }
                            }
                            send_req = urllib.request.Request(
                                f"{base_url}/sendMessage",
                                data=json.dumps(help_payload).encode("utf-8"),
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
            print(f"⚠️ Telegram polling connection notice: {e}")
            import time
            time.sleep(3)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN is not set.")
        print("Please configure TELEGRAM_BOT_TOKEN to connect your Telegram Bot.")
        print("Usage: TELEGRAM_BOT_TOKEN=123456:ABC... WEB_APP_URL=https://... python bot.py")

    try:
        import telegram
        run_ptb_bot()
    except ImportError:
        run_urllib_fallback()

if __name__ == "__main__":
    main()
