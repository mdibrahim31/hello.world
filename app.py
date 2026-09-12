#!/usr/bin/env python3
"""
Python Web Server (Flask) for Render Web Service
------------------------------------------------
Serves the Admin Mini App UI and REST API for order processing,
Telegram alert dispatching, and security verification.
Runs with Gunicorn or direct python app.py.
"""

import os
import sys
import time
import json
import logging
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")

# Configuration
PORT = int(os.getenv("PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()

# In-memory experiment product catalog
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

# In-memory experiment orders
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
    },
    {
        "id": 1003,
        "order_number": "ORD-2026-003",
        "customer_name": "Tariqul Islam",
        "phone_number": "+880 1711-223344",
        "product_name": "Smart Fitness Tracker Band",
        "quantity": 1,
        "unit_price": 34.99,
        "total_price": 34.99,
        "status": "pending",
        "notes": "Call before delivery.",
        "source": "Telegram Chat Bot (/order)",
        "telegram_user_id": "99482103",
        "telegram_username": "tariq_bd",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(time.time() - 3600))
    }
]


def send_telegram_alert(order, custom_token=None, custom_chat=None):
    """Dispatch real-time Markdown alert to Telegram Admin."""
    token = custom_token or TELEGRAM_BOT_TOKEN
    target = custom_chat or TELEGRAM_CHAT_ID or ADMIN_TELEGRAM_ID

    qty = order.get("quantity", 1)
    total = f"{float(order.get('total_price', 0)):.2f}"
    username_line = f"\n👤 *Telegram User:* @{order['telegram_username']}" if order.get("telegram_username") else ""
    user_id_line = f" (ID: `{order['telegram_user_id']}`)" if order.get("telegram_user_id") else ""
    notes_line = f"\n📝 *Notes:* _{order['notes']}_" if order.get("notes") else ""

    text = (
        "🔔 *NEW ORDER ALERT (ADMIN ONLY)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Order Ref:* `{order.get('order_number')}`\n"
        f"👤 *Customer:* *{order.get('customer_name')}*\n"
        f"📞 *Phone:* `{order.get('phone_number')}`\n"
        f"📦 *Product:* *{order.get('product_name')}*\n"
        f"🔢 *Quantity:* {qty} unit(s)\n"
        f"💰 *Total Amount:* ${total}\n"
        f"📍 *Channel:* {order.get('source', 'Telegram Chat Bot')}"
        f"{username_line}{user_id_line}"
        f"{notes_line}\n"
        f"🕒 *Time:* {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ _Manage in Admin Mini App: /admin_"
    )

    if not token or not target:
        return {"success": False, "simulated": True, "preview": text, "error": "Bot token or chat ID not set"}

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": target, "text": text, "parse_mode": "Markdown"}
        res = requests.post(url, json=payload, timeout=10)
        return {"success": res.status_code == 200, "result": res.json()}
    except Exception as e:
        return {"success": False, "error": str(e), "preview": text}


# Serve Single-Page Admin Mini App Frontend
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "system": "Telegram Bot & Admin Mini App (Python / Flask on Render)",
        "database": "In-Memory Experiment Mode",
        "orders_count": len(memory_orders),
        "products_count": len(memory_products),
        "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
        "has_chat_id": bool(TELEGRAM_CHAT_ID),
        "has_admin_id": bool(ADMIN_TELEGRAM_ID)
    })


@app.route("/api/admin/verify", methods=["POST"])
def verify_admin():
    global ADMIN_PIN
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()
    tg_user_id = str(data.get("telegram_user_id", "")).strip()

    is_adm = False
    reason = ""

    if pin and pin == str(ADMIN_PIN).strip():
        is_adm = True
        reason = "Admin Security PIN verified"
    elif tg_user_id:
        if ADMIN_TELEGRAM_ID and tg_user_id == str(ADMIN_TELEGRAM_ID).strip():
            is_adm = True
            reason = f"Telegram User ID matched ADMIN_TELEGRAM_ID ({tg_user_id})"
        elif TELEGRAM_CHAT_ID and tg_user_id == str(TELEGRAM_CHAT_ID).strip():
            is_adm = True
            reason = f"Telegram User ID matched TELEGRAM_CHAT_ID ({tg_user_id})"

    if is_adm:
        return jsonify({"success": True, "isAdmin": True, "message": reason})
    return jsonify({
        "success": False,
        "isAdmin": False,
        "error": "Access Denied. Mini App is restricted to Admin only. Enter valid Admin PIN or launch from Admin Telegram Account."
    }), 403


@app.route("/api/admin/config", methods=["GET", "POST"])
@app.route("/api/config", methods=["GET", "POST"])
def admin_config():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_TELEGRAM_ID, ADMIN_PIN
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "bot_token" in data:
            TELEGRAM_BOT_TOKEN = str(data["bot_token"]).strip()
        if "chat_id" in data:
            TELEGRAM_CHAT_ID = str(data["chat_id"]).strip()
        if "admin_telegram_id" in data:
            ADMIN_TELEGRAM_ID = str(data["admin_telegram_id"]).strip()
        if "admin_pin" in data and str(data["admin_pin"]).strip():
            ADMIN_PIN = str(data["admin_pin"]).strip()
        return jsonify({"success": True, "message": "Configuration updated in memory"})

    masked = ""
    if TELEGRAM_BOT_TOKEN:
        parts = TELEGRAM_BOT_TOKEN.split(":")
        masked = f"{parts[0]}:***" if len(parts) > 1 else "***"

    return jsonify({
        "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
        "has_chat_id": bool(TELEGRAM_CHAT_ID),
        "has_admin_id": bool(ADMIN_TELEGRAM_ID),
        "bot_token_masked": masked,
        "chat_id": TELEGRAM_CHAT_ID,
        "admin_telegram_id": ADMIN_TELEGRAM_ID,
        "admin_pin_configured": bool(ADMIN_PIN),
        "database_mode": "In-Memory Experiment Mode"
    })


@app.route("/api/products", methods=["GET", "POST"])
def products_handler():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_prod = {
            "id": f"prod-{int(time.time())}",
            "name": data.get("name", "New Item"),
            "category": data.get("category", "General"),
            "price": float(data.get("price", 10.0)),
            "stock": int(data.get("stock", 10)),
            "image": data.get("image", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300"),
            "badge": data.get("badge", "New"),
            "description": data.get("description", "")
        }
        memory_products.append(new_prod)
        return jsonify({"success": True, "product": new_prod}), 201
    return jsonify({"success": True, "products": memory_products})


@app.route("/api/orders", methods=["GET", "POST", "DELETE"])
@app.route("/api/order", methods=["GET", "POST"])
def orders_handler():
    global memory_orders
    if request.method == "GET":
        q = request.args.get("q", "").lower().strip()
        status_filter = request.args.get("status", "").strip()

        results = list(memory_orders)
        if status_filter:
            results = [o for o in results if o.get("status") == status_filter]
        if q:
            results = [
                o for o in results if
                q in o.get("customer_name", "").lower() or
                q in o.get("phone_number", "") or
                q in o.get("order_number", "").lower() or
                q in o.get("product_name", "").lower()
            ]

        return jsonify({
            "success": True,
            "orders": results,
            "total_count": len(memory_orders),
            "stats": {
                "pending": len([o for o in memory_orders if o.get("status") == "pending"]),
                "processing": len([o for o in memory_orders if o.get("status") == "processing"]),
                "delivered": len([o for o in memory_orders if o.get("status") == "delivered"]),
                "cancelled": len([o for o in memory_orders if o.get("status") == "cancelled"]),
                "total_revenue": sum(float(o.get("total_price", 0)) for o in memory_orders)
            }
        })

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        count = len(memory_orders) + 1
        ref_id = f"ORD-EXP-{count:03d}"
        qty = int(data.get("quantity", 1))
        unit_price = float(data.get("unit_price", 0.0))
        total_price = float(data.get("total_price", 0.0))
        if total_price == 0 and unit_price > 0:
            total_price = unit_price * qty

        new_order = {
            "id": int(time.time() * 1000),
            "order_number": data.get("order_number", ref_id),
            "customer_name": data.get("customer_name", "Experiment Customer"),
            "phone_number": data.get("phone_number", "N/A"),
            "product_name": data.get("product_name", "General Product"),
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": total_price,
            "status": data.get("status", "pending"),
            "notes": data.get("notes", ""),
            "source": data.get("source", "Telegram Chat Bot (/order)"),
            "telegram_user_id": str(data.get("telegram_user_id", "")),
            "telegram_username": str(data.get("telegram_username", "")),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
        }

        memory_orders.insert(0, new_order)
        tg_res = send_telegram_alert(new_order)
        return jsonify({"success": True, "order": new_order, "telegram": tg_res}), 201

    if request.method == "DELETE":
        memory_orders = []
        return jsonify({"success": True, "message": "All experiment orders cleared from memory."})


@app.route("/api/order/<int:order_id>/status", methods=["PATCH"])
@app.route("/api/orders/<int:order_id>/status", methods=["PATCH"])
def update_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "pending")
    target = next((o for o in memory_orders if o["id"] == order_id), None)
    if target:
        target["status"] = new_status
        return jsonify({"success": True, "order": target})
    return jsonify({"success": False, "error": "Order not found"}), 404


@app.route("/api/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    global memory_orders
    initial_len = len(memory_orders)
    memory_orders = [o for o in memory_orders if o["id"] != order_id]
    if len(memory_orders) < initial_len:
        return jsonify({"success": True, "message": f"Order #{order_id} deleted"})
    return jsonify({"success": False, "error": "Order not found"}), 404


@app.route("/api/test-telegram", methods=["POST"])
def test_telegram():
    data = request.get_json(silent=True) or {}
    custom_token = data.get("bot_token")
    custom_chat = data.get("chat_id")
    test_order = {
        "id": 9999,
        "order_number": "TEST-EXP-001",
        "customer_name": "Test Customer (Experiment)",
        "phone_number": "+1 (555) 019-2834",
        "product_name": "Wireless Noise-Cancelling Earbuds",
        "quantity": 1,
        "unit_price": 49.99,
        "total_price": 49.99,
        "notes": "Testing Admin Telegram Alert from Python backend",
        "source": "Telegram Chat Bot (/order)",
        "telegram_user_id": custom_chat or "123456789",
        "telegram_username": "admin_tester"
    }
    result = send_telegram_alert(test_order, custom_token, custom_chat)
    return jsonify(result)


if __name__ == "__main__":
    print(f"🚀 Python Web Server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
