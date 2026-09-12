#!/usr/bin/env python3
"""
Single-Service Full Web + Telegram Bot Webhook & Poller
-------------------------------------------------------
Runs Flask Web Server (Admin Mini App & REST APIs) AND handles
Telegram Bot updates in real-time (no separate worker required).
"""

import os
import sys
import time
import json
import logging
import threading
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("telegram_app")

app = Flask(__name__, static_folder=".")

# Configuration
PORT = int(os.getenv("PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://hello-world-fcg3.onrender.com").strip()

# Dynamic in-memory list of authorized admin Telegram user IDs
authorized_admins = set()
if ADMIN_TELEGRAM_ID:
    for aid in ADMIN_TELEGRAM_ID.split(","):
        clean_id = aid.strip()
        if clean_id:
            authorized_admins.add(clean_id)
if TELEGRAM_CHAT_ID:
    authorized_admins.add(TELEGRAM_CHAT_ID.strip())

# In-memory products
memory_products = [
    {
        "id": "prod-1",
        "name": "Wireless Noise-Cancelling Earbuds",
        "category": "Audio",
        "price": 49.99,
        "stock": 25,
        "image": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&auto=format&fit=crop&q=80",
        "badge": "Best Seller",
        "description": "Active noise cancelling with 28-hour battery life and waterproof build."
    },
    {
        "id": "prod-2",
        "name": "Vintage Mechanical Keyboard RGB",
        "category": "Workplace",
        "price": 89.50,
        "stock": 14,
        "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=300&auto=format&fit=crop&q=80",
        "badge": "Popular",
        "description": "Custom mechanical switches with per-key RGB backlighting and aluminum body."
    },
    {
        "id": "prod-3",
        "name": "Smart Fitness Tracker Band",
        "category": "Wearables",
        "price": 34.99,
        "stock": 30,
        "image": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=300&auto=format&fit=crop&q=80",
        "badge": "New Arrival",
        "description": "24/7 heart rate monitor, sleep analysis, SpO2 sensor and 14-day battery."
    },
    {
        "id": "prod-4",
        "name": "Ultra-light Commuter Backpack",
        "category": "Accessories",
        "price": 59.00,
        "stock": 18,
        "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&auto=format&fit=crop&q=80",
        "badge": "Waterproof",
        "description": "Ergonomic waterproof backpack with padded 16-inch laptop compartment."
    }
]

# In-memory orders
memory_orders = [
    {
        "id": 1001,
        "order_number": "ORD-2026-001",
        "customer_name": "Alex Morgan",
        "phone_number": "+1 (555) 019-2834",
        "product_name": "Wireless Noise-Cancelling Earbuds",
        "quantity": 1,
        "unit_price": 49.99,
        "total_price": 49.99,
        "status": "delivered",
        "notes": "Please leave package at front reception.",
        "source": "Telegram Chat Bot (/order)",
        "telegram_user_id": "78239102",
        "telegram_username": "alex_morgan",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(time.time() - 86400))
    },
    {
        "id": 1002,
        "order_number": "ORD-2026-002",
        "customer_name": "Sarah Chen",
        "phone_number": "+1 (555) 014-9921",
        "product_name": "Vintage Mechanical Keyboard RGB",
        "quantity": 2,
        "unit_price": 89.50,
        "total_price": 179.00,
        "status": "processing",
        "notes": "Gift packaging requested with blue ribbon.",
        "source": "Telegram Chat Bot (/order)",
        "telegram_user_id": "89123041",
        "telegram_username": "sarah_c",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(time.time() - 14400))
    }
]


# ================= TELEGRAM HELPER FUNCTIONS =================

def telegram_api(method, payload=None):
    token = TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        res = requests.post(url, json=payload or {}, timeout=15)
        return res.json()
    except Exception as e:
        logger.error(f"Telegram API {method} error: {e}")
        return {"ok": False, "error": str(e)}


def remove_global_miniapp():
    """Removes the persistent 'Shop' Mini App button for all regular users."""
    logger.info("Enforcing chat-only policy & removing global Mini App button...")
    telegram_api("setChatMenuButton", {"menu_button": {"type": "default"}})
    telegram_api("setMyCommands", {
        "commands": [
            {"command": "start", "description": "👋 Start bot & store menu"},
            {"command": "menu", "description": "🛍️ View products & prices"},
            {"command": "order", "description": "📦 Order: /order <id> <qty> <phone> <name>"},
            {"command": "help", "description": "ℹ️ Support & guide"},
            {"command": "status", "description": "📍 Check Telegram User ID"}
        ]
    })


def is_user_admin(user_id, chat_id=None):
    uid = str(user_id).strip()
    cid = str(chat_id).strip() if chat_id else ""
    if uid in authorized_admins or cid in authorized_admins:
        return True
    if ADMIN_TELEGRAM_ID and (uid == ADMIN_TELEGRAM_ID or cid == ADMIN_TELEGRAM_ID):
        return True
    if TELEGRAM_CHAT_ID and (uid == TELEGRAM_CHAT_ID or cid == TELEGRAM_CHAT_ID):
        return True
    return False


def process_telegram_update(update):
    """Core logic to process incoming messages & commands."""
    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg.get("chat", {}).get("id")
    user = msg.get("from", {})
    user_id = user.get("id")
    user_name = user.get("first_name", "Customer")
    username = user.get("username", "")
    text = msg.get("text", "").strip()

    if not text or not chat_id:
        return

    logger.info(f"Telegram message received from {user_id} (@{username}): {text}")

    # Reset any cached menu button for regular user
    if not is_user_admin(user_id, chat_id):
        telegram_api("setChatMenuButton", {"chat_id": chat_id, "menu_button": {"type": "default"}})

    if text.startswith("/start"):
        start_msg = (
            f"👋 *Welcome to our Store, {user_name}!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "You can browse our products and place orders directly in this chat.\n\n"
            "🛍️ *Quick Commands:*\n"
            "• `/menu` — View full product catalog & prices\n"
            "• `/order` — Order an item directly via chat\n"
            "• `/help` — Help and support guide\n"
            "• `/status` — View your Telegram ID\n\n"
            "👉 Send `/menu` to see available products!"
        )
        telegram_api("sendMessage", {"chat_id": chat_id, "text": start_msg, "parse_mode": "Markdown"})

    elif text.startswith("/menu"):
        lines = ["🛍️ *PRODUCT CATALOG (ORDER IN CHAT)*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for idx, p in enumerate(memory_products, 1):
            lines.append(f"*{idx}. {p['name']}*\n💰 Price: *${p['price']:.2f}*\nℹ️ _{p.get('description', '')}_")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("👉 *To place an order, send:*\n`/order <Item_No> <Qty> <Phone> <Your_Name>`\n\n_Example:_\n`/order 1 1 +8801700000000 Alex`")
        telegram_api("sendMessage", {"chat_id": chat_id, "text": "\n\n".join(lines), "parse_mode": "Markdown"})

    elif text.startswith("/order"):
        parts = text.split(maxsplit=4)
        if len(parts) < 4:
            guide = (
                "📦 *How to Order in Chat:*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Please send the `/order` command like this:\n\n"
                "`/order <Item_Number> <Quantity> <Phone_Number> [Name]`\n\n"
                "📌 *Example:* `/order 1 1 +15550192834 Tariqul Islam`\n"
                "💡 _Send `/menu` to check item numbers._"
            )
            telegram_api("sendMessage", {"chat_id": chat_id, "text": guide, "parse_mode": "Markdown"})
            return

        try:
            item_idx = int(parts[1]) - 1
            qty = max(1, int(parts[2]))
            phone = parts[3]
            cust_name = parts[4] if len(parts) > 4 else user_name
        except ValueError:
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "❌ Invalid number format. Example: `/order 1 1 +15550192834 John`", "parse_mode": "Markdown"})
            return

        if item_idx < 0 or item_idx >= len(memory_products):
            telegram_api("sendMessage", {"chat_id": chat_id, "text": f"❌ Item #{parts[1]} not found. Send `/menu` to view items 1 to {len(memory_products)}.", "parse_mode": "Markdown"})
            return

        prod = memory_products[item_idx]
        total_price = prod["price"] * qty
        ref_id = f"ORD-{int(time.time()) % 100000:05d}"

        new_order = {
            "id": int(time.time() * 1000),
            "order_number": ref_id,
            "customer_name": cust_name,
            "phone_number": phone,
            "product_name": prod["name"],
            "quantity": qty,
            "unit_price": prod["price"],
            "total_price": total_price,
            "status": "pending",
            "notes": f"Chat Order by {user_name} (@{username})",
            "source": "Telegram Chat Bot (/order)",
            "telegram_user_id": str(user_id),
            "telegram_username": username,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
        }

        memory_orders.insert(0, new_order)
        logger.info(f"New Order: {ref_id} for {cust_name}")

        # Send confirmation to user
        conf_msg = (
            "✅ *ORDER RECEIVED SUCCESSFULLY!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 *Order Ref:* `{ref_id}`\n"
            f"📦 *Product:* {prod['name']}\n"
            f"🔢 *Quantity:* {qty} pc(s)\n"
            f"💰 *Total Amount:* ${total_price:.2f}\n"
            f"📞 *Phone:* `{phone}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Thank you! Our team will contact you shortly to confirm delivery."
        )
        telegram_api("sendMessage", {"chat_id": chat_id, "text": conf_msg, "parse_mode": "Markdown"})

        # Send alert to Admin
        send_admin_alert_all(new_order)

    elif text.startswith("/admin"):
        if not is_user_admin(user_id, chat_id):
            rejection = (
                "🚫 *ACCESS RESTRICTED*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "The Mini App is reserved for Store Administrators.\n"
                "Regular customers can order using `/menu` and `/order`.\n\n"
                f"Your Telegram ID: `{user_id}`"
            )
            telegram_api("sendMessage", {"chat_id": chat_id, "text": rejection, "parse_mode": "Markdown"})
            return

        # Enable admin menu button
        telegram_api("setChatMenuButton", {
            "chat_id": chat_id,
            "menu_button": {"type": "web_app", "text": "Admin App", "web_app": {"url": WEB_APP_URL}}
        })

        card = (
            f"🔐 *ADMIN CONTROL PANEL*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 *Welcome, {user_name}! (Admin Verified)*\n\n"
            "Tap the button below to launch the **Admin Control Mini App**:\n"
            "• Manage live customer orders\n"
            "• Change delivery statuses\n\n"
            "🛠️ *Admin Commands:*\n"
            "• `/grant <id>` — Enable Mini App for another user\n"
            "• `/revoke <id>` — Remove Mini App access\n"
            "• `/admins` — View list of admins"
        )
        kb = {"inline_keyboard": [[{"text": "⚡ Open Admin Control Mini App", "web_app": {"url": WEB_APP_URL}}]]}
        telegram_api("sendMessage", {"chat_id": chat_id, "text": card, "parse_mode": "Markdown", "reply_markup": kb})

    elif text.startswith("/grant"):
        if not is_user_admin(user_id, chat_id):
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "🚫 Admin only command.", "parse_mode": "Markdown"})
            return
        parts = text.split()
        if len(parts) < 2:
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "📌 Usage: `/grant <telegram_user_id>`", "parse_mode": "Markdown"})
            return
        target = parts[1].strip()
        authorized_admins.add(target)
        telegram_api("setChatMenuButton", {
            "chat_id": target,
            "menu_button": {"type": "web_app", "text": "Admin App", "web_app": {"url": WEB_APP_URL}}
        })
        telegram_api("sendMessage", {"chat_id": chat_id, "text": f"✅ Granted Admin Mini App access to Telegram ID `{target}`.", "parse_mode": "Markdown"})
        telegram_api("sendMessage", {"chat_id": target, "text": "🎉 You have been granted Admin Access! Use `/admin` to launch.", "parse_mode": "Markdown"})

    elif text.startswith("/revoke"):
        if not is_user_admin(user_id, chat_id):
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "🚫 Admin only command.", "parse_mode": "Markdown"})
            return
        parts = text.split()
        if len(parts) < 2:
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "📌 Usage: `/revoke <telegram_user_id>`", "parse_mode": "Markdown"})
            return
        target = parts[1].strip()
        if target in authorized_admins:
            authorized_admins.remove(target)
            telegram_api("setChatMenuButton", {"chat_id": target, "menu_button": {"type": "default"}})
            telegram_api("sendMessage", {"chat_id": chat_id, "text": f"🚫 Revoked Admin access for `{target}`.", "parse_mode": "Markdown"})

    elif text.startswith("/admins"):
        if not is_user_admin(user_id, chat_id):
            telegram_api("sendMessage", {"chat_id": chat_id, "text": "🚫 Admin only command.", "parse_mode": "Markdown"})
            return
        lines = ["👑 *AUTHORIZED ADMIN IDS:*"] + [f"• `{a}`" for a in authorized_admins]
        telegram_api("sendMessage", {"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "Markdown"})

    elif text.startswith("/status"):
        is_adm = is_user_admin(user_id, chat_id)
        stat = (
            "📍 *TELEGRAM ACCOUNT STATUS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Your User ID:* `{user_id}`\n"
            f"💬 *Chat ID:* `{chat_id}`\n"
            f"👤 *Username:* @{username or 'N/A'}\n"
            f"🛡️ *Role:* {'👑 Administrator (Mini App Enabled)' if is_adm else '👤 Regular Customer (Chat Only)'}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        telegram_api("sendMessage", {"chat_id": chat_id, "text": stat, "parse_mode": "Markdown"})

    elif text.startswith("/help"):
        help_text = (
            "ℹ️ *CUSTOMER SUPPORT & HELP*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. Send `/menu` to check products\n"
            "2. Send `/order 1 1 +15550192834 Name` to order\n"
            "3. We will process and confirm your order promptly!"
        )
        telegram_api("sendMessage", {"chat_id": chat_id, "text": help_text, "parse_mode": "Markdown"})


def send_admin_alert_all(order):
    targets = list(authorized_admins) if authorized_admins else ([ADMIN_TELEGRAM_ID or TELEGRAM_CHAT_ID] if (ADMIN_TELEGRAM_ID or TELEGRAM_CHAT_ID) else [])
    if not targets:
        return

    qty = order.get("quantity", 1)
    total = f"{float(order.get('total_price', 0)):.2f}"
    text = (
        "🔔 *NEW ORDER ALERT (ADMIN ONLY)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Order Ref:* `{order.get('order_number')}`\n"
        f"👤 *Customer:* *{order.get('customer_name')}*\n"
        f"📞 *Phone:* `{order.get('phone_number')}`\n"
        f"📦 *Product:* *{order.get('product_name')}*\n"
        f"🔢 *Quantity:* {qty} unit(s)\n"
        f"💰 *Total Amount:* ${total}\n"
        f"🕒 *Time:* {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ _Manage in Admin Mini App: /admin_"
    )
    for t in targets:
        telegram_api("sendMessage", {"chat_id": t, "text": text, "parse_mode": "Markdown"})


# ================= BACKGROUND BOT POLLING THREAD =================
bot_thread_started = False

def start_bot_background_poller():
    global bot_thread_started
    if bot_thread_started:
        return
    bot_thread_started = True

    def poller_loop():
        logger.info("🤖 Starting Integrated Telegram Bot Background Poller inside Flask Web Service...")
        time.sleep(2)
        remove_global_miniapp()

        offset = 0
        while True:
            try:
                token = TELEGRAM_BOT_TOKEN
                if not token:
                    time.sleep(10)
                    continue

                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": offset, "timeout": 20}
                res = requests.get(url, params=params, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        for upd in data.get("result", []):
                            offset = upd["update_id"] + 1
                            try:
                                process_telegram_update(upd)
                            except Exception as e:
                                logger.error(f"Error processing update: {e}")
                    else:
                        time.sleep(3)
                else:
                    time.sleep(3)
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                logger.error(f"Poller exception: {e}")
                time.sleep(4)

    t = threading.Thread(target=poller_loop, daemon=True)
    t.start()


# Launch polling thread immediately on module load
if TELEGRAM_BOT_TOKEN:
    start_bot_background_poller()


# ================= FLASK WEB ROUTES & WEBHOOKS =================

@app.route("/")
def index():
    if not bot_thread_started and TELEGRAM_BOT_TOKEN:
        start_bot_background_poller()
    return send_from_directory(".", "index.html")


@app.route("/api/health")
@app.route("/health")
def health():
    if not bot_thread_started and TELEGRAM_BOT_TOKEN:
        start_bot_background_poller()
    return jsonify({
        "status": "healthy",
        "system": "Integrated Telegram Bot & Admin Mini App (Render Web Service)",
        "poller_running": bot_thread_started,
        "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
        "has_chat_id": bool(TELEGRAM_CHAT_ID),
        "has_admin_id": bool(ADMIN_TELEGRAM_ID),
        "authorized_admins": list(authorized_admins),
        "orders_count": len(memory_orders)
    })


# Telegram Webhook endpoint (Alternative to polling)
@app.route("/api/telegram/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    if update:
        process_telegram_update(update)
    return jsonify({"ok": True})


@app.route("/api/admin/verify", methods=["POST"])
def verify_admin():
    global ADMIN_PIN
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()
    tg_user_id = str(data.get("telegram_user_id", "")).strip()

    if pin and pin == str(ADMIN_PIN).strip():
        return jsonify({"success": True, "isAdmin": True, "message": "PIN verified"})
    if tg_user_id and is_user_admin(tg_user_id):
        return jsonify({"success": True, "isAdmin": True, "message": f"Telegram ID {tg_user_id} verified"})

    return jsonify({"success": False, "isAdmin": False, "error": "Access Denied"}), 403


@app.route("/api/admin/config", methods=["GET", "POST"])
def admin_config():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_TELEGRAM_ID, ADMIN_PIN
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "bot_token" in data:
            TELEGRAM_BOT_TOKEN = str(data["bot_token"]).strip()
        if "chat_id" in data:
            TELEGRAM_CHAT_ID = str(data["chat_id"]).strip()
            if TELEGRAM_CHAT_ID:
                authorized_admins.add(TELEGRAM_CHAT_ID)
        if "admin_telegram_id" in data:
            ADMIN_TELEGRAM_ID = str(data["admin_telegram_id"]).strip()
            if ADMIN_TELEGRAM_ID:
                authorized_admins.add(ADMIN_TELEGRAM_ID)
        if "admin_pin" in data and str(data["admin_pin"]).strip():
            ADMIN_PIN = str(data["admin_pin"]).strip()

        # Start poller if token provided
        if TELEGRAM_BOT_TOKEN and not bot_thread_started:
            start_bot_background_poller()

        return jsonify({"success": True, "authorized_admins": list(authorized_admins)})

    masked = ""
    if TELEGRAM_BOT_TOKEN:
        p = TELEGRAM_BOT_TOKEN.split(":")
        masked = f"{p[0]}:***" if len(p) > 1 else "***"

    return jsonify({
        "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
        "has_chat_id": bool(TELEGRAM_CHAT_ID),
        "has_admin_id": bool(ADMIN_TELEGRAM_ID),
        "bot_token_masked": masked,
        "chat_id": TELEGRAM_CHAT_ID,
        "admin_telegram_id": ADMIN_TELEGRAM_ID,
        "authorized_admins": list(authorized_admins),
        "admin_pin_configured": bool(ADMIN_PIN)
    })


@app.route("/api/setup-bot-commands", methods=["POST"])
def setup_commands_route():
    remove_global_miniapp()
    return jsonify({"success": True, "message": "Global Mini App button removed and chat commands set."})


@app.route("/api/products", methods=["GET", "POST"])
def products_route():
    return jsonify({"success": True, "products": memory_products})


@app.route("/api/orders", methods=["GET", "POST", "DELETE"])
def orders_route():
    global memory_orders
    if request.method == "GET":
        return jsonify({
            "success": True,
            "orders": memory_orders,
            "stats": {
                "pending": len([o for o in memory_orders if o.get("status") == "pending"]),
                "delivered": len([o for o in memory_orders if o.get("status") == "delivered"]),
                "total_revenue": sum(float(o.get("total_price", 0)) for o in memory_orders)
            }
        })
    if request.method == "DELETE":
        memory_orders = []
        return jsonify({"success": True})


@app.route("/api/order/<int:order_id>/status", methods=["PATCH"])
def update_status(order_id):
    data = request.get_json(silent=True) or {}
    st = data.get("status", "pending")
    for o in memory_orders:
        if o["id"] == order_id:
            o["status"] = st
            return jsonify({"success": True, "order": o})
    return jsonify({"success": False, "error": "Not found"}), 404


@app.route("/api/test-telegram", methods=["POST"])
def test_telegram_alert():
    target = ADMIN_TELEGRAM_ID or TELEGRAM_CHAT_ID
    if not target or not TELEGRAM_BOT_TOKEN:
        return jsonify({"success": False, "error": "Bot token or Chat ID missing."})

    res = telegram_api("sendMessage", {
        "chat_id": target,
        "text": "🔔 *Test Alert from Python Backend (Render Web Service)*\nBot is active and ready to deliver customer orders!",
        "parse_mode": "Markdown"
    })
    return jsonify({"success": res.get("ok", False), "result": res})


if __name__ == "__main__":
    start_bot_background_poller()
    logger.info(f"🚀 Running Web & Bot Service on port {PORT}")
    app.run(host=HOST, port=PORT, debug=False)
