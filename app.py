"""
E-Commerce Order System - Backend Server (Flask)
Ready for deployment on Render, Vercel, or local execution.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import database

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
PORT = int(os.getenv("PORT", 3000))

def format_telegram_alert(order):
    """Formats a sleek Markdown Telegram notification message for a new order."""
    source_badge = "📱 Telegram Mini App" if order.get("is_telegram_webapp") else "🌐 Standard Web Browser"
    username_line = f"\n👤 *Telegram User:* @{order['telegram_username']}" if order.get("telegram_username") else ""
    user_id_line = f" (ID: `{order['telegram_user_id']}`)" if order.get("telegram_user_id") else ""
    notes_line = f"\n📝 *Notes:* _{order['notes']}_" if order.get("notes") else ""
    total = order.get("total_price", 0.0)
    qty = order.get("quantity", 1)
    
    message = (
        "🛒 *NEW ORDER RECEIVED!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Order Ref:* `{order.get('order_number', 'N/A')}`\n"
        f"👤 *Customer:* {order.get('customer_name', 'N/A')}\n"
        f"📞 *Phone:* `{order.get('phone_number', 'N/A')}`\n"
        f"📦 *Item:* *{order.get('product_name', 'N/A')}*\n"
        f"🔢 *Quantity:* {qty} pc{'s' if int(qty) > 1 else ''}\n"
        f"💰 *Total Amount:* ${float(total):.2f}\n"
        f"🏷️ *Source:* {source_badge}"
        f"{username_line}{user_id_line}"
        f"{notes_line}\n"
        f"🕒 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ _Processed via Telegram E-Commerce System_"
    )
    return message

def send_telegram_alert(order, bot_token=None, chat_id=None):
    """
    Sends an alert message to a specified Telegram Group/Channel or user
    using the official Telegram Bot API (HTTP REST).
    Uses standard library urllib so it works in any Python runtime without extra dependencies.
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_CHAT_ID

    if not token or not target_chat:
        return {
            "success": False, 
            "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.",
            "simulated": True,
            "preview_message": format_telegram_alert(order)
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": format_telegram_alert(order),
        "parse_mode": "Markdown"
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            if res_json.get("ok"):
                database.mark_alert_sent(order.get("id"))
                return {"success": True, "result": res_json}
            else:
                return {"success": False, "error": res_json.get("description", "Unknown Telegram error")}
    except Exception as e:
        return {"success": False, "error": str(e), "preview_message": format_telegram_alert(order)}

# Initialize database tables on startup
database.init_db()

# Check if Flask is installed; if yes, define Flask app
try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS

    app = Flask(__name__, static_folder="dist", static_url_path="")
    CORS(app)

    @app.route("/api/order", methods=["POST"])
    @app.route("/api/orders", methods=["POST"])
    def place_order():
        try:
            data = request.get_json(force=True, silent=True) or {}
            customer_name = data.get("customer_name")
            phone_number = data.get("phone_number")
            product_name = data.get("product_name")
            quantity = data.get("quantity", 1)

            if not customer_name or not phone_number or not product_name:
                return jsonify({
                    "success": False, 
                    "error": "Missing required fields: customer_name, phone_number, and product_name are required."
                }), 400

            unit_price = float(data.get("unit_price", 0.0))
            total_price = float(data.get("total_price", 0.0))
            if total_price == 0.0 and unit_price > 0.0:
                total_price = unit_price * int(quantity)

            notes = data.get("notes", "")
            is_tg = 1 if data.get("is_telegram_webapp") else 0
            tg_uid = str(data.get("telegram_user_id", ""))
            tg_uname = str(data.get("telegram_username", ""))

            # Save to SQLite database
            order = database.create_order(
                customer_name=customer_name,
                phone_number=phone_number,
                product_name=product_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                notes=notes,
                is_telegram_webapp=is_tg,
                telegram_user_id=tg_uid,
                telegram_username=tg_uname
            )

            # Send Telegram Alert
            tg_result = send_telegram_alert(order)

            return jsonify({
                "success": True,
                "message": "Order placed successfully!",
                "order": order,
                "telegram": tg_result
            }), 201

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/orders", methods=["GET"])
    def list_orders():
        try:
            orders = database.get_all_orders()
            return jsonify({"success": True, "orders": orders})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/order/<int:order_id>/status", methods=["PATCH"])
    def update_status(order_id):
        try:
            data = request.get_json(force=True, silent=True) or {}
            new_status = data.get("status", "pending")
            database.update_order_status(order_id, new_status)
            return jsonify({"success": True, "message": f"Order #{order_id} status updated to {new_status}"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/config", methods=["GET", "POST"])
    def bot_config():
        global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            if "bot_token" in data:
                TELEGRAM_BOT_TOKEN = data["bot_token"].strip()
            if "chat_id" in data:
                TELEGRAM_CHAT_ID = data["chat_id"].strip()
            return jsonify({"success": True, "message": "Configuration updated"})

        token_masked = ""
        if TELEGRAM_BOT_TOKEN:
            parts = TELEGRAM_BOT_TOKEN.split(":")
            token_masked = f"{parts[0]}:***" if len(parts) > 1 else "***"

        return jsonify({
            "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
            "has_chat_id": bool(TELEGRAM_CHAT_ID),
            "bot_token_masked": token_masked,
            "chat_id": TELEGRAM_CHAT_ID
        })

    @app.route("/api/test-telegram", methods=["POST"])
    def test_telegram():
        data = request.get_json(force=True, silent=True) or {}
        custom_token = data.get("bot_token") or TELEGRAM_BOT_TOKEN
        custom_chat = data.get("chat_id") or TELEGRAM_CHAT_ID

        test_order = {
            "id": 9999,
            "order_number": "TEST-DEMO-001",
            "customer_name": "Test Customer",
            "phone_number": "+1 (555) 019-2834",
            "product_name": "Test Product Sample",
            "quantity": 1,
            "unit_price": 25.00,
            "total_price": 25.00,
            "notes": "Testing Telegram Bot Alert integration.",
            "is_telegram_webapp": 1,
            "telegram_user_id": "123456789",
            "telegram_username": "test_bot_user",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        res = send_telegram_alert(test_order, bot_token=custom_token, chat_id=custom_chat)
        return jsonify(res)

    @app.route("/api/webhook", methods=["GET", "POST"])
    @app.route("/webhook", methods=["GET", "POST"])
    def telegram_webhook():
        """
        Receives Telegram Bot webhook updates.
        Handles /start, /orders, and /help directly without needing a separate polling process.
        """
        if request.method == "GET":
            return jsonify({
                "status": "Telegram webhook listening",
                "has_token": bool(TELEGRAM_BOT_TOKEN),
                "instructions": "Send Telegram updates via POST to this endpoint or configure via setWebhook."
            })

        update = request.get_json(force=True, silent=True) or {}
        message = update.get("message") or update.get("edited_message")
        if not message:
            return jsonify({"ok": True, "note": "No message in update"})

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        user = message.get("from", {})
        first_name = user.get("first_name", "Customer")
        username = user.get("username", "")
        user_id = str(user.get("id", ""))
        text = message.get("text", "").strip()

        token = TELEGRAM_BOT_TOKEN
        if not token or not chat_id:
            return jsonify({"ok": False, "error": "Bot token or chat_id missing"}), 400

        base_tg_url = f"https://api.telegram.org/bot{token}"
        web_url = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))

        if text.startswith("/start"):
            welcome_text = (
                f"👋 *Welcome to our Storefront, {first_name}!*"
                + (f" (@{username})" if username else "")
                + "\n━━━━━━━━━━━━━━━━━━━━━━\n"
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
            reply_payload = {
                "chat_id": chat_id,
                "text": welcome_text,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🛍️ Open Store & Place Order", "web_app": {"url": web_url}}],
                        [{"text": "🌐 Open in Web Browser", "url": web_url}]
                    ]
                }
            }
        elif text.startswith("/orders"):
            orders = database.get_orders_by_telegram_user(user_id) if user_id else []
            if not orders:
                orders_text = f"📦 *No Orders Found for {first_name}*\n\nYou haven't placed any orders yet. Tap below to launch our store and place your first order!"
            else:
                lines = [
                    f"• `{o.get('order_number')}`: *{o.get('product_name')}* (x{o.get('quantity')}) — ${float(o.get('total_price', 0)):.2f} [{o.get('status', 'pending').upper()}]"
                    for o in orders[:5]
                ]
                orders_text = f"📦 *Your Recent Orders:*\n\n" + "\n".join(lines)

            reply_payload = {
                "chat_id": chat_id,
                "text": orders_text,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [[{"text": "🛍️ Open Store", "web_app": {"url": web_url}}]]
                }
            }
        elif text.startswith("/help"):
            reply_payload = {
                "chat_id": chat_id,
                "text": (
                    "ℹ️ *Storefront Bot Help & Guide*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "• `/start` - Launch storefront Mini App\n"
                    "• `/orders` - View your order history\n"
                    "• `/help` - View store guide\n"
                    "• `/status` - Check your Chat ID\n\n"
                    f"📍 *Your Chat ID:* `{chat_id}`"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [[{"text": "🛍️ Open Store", "web_app": {"url": web_url}}]]
                }
            }
        elif text.startswith("/status"):
            reply_payload = {
                "chat_id": chat_id,
                "text": f"📍 *Your Telegram Chat ID:* `{chat_id}`\n\nUse this Chat ID in TELEGRAM_CHAT_ID to receive alerts!",
                "parse_mode": "Markdown"
            }
        else:
            # Default response
            reply_payload = {
                "chat_id": chat_id,
                "text": "👋 Welcome! Tap below to open our store and place an order:",
                "reply_markup": {
                    "inline_keyboard": [[{"text": "🛍️ Open Store & Place Order", "web_app": {"url": web_url}}]]
                }
            }

        try:
            req = urllib.request.Request(
                f"{base_tg_url}/sendMessage",
                data=json.dumps(reply_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return jsonify({"ok": True, "result": resp_data})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/setup-bot-commands", methods=["GET", "POST"])
    def setup_bot_commands():
        """
        Registers the /start, /orders, /help commands in Telegram's autocomplete menu
        and configures the persistent 'Shop' WebApp menu button.
        """
        data = request.get_json(force=True, silent=True) or {}
        token = data.get("bot_token") or TELEGRAM_BOT_TOKEN
        web_url = data.get("web_app_url") or os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))

        if not token:
            return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}), 400

        base_tg_url = f"https://api.telegram.org/bot{token}"
        results = {}

        # 1. setMyCommands
        try:
            cmd_payload = {
                "commands": [
                    {"command": "start", "description": "🛍️ Open Store & Place Order"},
                    {"command": "orders", "description": "📦 View my recent orders"},
                    {"command": "help", "description": "ℹ️ Store guide & customer support"},
                    {"command": "status", "description": "📍 Check chat ID & bot status"}
                ]
            }
            req = urllib.request.Request(
                f"{base_tg_url}/setMyCommands",
                data=json.dumps(cmd_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                results["setMyCommands"] = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            results["setMyCommands"] = {"ok": False, "error": str(e)}

        # 2. setChatMenuButton (Persistent Mini App Button)
        if web_url and web_url.startswith("https://"):
            try:
                menu_payload = {
                    "menu_button": {
                        "type": "web_app",
                        "text": "Shop",
                        "web_app": {"url": web_url}
                    }
                }
                req2 = urllib.request.Request(
                    f"{base_tg_url}/setChatMenuButton",
                    data=json.dumps(menu_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    results["setChatMenuButton"] = json.loads(r2.read().decode("utf-8"))
            except Exception as e:
                results["setChatMenuButton"] = {"ok": False, "error": str(e)}

        return jsonify({
            "success": True,
            "message": "Bot menu commands and /start configuration dispatched to Telegram!",
            "details": results
        })

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        dist_dir = os.path.join(os.path.dirname(__file__), "dist")
        if path and os.path.exists(os.path.join(dist_dir, path)):
            return send_from_directory(dist_dir, path)
        if os.path.exists(os.path.join(dist_dir, "index.html")):
            return send_from_directory(dist_dir, "index.html")
        return jsonify({"status": "API Server running. Frontend build pending."})

except ImportError:
    app = None

if __name__ == "__main__":
    if app:
        print(f"Starting Flask server on port {PORT}...")
        app.run(host="0.0.0.0", port=PORT, debug=True)
    else:
        print("Flask not installed in this Python environment. Requirements can be installed via 'pip install -r requirements.txt'")
