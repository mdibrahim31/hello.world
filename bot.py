#!/usr/bin/env python3
"""
Telegram Bot Worker for Render / Background Service
---------------------------------------------------
- Regular Users: Chat-only interaction (/start, /menu, /order, /help, /status).
  (Mini App is completely removed for regular users).
- Admin: Only verified Admins (matching ADMIN_TELEGRAM_ID or TELEGRAM_CHAT_ID)
  can use /admin to receive the private Admin Mini App launcher button.
- In-memory experiment architecture (Zero database requirement).
"""

import os
import sys
import time
import json
import logging
import requests
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("telegram_bot")

# Configuration from Environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://hello-world-fcg3.onrender.com").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000").strip()

# In-memory product catalog for experiment
CATALOG = [
    {
        "id": 1,
        "name": "Wireless Noise-Cancelling Earbuds",
        "price": 49.99,
        "desc": "Active noise cancellation with 28-hr battery life."
    },
    {
        "id": 2,
        "name": "Vintage Mechanical Keyboard RGB",
        "price": 89.50,
        "desc": "Custom mechanical switches with RGB backlight."
    },
    {
        "id": 3,
        "name": "Smart Fitness Tracker Band",
        "price": 34.99,
        "desc": "Heart rate, SpO2, sleep monitor & 14-day battery."
    },
    {
        "id": 4,
        "name": "Ultra-light Commuter Backpack",
        "price": 59.00,
        "desc": "Ergonomic waterproof build with 16-inch laptop pocket."
    }
]

# In-memory orders store
memory_orders = []


def telegram_api(method, payload=None):
    """Make requests to Telegram Bot API with error handling."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing. Please set it in Render Environment Variables.")
        return {"ok": False, "error": "Missing BOT_TOKEN"}
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=payload or {}, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"Telegram API exception on {method}: {e}")
        return {"ok": False, "error": str(e)}


def setup_bot_commands():
    """
    1. Register user-friendly chat commands (/start, /menu, /order, /help, /status).
    2. Reset chat menu button to default so regular users DO NOT get the Mini App button.
    """
    logger.info("Configuring Bot Commands & Restricting User Menu...")
    
    # 1. Set public bot commands
    user_commands = [
        {"command": "start", "description": "👋 Start bot & view store instructions"},
        {"command": "menu", "description": "🛍️ View products & prices in chat"},
        {"command": "order", "description": "📦 Place order directly via chat"},
        {"command": "help", "description": "ℹ️ How to order & customer support"},
        {"command": "status", "description": "📍 Check your Telegram Chat ID"}
    ]
    cmd_res = telegram_api("setMyCommands", {"commands": user_commands})
    logger.info(f"setMyCommands response: {cmd_res.get('ok')}")

    # 2. Restrict Chat Menu Button to standard default (Removes Mini App for regular users)
    menu_res = telegram_api("setChatMenuButton", {"menu_button": {"type": "default"}})
    logger.info(f"setChatMenuButton (default) response: {menu_res.get('ok')}")


def send_admin_alert(order):
    """Send real-time order alert to Admin Telegram Chat."""
    target_chat = ADMIN_TELEGRAM_ID or CHAT_ID
    if not target_chat:
        logger.warning("No Admin Chat ID configured. Skipping admin alert.")
        return

    qty = order.get("quantity", 1)
    total = f"{order.get('total_price', 0):.2f}"
    username_line = f"\n👤 *Telegram User:* @{order['telegram_username']}" if order.get('telegram_username') else ""
    user_id_line = f" (ID: `{order['telegram_user_id']}`)" if order.get('telegram_user_id') else ""
    notes_line = f"\n📝 *Notes:* _{order['notes']}_" if order.get('notes') else ""

    alert_text = (
        "🔔 *NEW ORDER ALERT (ADMIN ONLY)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Order Ref:* `{order.get('order_number')}`\n"
        f"👤 *Customer:* *{order.get('customer_name')}*\n"
        f"📞 *Phone:* `{order.get('phone_number')}`\n"
        f"📦 *Product:* *{order.get('product_name')}*\n"
        f"🔢 *Quantity:* {qty} unit(s)\n"
        f"💰 *Total Amount:* ${total}\n"
        f"📍 *Channel:* Telegram Chat Bot"
        f"{username_line}{user_id_line}"
        f"{notes_line}\n"
        f"🕒 *Time:* {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ _Manage in Admin Mini App: /admin_"
    )

    telegram_api("sendMessage", {
        "chat_id": target_chat,
        "text": alert_text,
        "parse_mode": "Markdown"
    })


def is_admin(user_id, chat_id):
    """Check if the sender is the authorized administrator."""
    uid = str(user_id).strip()
    cid = str(chat_id).strip()
    
    admin_id = str(ADMIN_TELEGRAM_ID).strip()
    global_chat_id = str(CHAT_ID).strip()

    if admin_id and uid == admin_id:
        return True
    if global_chat_id and (uid == global_chat_id or cid == global_chat_id):
        return True
    return False


def handle_start(chat_id, user):
    """Handle /start command."""
    first_name = user.get("first_name", "Customer")
    text = (
        f"👋 *Welcome to our Store, {first_name}!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Browse products and place your order directly inside this chat.\n\n"
        "🛍️ *Quick Commands:*\n"
        "• `/menu` — View our full product list & prices\n"
        "• `/order` — Place an order directly via message\n"
        "• `/help` — How to order & support details\n"
        "• `/status` — View your Telegram Chat ID\n\n"
        "👉 Type `/menu` now to explore available items!"
    )
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


def handle_menu(chat_id):
    """Handle /menu command."""
    lines = ["🛍️ *PRODUCT CATALOG (ORDER IN CHAT)*\n━━━━━━━━━━━━━━━━━━━━━━"]
    for p in CATALOG:
        lines.append(
            f"*{p['id']}. {p['name']}*\n"
            f"💰 Price: *${p['price']:.2f}*\n"
            f"ℹ️ _{p['desc']}_"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        "👉 *To place an order, send:*\n"
        "`/order <Item_No> <Qty> <Phone> <Your_Name>`\n\n"
        "_Example:_\n"
        "`/order 1 1 +15550192834 Alex Morgan`"
    )

    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": "\n\n".join(lines),
        "parse_mode": "Markdown"
    })


def handle_order(chat_id, user, text):
    """
    Handle /order command.
    Format: /order <Item Number> <Qty> <Phone Number> [Customer Name / Notes]
    """
    parts = text.strip().split(maxsplit=4)
    if len(parts) < 4:
        guide = (
            "📦 *How to Place an Order in Chat:*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Please send the `/order` command in this format:\n\n"
            "`/order <Item_Number> <Quantity> <Phone_Number> [Name/Address]`\n\n"
            "📌 *Examples:*\n"
            "• `/order 1 1 +8801711223344 Tariqul Islam`\n"
            "• `/order 2 2 +15550149921 Sarah Chen (Gift wrap)`\n\n"
            "💡 _Need to check item numbers? Send `/menu`_"
        )
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": guide,
            "parse_mode": "Markdown"
        })
        return

    try:
        item_id = int(parts[1])
        quantity = max(1, int(parts[2]))
        phone = parts[3]
        customer_info = parts[4] if len(parts) > 4 else user.get("first_name", "Customer")
    except ValueError:
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ *Invalid format.* Item Number and Quantity must be numbers.\nExample: `/order 1 1 +15550192834 John`",
            "parse_mode": "Markdown"
        })
        return

    product = next((p for p in CATALOG if p["id"] == item_id), None)
    if not product:
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": f"❌ *Item #{item_id} not found.* Please send `/menu` to view valid item numbers (1 - {len(CATALOG)}).",
            "parse_mode": "Markdown"
        })
        return

    total_price = product["price"] * quantity
    order_ref = f"ORD-{int(time.time()) % 100000:05d}"

    new_order = {
        "id": int(time.time() * 1000),
        "order_number": order_ref,
        "customer_name": customer_info,
        "phone_number": phone,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total_price": total_price,
        "status": "pending",
        "notes": f"Chat Order by {user.get('first_name', '')} (@{user.get('username', '')})",
        "telegram_user_id": str(user.get("id", "")),
        "telegram_username": str(user.get("username", "")),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    memory_orders.append(new_order)
    logger.info(f"New Order Created: {order_ref} by {customer_info}")

    # 1. Notify Customer in Chat
    customer_confirmation = (
        "✅ *ORDER RECEIVED SUCCESSFULLY!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Order Reference:* `{order_ref}`\n"
        f"📦 *Product:* {product['name']}\n"
        f"🔢 *Quantity:* {quantity} pc(s)\n"
        f"💰 *Total Amount:* ${total_price:.2f}\n"
        f"📞 *Phone:* `{phone}`\n"
        f"👤 *Customer:* {customer_info}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Our team has received your order and will contact you shortly to confirm delivery!"
    )
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": customer_confirmation,
        "parse_mode": "Markdown"
    })

    # 2. Dispatch Alert to Admin
    send_admin_alert(new_order)


def handle_admin(chat_id, user):
    """
    Handle /admin command:
    - If Admin: Sends the private Admin Mini App Launch Card with WebApp button.
    - If Regular User: Rejects access (Mini App is restricted).
    """
    user_id = user.get("id")
    username = user.get("username", "")
    first_name = user.get("first_name", "Admin")

    if not is_admin(user_id, chat_id):
        logger.warning(f"Unauthorized /admin attempt by User ID {user_id} (@{username})")
        rejection_text = (
            "🚫 *ACCESS RESTRICTED*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "The Mini App is reserved exclusively for Store Administrators.\n\n"
            "• Regular customers can place orders directly using `/menu` and `/order`.\n"
            f"• Your Telegram ID: `{user_id}`\n\n"
            "_(If you are the store owner, configure `ADMIN_TELEGRAM_ID` in your Render settings)_"
        )
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": rejection_text,
            "parse_mode": "Markdown"
        })
        return

    # Authorized Admin -> Send Exclusive Mini App Button
    logger.info(f"Authorized Admin {user_id} accessed /admin")
    admin_card_text = (
        f"🔐 *ADMIN CONTROL ACCESS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Welcome, {first_name}! (Admin Verified)*\n\n"
        "Tap the button below to launch the **Admin Control Mini App**:\n"
        "• View all live orders in real-time\n"
        "• Update order statuses (Pending/Processing/Delivered)\n"
        "• Test telegram alert notifications\n"
        "• Manage product catalog & pricing"
    )

    admin_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "⚡ Open Admin Control Mini App",
                    "web_app": {"url": WEB_APP_URL}
                }
            ],
            [
                {
                    "text": "📊 View Orders in Memory",
                    "callback_data": "admin_summary"
                }
            ]
        ]
    }

    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": admin_card_text,
        "parse_mode": "Markdown",
        "reply_markup": admin_keyboard
    })


def handle_help(chat_id):
    """Handle /help command."""
    text = (
        "ℹ️ *CUSTOMER SUPPORT & HELP*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to our Telegram Store!\n\n"
        "📦 *How to Order:*\n"
        "1. Send `/menu` to check products & prices\n"
        "2. Send `/order 1 1 +15550192834 Your Name` to place an order\n"
        "3. You will receive an instant confirmation\n\n"
        "💬 *Contact Admin:* Message directly in this chat for assistance."
    )
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


def handle_status(chat_id, user):
    """Handle /status command (Useful to find Chat ID for Admin configuration)."""
    user_id = user.get("id")
    is_adm = is_admin(user_id, chat_id)
    text = (
        "📍 *TELEGRAM ACCOUNT STATUS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Your User ID:* `{user_id}`\n"
        f"💬 *Current Chat ID:* `{chat_id}`\n"
        f"👤 *Username:* @{user.get('username', 'N/A')}\n"
        f"🛡️ *Role:* {'👑 Administrator' if is_adm else '👤 Regular Customer'}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "_(To configure this ID as Admin, set `ADMIN_TELEGRAM_ID` in Render settings)_"
    )
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


def process_update(update):
    """Dispatch incoming Telegram message or callback query."""
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        text = msg.get("text", "").strip()

        if not text or not chat_id:
            return

        logger.info(f"Incoming message from {user.get('id')} (@{user.get('username')}): {text}")

        if text.startswith("/start"):
            handle_start(chat_id, user)
        elif text.startswith("/menu"):
            handle_menu(chat_id)
        elif text.startswith("/order"):
            handle_order(chat_id, user, text)
        elif text.startswith("/admin"):
            handle_admin(chat_id, user)
        elif text.startswith("/help"):
            handle_help(chat_id)
        elif text.startswith("/status"):
            handle_status(chat_id, user)
        else:
            telegram_api("sendMessage", {
                "chat_id": chat_id,
                "text": "🤖 Send `/menu` to browse products or `/order` to buy. Type `/help` for guidance.",
                "parse_mode": "Markdown"
            })

    elif "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        user = cb.get("from", {})
        data = cb.get("data", "")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")

        if data == "admin_summary" and chat_id:
            if is_admin(user.get("id"), chat_id):
                cnt = len(memory_orders)
                rev = sum(o.get("total_price", 0) for o in memory_orders)
                telegram_api("answerCallbackQuery", {
                    "callback_query_id": cb_id,
                    "text": f"📊 Total Orders: {cnt} | Revenue: ${rev:.2f}",
                    "show_alert": True
                })
            else:
                telegram_api("answerCallbackQuery", {
                    "callback_query_id": cb_id,
                    "text": "Access restricted to admin only.",
                    "show_alert": True
                })


def run_polling():
    """Main polling loop for Render Background Worker."""
    if not BOT_TOKEN:
        logger.error("=" * 60)
        logger.error("CRITICAL: TELEGRAM_BOT_TOKEN is not set.")
        logger.error("Please add TELEGRAM_BOT_TOKEN in Render Environment Variables.")
        logger.error("=" * 60)
        # Sleep loop to prevent fast crashing on Render
        while True:
            time.sleep(60)

    logger.info("=" * 60)
    logger.info("🚀 Starting Telegram Bot Worker (Render Compatible)...")
    logger.info(f"🌐 Web App URL (Admin Only): {WEB_APP_URL}")
    logger.info(f"👑 Admin ID: {ADMIN_TELEGRAM_ID or 'Not Set'}")
    logger.info("=" * 60)

    # Configure bot commands
    try:
        setup_bot_commands()
    except Exception as e:
        logger.error(f"Error initializing commands: {e}")

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 25}
            res = requests.get(url, params=params, timeout=30)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        process_update(update)
                else:
                    logger.warning(f"Telegram getUpdates returned not ok: {data}")
                    time.sleep(3)
            else:
                logger.warning(f"Telegram getUpdates HTTP {res.status_code}")
                time.sleep(3)

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            logger.warning("Network connection issue. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_polling()
