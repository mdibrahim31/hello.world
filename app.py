"""
E-Commerce Order System - Backend Server (Flask)
Ready for deployment on Render, Vercel, or local execution.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import subprocess
import threading
import atexit
from datetime import datetime

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import database
import supabase_client
import bot_workflow

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
PORT = int(os.getenv("PORT", 3000))

# Background Bot Process Tracking
_bot_process = None
_bot_lock = threading.Lock()

def start_background_bot():
    """
    Automatically runs bot.py as a background process/thread when app.py starts.
    This allows both the REST API server and the Telegram Bot (polling for /start,
    /orders, and alerts) to run simultaneously without needing a separate worker
    or changing the Render Start Command.
    """
    global _bot_process
    with _bot_lock:
        # If already running, do not start again
        if _bot_process is not None:
            if hasattr(_bot_process, "poll") and _bot_process.poll() is None:
                return _bot_process
            if hasattr(_bot_process, "is_alive") and _bot_process.is_alive():
                return _bot_process

        # Prevent duplicate bot process if Werkzeug debug reloader parent process runs
        if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
            return None

        # Allow user to disable auto-bot via environment variable if running standalone bot
        if os.getenv("DISABLE_BACKGROUND_BOT", "false").lower() in ("true", "1", "yes"):
            print("ℹ️ [Background Bot] Disabled via DISABLE_BACKGROUND_BOT env variable.")
            return None

        bot_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py")
        if not os.path.exists(bot_script):
            print(f"⚠️ [Background Bot] bot.py not found at: {bot_script}")
            return None

        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            print("ℹ️ [Background Bot] TELEGRAM_BOT_TOKEN is not set yet. The bot script will run and wait for credentials.")

        print(f"🤖 [app.py] Starting Telegram bot ({bot_script}) in background process...")
        try:
            bot_env = os.environ.copy()
            bot_env["PYTHONUNBUFFERED"] = "1"
            # Spawn bot.py unbuffered using the current Python interpreter environment
            _bot_process = subprocess.Popen(
                [sys.executable, "-u", bot_script],
                env=bot_env
            )
            print(f"✅ [app.py] Telegram bot background process started successfully (PID: {_bot_process.pid})")
            return _bot_process
        except Exception as e:
            print(f"⚠️ [app.py] Subprocess execution failed: {e}. Falling back to background daemon thread...")
            try:
                import bot
                t = threading.Thread(target=bot.main, daemon=True, name="TelegramBotDaemon")
                t.start()
                _bot_process = t
                print("✅ [app.py] Telegram bot running in background daemon thread.")
                return _bot_process
            except Exception as thread_err:
                print(f"❌ [app.py] Failed to launch bot thread: {thread_err}")
                return None

def stop_background_bot():
    """Cleanly terminates the background bot process when the web server shuts down."""
    global _bot_process
    if _bot_process is not None:
        try:
            if hasattr(_bot_process, "terminate"):
                print("🛑 [app.py] Shutting down background Telegram bot process...")
                _bot_process.terminate()
                _bot_process.wait(timeout=3)
        except Exception:
            pass

atexit.register(stop_background_bot)

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

# Initialize database tables on startup safely
try:
    database.init_db()
except Exception as _init_err:
    print(f"⚠️ [app.py] Database initialization warning: {_init_err}")

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
        Delegates to bot_workflow to handle /start (Register / Search / Store),
        the 4-step registration flow, image upload to Supabase 'user-images' bucket,
        and image name search.
        """
        if request.method == "GET":
            return jsonify({
                "status": "Telegram webhook listening",
                "has_token": bool(TELEGRAM_BOT_TOKEN),
                "supabase_configured": bool(supabase_client.SUPABASE_URL and supabase_client.SUPABASE_KEY),
                "instructions": "Send Telegram updates via POST to this endpoint or configure via setWebhook."
            })

        update = request.get_json(force=True, silent=True) or {}
        if not update:
            return jsonify({"ok": True, "note": "No update in payload"})

        token = TELEGRAM_BOT_TOKEN
        web_url = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))

        # Process update with unified bot workflow engine
        result = bot_workflow.handle_update(update, bot_token=token, web_url=web_url)
        return jsonify({"ok": True, "result": result})

    @app.route("/api/supabase/status", methods=["GET"])
    def supabase_status_endpoint():
        """Returns the status of Supabase configuration and setup."""
        has_url = bool(supabase_client.SUPABASE_URL)
        has_key = bool(supabase_client.SUPABASE_KEY)
        client = supabase_client.get_supabase_client()
        return jsonify({
            "configured": bool(has_url and has_key),
            "supabase_url": supabase_client.SUPABASE_URL if has_url else None,
            "has_key": has_key,
            "bucket_name": supabase_client.BUCKET_NAME,
            "client_initialized": bool(client is not None),
            "table": "users",
            "schema_fields": ["id", "name", "phone", "image_name", "image_url", "created_at"],
            "sql_migration": supabase_client.get_supabase_sql_migration()
        })

    @app.route("/api/supabase/users", methods=["GET"])
    def supabase_users_endpoint():
        """Lists users or searches users by image name from Supabase / fallback."""
        q = request.args.get("q", "").strip()
        if q:
            results = supabase_client.search_users_by_image(q)
            return jsonify({"success": True, "query": q, "count": len(results), "users": results})

        client = supabase_client.get_supabase_client()
        if client:
            try:
                res = client.table("users").select("*").order("id", desc=True).limit(50).execute()
                return jsonify({"success": True, "source": "supabase", "count": len(res.data), "users": res.data})
            except Exception as err:
                print(f"⚠️ Supabase fetch error: {err}")

        # Local SQLite fallback
        local_records = database.search_local_users("")
        return jsonify({"success": True, "source": "local_sqlite", "count": len(local_records), "users": local_records})

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

    @app.route("/api/set-webhook", methods=["GET", "POST"])
    def configure_webhook():
        """
        Configures Telegram Webhook to point directly to Render /api/webhook.
        This allows 100% instant responses to /start, /orders, /admin even if background bot polling is not running!
        """
        token = TELEGRAM_BOT_TOKEN
        if not token:
            return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}), 400

        data = request.get_json(force=True, silent=True) or {}
        custom_base = request.args.get("url") or data.get("url")
        base_url = custom_base or os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))
        webhook_url = f"{base_url.rstrip('/')}/api/webhook"

        try:
            tg_url = f"https://api.telegram.org/bot{token}/setWebhook"
            wh_payload = {
                "url": webhook_url,
                "drop_pending_updates": True,
                "allowed_updates": ["message", "edited_message", "callback_query", "inline_query"]
            }
            req = urllib.request.Request(
                tg_url,
                data=json.dumps(wh_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                res_data = json.loads(r.read().decode("utf-8"))
            return jsonify({
                "success": res_data.get("ok", False),
                "webhook_url": webhook_url,
                "telegram_response": res_data,
                "message": f"Webhook configured! Telegram will now forward messages and button clicks to {webhook_url}"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/delete-webhook", methods=["GET", "POST"])
    def remove_webhook():
        """Deletes any configured webhook to allow long-polling in bot.py."""
        token = TELEGRAM_BOT_TOKEN
        if not token:
            return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}), 400
        try:
            tg_url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
            req = urllib.request.Request(tg_url)
            with urllib.request.urlopen(req, timeout=10) as r:
                res_data = json.loads(r.read().decode("utf-8"))
            return jsonify({"success": True, "telegram_response": res_data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/health", methods=["GET"])
    @app.route("/health", methods=["GET"])
    def health_check():
        bot_running = False
        bot_pid = None
        if _bot_process is not None:
            if hasattr(_bot_process, "poll"):
                bot_running = (_bot_process.poll() is None)
                bot_pid = _bot_process.pid
            elif hasattr(_bot_process, "is_alive"):
                bot_running = _bot_process.is_alive()
                bot_pid = "thread"

        return jsonify({
            "status": "healthy",
            "server": "Flask E-Commerce API",
            "timestamp": datetime.now().isoformat(),
            "has_bot_token": bool(TELEGRAM_BOT_TOKEN),
            "has_chat_id": bool(TELEGRAM_CHAT_ID),
            "background_bot": {
                "running": bot_running,
                "pid": bot_pid,
                "auto_start": True
            }
        })

    @app.route("/api/bot-status", methods=["GET", "POST"])
    def bot_status_endpoint():
        """Returns background bot status, or starts/restarts it if requested."""
        if request.method == "POST":
            stop_background_bot()
            start_background_bot()

        bot_running = False
        bot_pid = None
        if _bot_process is not None:
            if hasattr(_bot_process, "poll"):
                bot_running = (_bot_process.poll() is None)
                bot_pid = _bot_process.pid
            elif hasattr(_bot_process, "is_alive"):
                bot_running = _bot_process.is_alive()
                bot_pid = "thread"

        return jsonify({
            "running": bot_running,
            "pid": bot_pid,
            "bot_token_configured": bool(TELEGRAM_BOT_TOKEN),
            "chat_id_configured": bool(TELEGRAM_CHAT_ID),
            "web_app_url": os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com"))
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

    # Start the background bot automatically when the WSGI/Flask module is loaded
    start_background_bot()

except ImportError:
    app = None

if __name__ == "__main__":
    # Ensure the background bot is running when invoked directly
    start_background_bot()

    if app:
        print(f"🚀 Starting Flask server on port {PORT}...")
        # debug=False and use_reloader=False prevent duplicate child processes in production/local
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    else:
        print("Flask not installed in this Python environment. Requirements can be installed via 'pip install -r requirements.txt'")
