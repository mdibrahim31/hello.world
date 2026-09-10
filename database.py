"""
Database module for E-Commerce Order System
Supports SQLite with persistent storage and optional Supabase / PostgreSQL schema compatibility.
"""
import sqlite3
import os
import sys
import json
from datetime import datetime

DB_FILE = os.getenv("DATABASE_FILE", "orders.db")

def get_db_connection(db_path=None):
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes the database schema."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE,
        customer_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price REAL DEFAULT 0.0,
        total_price REAL DEFAULT 0.0,
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        is_telegram_webapp INTEGER DEFAULT 0,
        telegram_user_id TEXT DEFAULT '',
        telegram_username TEXT DEFAULT '',
        alert_sent INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {db_path or DB_FILE}")

def create_order(customer_name, phone_number, product_name, quantity, 
                 unit_price=0.0, total_price=0.0, notes='', 
                 is_telegram_webapp=0, telegram_user_id='', telegram_username='', 
                 db_path=None):
    """Inserts a new order and returns the inserted order record as a dict."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Generate human-friendly order number e.g. ORD-2026-XXXX
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    order_number = f"ORD-{timestamp[-6:]}"
    
    calc_total = total_price if total_price > 0 else (unit_price * int(quantity))

    cursor.execute("""
    INSERT INTO orders (
        order_number, customer_name, phone_number, product_name, 
        quantity, unit_price, total_price, notes, status,
        is_telegram_webapp, telegram_user_id, telegram_username, alert_sent
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 0)
    """, (
        order_number,
        customer_name.strip(),
        phone_number.strip(),
        product_name.strip(),
        int(quantity),
        float(unit_price),
        float(calc_total),
        notes.strip() if notes else '',
        1 if is_telegram_webapp else 0,
        str(telegram_user_id or ''),
        str(telegram_username or '')
    ))
    
    order_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    order_dict = dict(row)
    conn.close()
    return order_dict

def get_all_orders(limit=50, db_path=None):
    """Retrieves recent orders."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    orders = [dict(r) for r in rows]
    conn.close()
    return orders

def get_order_by_id(order_id, db_path=None):
    """Retrieves an order by its ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ? OR order_number = ?", (order_id, str(order_id)))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_order_status(order_id, status, db_path=None):
    """Updates order status (e.g. pending, confirmed, shipped, cancelled)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ? OR order_number = ?", (status, str(order_id), str(order_id)))
    conn.commit()
    conn.close()

def mark_alert_sent(order_id, db_path=None):
    """Marks Telegram alert as dispatched."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET alert_sent = 1 WHERE id = ? OR order_number = ?", (order_id, str(order_id)))
    conn.commit()
    conn.close()

# CLI handler for direct command-line operations or subprocess calls
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "init":
            init_db()
        elif cmd == "list":
            init_db()
            print(json.dumps(get_all_orders()))
        elif cmd == "insert":
            # Usage: python database.py insert <name> <phone> <product> <qty> [price] [notes] [is_tg] [tg_uid] [tg_uname]
            name = sys.argv[2]
            phone = sys.argv[3]
            product = sys.argv[4]
            qty = int(sys.argv[5])
            price = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
            notes = sys.argv[7] if len(sys.argv) > 7 else ""
            is_tg = int(sys.argv[8]) if len(sys.argv) > 8 else 0
            tg_uid = sys.argv[9] if len(sys.argv) > 9 else ""
            tg_uname = sys.argv[10] if len(sys.argv) > 10 else ""
            init_db()
            new_ord = create_order(name, phone, product, qty, price, price * qty, notes, is_tg, tg_uid, tg_uname)
            print(json.dumps(new_ord))
    else:
        init_db()
