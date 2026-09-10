export const CODE_SNIPPETS: { [key: string]: string } = {
  "app.py": `# Flask API Server for E-Commerce Orders with Telegram Alerting
from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, urllib.request
import database

app = Flask(__name__)
CORS(app)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/api/order", methods=["POST"])
def place_order():
    data = request.json or {}
    order = database.create_order(
        customer_name=data["customer_name"],
        phone_number=data["phone_number"],
        product_name=data["product_name"],
        quantity=data.get("quantity", 1),
        unit_price=data.get("unit_price", 0.0),
        total_price=data.get("total_price", 0.0),
        notes=data.get("notes", ""),
        is_telegram_webapp=1 if data.get("is_telegram_webapp") else 0
    )
    
    # Send Telegram Bot Alert
    alert_text = (
        f"🛒 *New Order Alert!*\\n"
        f"🔖 Ref: {order.get('order_number')}\\n"
        f"👤 Name: {order.get('customer_name')}\\n"
        f"📞 Phone: {order.get('phone_number')}\\n"
        f"📦 Item: {order.get('product_name')} x {order.get('quantity')}\\n"
        f"💰 Total: \${order.get('total_price', 0.0):.2f}"
    )
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(
            url,
            data=json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": alert_text, "parse_mode": "Markdown"}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        
    return jsonify({"success": True, "order": order}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
`,

  "database.py": `# SQLite Database Storage for Orders
import sqlite3, os

DB_FILE = os.getenv("DATABASE_FILE", "orders.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE,
        customer_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        unit_price REAL DEFAULT 0.0,
        total_price REAL DEFAULT 0.0,
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        is_telegram_webapp INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
`,

  "bot.py": `# Telegram Bot script with /start WebApp button
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-domain.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [
            InlineKeyboardButton(
                "🛍️ Open Order Store", 
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 Open in Browser", 
                url=WEB_APP_URL
            )
        ]
    ]
    await update.message.reply_text(
        "👋 Welcome! Tap below to open our E-Commerce Store:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot polling started...")
    app.run_polling()
`,

  "requirements.txt": `Flask==3.0.3
Flask-Cors==4.0.1
python-telegram-bot==21.3
python-dotenv==1.0.1
requests==2.32.3
gunicorn==22.0.0
`,

  "render.yaml": `services:
  - type: web
    name: telegram-ecommerce-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_CHAT_ID
        sync: false
`
};
