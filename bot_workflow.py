"""
Core Telegram Bot Workflow Engine
Implements:
1. /start: Choice between "Register", "Search Image", and Storefront
2. Registration Flow (4 steps):
   - Step 1: User Name
   - Step 2: Phone Number
   - Step 3: Image Name
   - Step 4: Image File Upload -> Supabase Bucket 'user-images' -> Supabase 'users' table
3. Search Flow:
   - Prompt for Image Name -> Query Supabase 'users' by image_name
   - Return User Name, Phone, and send photo back via image_url
4. Backward compatibility with Storefront Mini App, /orders, /admin, and /status
"""
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

import database
import supabase_client

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", os.getenv("APP_URL", "https://hello-world-fcg3.onrender.com")).strip()

def send_telegram_request(method, payload, bot_token=None):
    """Dispatches an HTTP request to Telegram Bot API."""
    token = bot_token or TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print(f"⚠️ [bot_workflow] Telegram token missing for {method}")
        return {"ok": False, "error": "Bot token missing"}

    # Mock support for tests
    if token.startswith("test_") or token.startswith("mock_"):
        return {"ok": True, "result": {"message_id": 999, "mock": True}}

    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"⚠️ [bot_workflow] Error sending {method}: {e}")
        return {"ok": False, "error": str(e)}

def download_telegram_file(file_id, bot_token=None):
    """Downloads raw file bytes from Telegram Bot API using file_id."""
    token = bot_token or TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return None, "Bot token missing"

    # 1. getFile
    res = send_telegram_request("getFile", {"file_id": file_id}, bot_token=token)
    if not res.get("ok") or not res.get("result", {}).get("file_path"):
        return None, f"Could not retrieve file path from Telegram: {res.get('error')}"

    file_path = res["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "TelegramBot/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw_bytes = resp.read()
            return raw_bytes, file_path
    except Exception as e:
        return None, str(e)

def get_main_menu_keyboard(web_url=None):
    """Main Menu keyboard with Register, Search, and Storefront buttons."""
    url = web_url or WEB_APP_URL
    return {
        "inline_keyboard": [
            [
                {"text": "📝 Register Profile & Image", "callback_data": "action_register"},
                {"text": "🔍 Search Image", "callback_data": "action_search"}
            ],
            [
                {"text": "🛍️ Open Store & Place Order", "web_app": {"url": url}}
            ],
            [
                {"text": "📦 My Orders", "callback_data": "action_orders"},
                {"text": "ℹ️ Help & Guide", "callback_data": "action_help"}
            ]
        ]
    }

def get_cancel_keyboard():
    """Simple cancel keyboard for multi-step registration or search."""
    return {
        "inline_keyboard": [
            [{"text": "❌ Cancel & Main Menu", "callback_data": "action_cancel"}]
        ]
    }

def get_post_search_keyboard():
    """Keyboard shown after search results."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔍 Search Another Image", "callback_data": "action_search"},
                {"text": "📝 Register New Profile", "callback_data": "action_register"}
            ],
            [{"text": "🏠 Main Menu", "callback_data": "action_cancel"}]
        ]
    }

def handle_update(update, bot_token=None, web_url=None):
    """
    Main update router. Handles:
    - callback_query
    - message (text, photo, document, commands)
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    app_url = web_url or WEB_APP_URL

    # 1. Handle Inline Keyboard Callbacks
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq.get("id")
        user = cq.get("from", {})
        user_id = str(user.get("id", ""))
        chat_id = cq.get("message", {}).get("chat", {}).get("id") or user_id
        data = cq.get("data", "")

        # Acknowledge callback query
        send_telegram_request("answerCallbackQuery", {"callback_query_id": cq_id}, bot_token=token)

        if data == "action_register":
            database.set_user_session(user_id, "reg_name", {})
            msg = (
                "📝 *Registration (Step 1 of 4)*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "👤 Please enter your *Full Name*:\n\n"
                "_(Type /cancel anytime to return to main menu)_"
            )
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": get_cancel_keyboard()
            }, bot_token=token)

        elif data == "action_search":
            database.set_user_session(user_id, "search_query", {})
            msg = (
                "🔍 *Search Image & User Profile*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Please type or send the *Image Name* you wish to search:\n\n"
                "_(Type /cancel anytime to return to main menu)_"
            )
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": get_cancel_keyboard()
            }, bot_token=token)

        elif data == "action_cancel":
            database.clear_user_session(user_id)
            first_name = user.get("first_name", "Friend")
            return send_welcome_message(chat_id, first_name, user.get("username", ""), token, app_url)

        elif data == "action_orders":
            return send_orders_list(chat_id, user_id, user.get("first_name", "Customer"), token, app_url)

        elif data == "action_help":
            return send_help_message(chat_id, token, app_url)

    # 2. Handle Messages
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True, "note": "No message in update"}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    user = message.get("from", {})
    user_id = str(user.get("id", ""))
    first_name = user.get("first_name", "Friend")
    username = user.get("username", "")
    text = (message.get("text") or "").strip()

    # Read current conversation state
    session = database.get_user_session(user_id)
    state = session.get("state", "idle")
    session_data = session.get("data", {})

    # Global cancellation / reset commands
    if text in ["/cancel", "/stop"]:
        database.clear_user_session(user_id)
        send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": "🛑 *Action cancelled.* Returned to Main Menu.",
            "parse_mode": "Markdown",
            "reply_markup": get_main_menu_keyboard(app_url)
        }, bot_token=token)
        return {"ok": True}

    if text.startswith("/start"):
        database.clear_user_session(user_id)
        return send_welcome_message(chat_id, first_name, username, token, app_url)

    if text.startswith("/register"):
        database.set_user_session(user_id, "reg_name", {})
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": (
                "📝 *Registration (Step 1 of 4)*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "👤 Please enter your *Full Name*:\n\n"
                "_(Type /cancel anytime to return to main menu)_"
            ),
            "parse_mode": "Markdown",
            "reply_markup": get_cancel_keyboard()
        }, bot_token=token)

    if text.startswith("/search"):
        database.set_user_session(user_id, "search_query", {})
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": (
                "🔍 *Search Image & User Profile*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Please type or send the *Image Name* you wish to search:\n\n"
                "_(Type /cancel anytime to return to main menu)_"
            ),
            "parse_mode": "Markdown",
            "reply_markup": get_cancel_keyboard()
        }, bot_token=token)

    if text.startswith("/orders"):
        return send_orders_list(chat_id, user_id, first_name, token, app_url)

    if text.startswith("/admin"):
        return send_admin_summary(chat_id, token, app_url)

    if text.startswith("/help"):
        return send_help_message(chat_id, token, app_url)

    if text.startswith("/status"):
        return send_status_message(chat_id, token, app_url)

    # 3. Handle Active Multi-Step Conversation State
    # ── State: reg_name (Step 1 -> Step 2) ─────────────────────────
    if state == "reg_name":
        if not text:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Please enter a valid name in text format:"
            }, bot_token=token)

        session_data["name"] = text
        database.set_user_session(user_id, "reg_phone", session_data)
        msg = (
            "📝 *Registration (Step 2 of 4)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: *{text}*\n\n"
            "📱 Please enter your *Phone Number* (e.g. `+1234567890`):"
        )
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": get_cancel_keyboard()
        }, bot_token=token)

    # ── State: reg_phone (Step 2 -> Step 3) ────────────────────────
    elif state == "reg_phone":
        if not text:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Please enter a valid phone number:"
            }, bot_token=token)

        session_data["phone"] = text
        database.set_user_session(user_id, "reg_img_name", session_data)
        msg = (
            "📝 *Registration (Step 3 of 4)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: *{session_data.get('name')}*\n"
            f"📱 Phone: *{text}*\n\n"
            "🏷️ Please enter a *Name or Title for your Image*\n"
            "_(e.g. 'sunset_photo', 'passport', 'id_card', 'selfie')_:"
        )
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": get_cancel_keyboard()
        }, bot_token=token)

    # ── State: reg_img_name (Step 3 -> Step 4) ────────────────────
    elif state == "reg_img_name":
        if not text:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Please enter an image title/name:"
            }, bot_token=token)

        session_data["image_name"] = text
        database.set_user_session(user_id, "reg_img_file", session_data)
        msg = (
            "📝 *Registration (Step 4 of 4)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: *{session_data.get('name')}*\n"
            f"📱 Phone: *{session_data.get('phone')}*\n"
            f"🏷️ Image Name: *{text}*\n\n"
            "📸 Now, please **send or upload your Image/Photo** attachment right here in this chat!"
        )
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": get_cancel_keyboard()
        }, bot_token=token)

    # ── State: reg_img_file (Step 4 Upload & Save) ─────────────────
    elif state == "reg_img_file":
        photo_arr = message.get("photo")
        doc = message.get("document")

        file_id = None
        if photo_arr and isinstance(photo_arr, list):
            # Best resolution is always the last element
            file_id = photo_arr[-1].get("file_id")
        elif doc and doc.get("mime_type", "").startswith("image/"):
            file_id = doc.get("file_id")

        if not file_id:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Please send an actual **photo/image file** to complete registration (or tap Cancel below):",
                "parse_mode": "Markdown",
                "reply_markup": get_cancel_keyboard()
            }, bot_token=token)

        # Notify user processing has begun
        send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": "⏳ *Processing your image...*\nUploading to Supabase Storage bucket `user-images`...",
            "parse_mode": "Markdown"
        }, bot_token=token)

        # Download image from Telegram
        raw_bytes, path_or_err = download_telegram_file(file_id, bot_token=token)
        if not raw_bytes:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": f"❌ Could not download image from Telegram: {path_or_err}\nPlease try uploading again."
            }, bot_token=token)

        user_name = session_data.get("name", "User")
        user_phone = session_data.get("phone", "")
        img_title = session_data.get("image_name", "image")

        # Upload to Supabase Storage
        upload_res = supabase_client.upload_image_to_supabase(
            file_bytes=raw_bytes,
            image_name_hint=img_title,
            content_type="image/jpeg"
        )
        public_img_url = upload_res.get("public_url")

        # Insert to Supabase 'users' table
        db_res = supabase_client.insert_user_profile(
            name=user_name,
            phone=user_phone,
            image_name=img_title,
            image_url=public_img_url
        )

        # Clear session
        database.clear_user_session(user_id)

        # Send confirmation
        success_text = (
            "🎉 *Registration Completed Successfully!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name:* {user_name}\n"
            f"📱 *Phone:* {user_phone}\n"
            f"🏷️ *Image Name:* `{img_title}`\n\n"
            f"📦 *Storage Bucket:* `user-images`\n"
            f"💾 *Database Table:* `users`\n\n"
            f"🌐 *Supabase Image Public URL:*\n`{public_img_url}`"
        )

        # Also send photo back with confirmation caption
        photo_payload = {
            "chat_id": chat_id,
            "photo": public_img_url,
            "caption": f"✅ Registered: {img_title} by {user_name}",
            "reply_markup": get_post_search_keyboard()
        }
        res_photo = send_telegram_request("sendPhoto", photo_payload, bot_token=token)
        if not res_photo.get("ok"):
            # Fallback to text message if sendPhoto fails
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": success_text,
                "parse_mode": "Markdown",
                "reply_markup": get_post_search_keyboard()
            }, bot_token=token)

        return res_photo

    # ── State: search_query (Search by Image Name) ─────────────────
    elif state == "search_query":
        if not text:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Please type the image name you want to search:"
            }, bot_token=token)

        search_term = text.strip()
        send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": f"🔎 Searching Supabase database for *'{search_term}'*...",
            "parse_mode": "Markdown"
        }, bot_token=token)

        results = supabase_client.search_users_by_image(search_term)
        database.clear_user_session(user_id)

        if not results:
            return send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": (
                    f"❌ *No Records Found*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"No image was found matching *'{search_term}'* in the Supabase `users` table.\n\n"
                    "💡 Check the spelling or register a new image below:"
                ),
                "parse_mode": "Markdown",
                "reply_markup": get_post_search_keyboard()
            }, bot_token=token)

        # Found match(es)!
        first_match = results[0]
        f_name = first_match.get("name", "Unknown")
        f_phone = first_match.get("phone", "N/A")
        f_img_name = first_match.get("image_name", search_term)
        f_img_url = first_match.get("image_url", "")
        f_date = first_match.get("created_at", "")[:19]

        details_text = (
            "✅ *Image Record Found!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ *Image Name:* `{f_img_name}`\n"
            f"👤 *Registered By:* {f_name}\n"
            f"📱 *Phone Number:* {f_phone}\n"
            f"📅 *Uploaded At:* {f_date}\n\n"
            f"🌐 *Supabase URL:* [Direct Link]({f_img_url})"
        )

        # Send image back via Telegram sendPhoto
        if f_img_url:
            photo_payload = {
                "chat_id": chat_id,
                "photo": f_img_url,
                "caption": f"📸 {f_img_name}\n👤 {f_name} | 📱 {f_phone}",
                "reply_markup": get_post_search_keyboard()
            }
            res_photo = send_telegram_request("sendPhoto", photo_payload, bot_token=token)
            if res_photo.get("ok"):
                return res_photo

        # If sendPhoto fails or no URL, send text details
        return send_telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": details_text,
            "parse_mode": "Markdown",
            "reply_markup": get_post_search_keyboard()
        }, bot_token=token)

    # 4. Default Greeting / Menu for unhandled text
    return send_welcome_message(chat_id, first_name, username, token, app_url)

def send_welcome_message(chat_id, first_name="Friend", username="", bot_token=None, web_url=None):
    """Sends /start greeting with choice between Register and Search Image."""
    user_handle = f" (@{username})" if username else ""
    url = web_url or WEB_APP_URL
    text = (
        f"👋 *Welcome to our Supabase & Storefront Bot, {first_name}!*{user_handle}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Please choose an action from the options below:\n\n"
        "📝 *Register Profile*: Register your Name, Phone, and upload an image to Supabase Storage (`user-images` bucket).\n\n"
        "🔍 *Search Image*: Search the Supabase database by Image Name to retrieve the photo and owner details.\n\n"
        "🛍️ *Online Store*: Browse products and place orders with instant Telegram alerts."
    )
    return send_telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": get_main_menu_keyboard(url)
    }, bot_token=bot_token)

def send_orders_list(chat_id, user_id, first_name, bot_token=None, web_url=None):
    """Lists recent e-commerce orders for this Telegram user."""
    orders = database.get_orders_by_telegram_user(user_id) if user_id else []
    url = web_url or WEB_APP_URL
    if not orders:
        orders_text = f"📦 *No Store Orders Found for {first_name}*\n\nYou haven't placed any store orders yet. Tap below to launch our store and place your first order!"
    else:
        lines = [
            f"• `{o.get('order_number')}`: *{o.get('product_name')}* (x{o.get('quantity')}) — ${float(o.get('total_price', 0)):.2f} [{o.get('status', 'pending').upper()}]"
            for o in orders[:5]
        ]
        orders_text = f"📦 *Your Recent Orders:*\n\n" + "\n".join(lines)

    return send_telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": orders_text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🛍️ Open Store", "web_app": {"url": url}}],
                [{"text": "🏠 Main Menu", "callback_data": "action_cancel"}]
            ]
        }
    }, bot_token=bot_token)

def send_admin_summary(chat_id, bot_token=None, web_url=None):
    """Admin dashboard overview."""
    all_orders = database.get_all_orders()
    pending_count = sum(1 for o in all_orders if o.get("status") == "pending")
    total_rev = sum(float(o.get("total_price", 0)) for o in all_orders)
    url = web_url or WEB_APP_URL
    admin_text = (
        "👑 *Admin Dashboard Summary*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Total Orders:* `{len(all_orders)}`\n"
        f"⏳ *Pending Orders:* `{pending_count}`\n"
        f"💰 *Total Revenue:* `${total_rev:.2f}`\n\n"
        "🔗 Tap below to manage all orders in real-time:"
    )
    return send_telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": admin_text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📊 Open Order Manager", "url": url}],
                [{"text": "🛍️ Open Storefront", "web_app": {"url": url}}]
            ]
        }
    }, bot_token=bot_token)

def send_help_message(chat_id, bot_token=None, web_url=None):
    """Help & guide overview."""
    url = web_url or WEB_APP_URL
    help_text = (
        "ℹ️ *Bot Commands & Guide*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "• `/start` - Main menu with Register, Search & Store\n"
        "• `/register` - Start 4-step user & image registration\n"
        "• `/search` - Search Supabase by Image Name\n"
        "• `/orders` - View your recent store orders\n"
        "• `/admin` - View store admin summary\n"
        "• `/cancel` - Cancel current step and return to main menu\n"
        "• `/status` - Check your Chat ID and Supabase configuration status"
    )
    return send_telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": help_text,
        "parse_mode": "Markdown",
        "reply_markup": get_main_menu_keyboard(url)
    }, bot_token=bot_token)

def send_status_message(chat_id, bot_token=None, web_url=None):
    """Reports status of Telegram Bot & Supabase integration."""
    has_sb_url = bool(supabase_client.SUPABASE_URL)
    has_sb_key = bool(supabase_client.SUPABASE_KEY)
    masked_url = supabase_client.SUPABASE_URL if has_sb_url else "Not configured"

    status_text = (
        "⚡ *System & Integration Status*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *Your Chat ID:* `{chat_id}`\n\n"
        "🗄️ *Supabase Integration:*\n"
        f"• Status: {'✅ Configured' if (has_sb_url and has_sb_key) else '⚠️ Pending Env Vars'}\n"
        f"• Project URL: `{masked_url}`\n"
        f"• Storage Bucket: `user-images`\n"
        f"• Database Table: `users`\n\n"
        "💡 _Set SUPABASE_URL and SUPABASE_KEY in Render Environment Variables._"
    )
    return send_telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": status_text,
        "parse_mode": "Markdown"
    }, bot_token=bot_token)
