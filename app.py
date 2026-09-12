#!/usr/bin/env python3
"""
Render Webhook-First & Polling Telegram Store Server
---------------------------------------------------
1. Webhook Mode: Listens to incoming Telegram updates on /webhook & /api/telegram/webhook.
2. Background Polling: Fallback poller running continuously.
3. Completely removes Mini App for regular users (Chat-only /start, /menu, /order).
4. Only verified Admins get the Admin Mini App Card via /admin.
5. Admins can grant/revoke Mini App access by Telegram User ID (/grant <id>, /revoke <id>).
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

logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("telegram_app")

app = Flask(__name__, static_folder=".")

PORT = int(os.getenv("PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://hello-world-fcg3.onrender.com").strip()

# Authorized admin IDs
authorized_admins = set()
if ADMIN_TELEGRAM_ID:
    for aid in ADMIN_TELEGRAM_ID.split(","):
        cid = aid.strip()
        if cid:
            authorized_admins.add(cid)
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
memory_orders = []


def telegram_api(method, payload=None):
    token = TELEGRAM_BOT_TOKEN
    if not token:
        logger.error(f"Cannot call {method}: TELEGRAM_BOT_TOKEN is empty!")
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN is missing"}
    
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        res = requests.post(url, json=payload or {}, timeout=12)
        data = res.json()
        if not data.get("ok"):
            logger.warning(f"Telegram API {method} returned not OK: {data}")
        return data
    except Exception as e:
        logger.error(f"Telegram API {method} error: {e}")
        return {"ok": False, "error": str(e)}


def init_bot_policy_and_remove_miniapp():
    """Removes the persistent 'Shop' / Mini App button for all regular users."""
    logger.info("Enforcing Chat-Only policy: removing global Mini App button...")
    
    # 1. Reset Global Chat Menu Button to default (removes 'Shop' button for standard users)
    telegram_api("setChatMenuButton", {"menu_button": {"type": "default"}})
    
    # 2. Register Chat Commands
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
    """Processes incoming Telegram message or button click."""
    if not update:
        return

    msg = update.get("message")
    if not msg:
        return

    chat_id = msg.get("chat", {}).get("id")
    user = msg.get("from", {})
    user_id = user.get("id")
    user_name = user.get("first_name", "Customer")
    username = user.get("username", "")
    text = (msg.get("text") or "").strip()

    if not text or not chat_id:
        return

    logger.info(f"📩 Processing command from {user_id} (@{username}): {text}")

    # Remove any cached Mini App button for regular users
    if not is_user_admin(user_id, chat_id):
        telegram_api("setChatMenuButton", {
            "chat_id": chat_id,
            "menu_button": {"type": "default"}
        })

    if text.startswith("/start"):
        start_msg = (
            f"👋 *Welcome to our Store, {user_name}!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Browse our products and place orders directly inside this chat.\n\n"
            "🛍️ *Quick Commands:*\n"
            "• `/menu` — View product catalog & prices\n"
            "• `/order` — Place an order directly via message\n"
            "• `/help` — How to order & support details\n"
            "• `/status` — View your Telegram ID\n\n"
            "👉 Send `/menu` to explore available products!"
        )
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": start_msg,
            "parse_mode": "Markdown"
        })

    elif text.startswith("/menu"):
        lines = ["🛍️ *PRODUCT CATALOG (ORDER IN CHAT)*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for idx, p in enumerate(memory_products, 1):
            lines.append(
                f"*{idx}. {p['name']}*\n"
                f"💰 Price: *${p['price']:.2f}*\n"
                f"ℹ️ _{p.get('description', '')}_"
            )
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(
            "👉 *To place an order, send:*\n"
            "`/order <Item_No> <Qty> <Phone> <Your_Name>`\n\n"
            "_Example:_\n"
            "`/order 1 1 +8801700000000 Alex`"
        )
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": "\n\n".join(lines),
            "parse_mode": "Markdown"
        })

    elif text.startswith("/order"):
        parts = text.split(maxsplit=4)
        if len(parts) < 4:
            guide = (
                "📦 *How to Order in Chat:*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Please send the `/order` command in this format:\n\n"
                "`/order <Item_Number> <Quantity> <Phone_Number> [Name]`\n\n"
                "📌 *Example:* `/order 1 1 +15550192834 Tariqul Islam`\n"
                "💡 _Send `/menu` to check item numbers._"
            )
            telegram_api("sendMessage", {
                "chat_id": chat_id,
                "text": guide,
                "parse_mode": "Markdown"
            })
            return

        try:
            item_idx = int(parts[1]) - 1
            qty = max(1, int(parts[2]))
            phone = parts[3]
            cust_name = parts[4] if len(parts) > 4 else user_name
        except ValueError:
            telegram_api("sendMessage", {
                "chat_id": chat_id,
                "text": "❌ *Invalid format.* Number and Quantity must be digits.\n_Example:_ `/order 1 1 +15550192834 John`",
                "parse_mode": "Markdown"
            })
            return

        if item_idx < 0 or item_idx >= len(memory_products):
            telegram_api("sendMessage", {
                "chat_id": chat_id,
                "text": f"❌ Item #{parts[1]} not found. Send `/menu` to view items (1 to {len(memory_products)}).",
                "parse_mode": "Markdown"
            })
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
        logger.info(f"New Order Created: {ref_id} for {cust_name}")

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
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": conf_msg,
            "parse_mode": "Markdown"
        })

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
            telegram_api("sendMessage", {
                "chat_id": chat_id,
                "text": rejection,
                "parse_mode": "Markdown"
            })
            return

        # Enable admin menu button
        telegram_api("setChatMenuButton", {
            "chat_id": chat_id,
            "menu_button": {
                "type": "web_app",
                "text": "Admin App",
                "web_app": {"url": WEB_APP_URL}
            }
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
        kb = {
            "inline_keyboard": [
                [{"text": "⚡ Open Admin Control Mini App", "web_app": {"url": WEB_APP_URL}}]
            ]
        }
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": card,
            "parse_mode": "Markdown",
            "reply_markup": kb
        })

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


# ================= POLLING WORKER THREAD =================
def run_poller_thread():
    logger.info("🤖 Starting Telegram Poller Loop in background...")
    time.sleep(2)
    init_bot_policy_and_remove_miniapp()

    offset = 0
    while True:
        token = TELEGRAM_BOT_TOKEN
        if not token:
            time.sleep(5)
            continue

        try:
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
                            logger.error(f"Error handling update: {e}")
                else:
                    time.sleep(3)
            else:
                time.sleep(3)
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Polling loop exception: {e}")
            time.sleep(4)


# Start background thread immediately
t = threading.Thread(target=run_poller_thread, daemon=True)
t.start()


# ================= WEB ROUTES =================

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/health")
@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "has_token": bool(TELEGRAM_BOT_TOKEN),
        "authorized_admins": list(authorized_admins),
        "orders": len(memory_orders)
    })


# Telegram Webhook listener
@app.route("/webhook", methods=["POST", "GET"])
@app.route("/api/telegram/webhook", methods=["POST", "GET"])
def webhook_handler():
    if request.method == "GET":
        return jsonify({"status": "Telegram webhook endpoint ready"})
    data = request.get_json(silent=True) or {}
    if data:
        process_telegram_update(data)
    return jsonify({"ok": True})


# Automatic Webhook Setter Endpoint
@app.route("/api/set-webhook", methods=["GET", "POST"])
def set_webhook_api():
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN missing"}), 400
    host_url = request.host_url.rstrip('/')
    # If on Render, prefer https
    if "onrender.com" in host_url and host_url.startswith("http://"):
        host_url = host_url.replace("http://", "https://")
    webhook_target = f"{host_url}/webhook"
    
    res = telegram_api("setWebhook", {"url": webhook_target})
    init_bot_policy_and_remove_miniapp()
    return jsonify({"success": res.get("ok", False), "webhook_url": webhook_target, "telegram_response": res})


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
        "authorized_admins": list(authorized_admins)
    })


if __name__ == "__main__":
    logger.info(f"🚀 Starting App Server on port {PORT}...")
    app.run(host=HOST, port=PORT, debug=False)
