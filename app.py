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
