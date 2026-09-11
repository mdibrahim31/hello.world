"""
Database module for E-Commerce Order System
Supports SQLite with persistent storage and automatic path resolution for cloud hosts like Render.
"""
import sqlite3
import os
import sys
import json
from datetime import datetime

def get_resolved_db_path(db_path=None):
    """
    Safely resolves the SQLite database path:
    1. Reads provided path or DATABASE_FILE environment variable (default: 'orders.db').
    2. If relative, anchors to the directory of this script (current app directory).
    3. Automatically creates any missing parent directories via os.makedirs(..., exist_ok=True).
    4. If the directory cannot be created or is not writable, safely falls back to
       the current working directory or system temp directory (e.g. /tmp/orders.db).
    """
    raw_path = db_path or os.getenv("DATABASE_FILE", "orders.db")
    if not raw_path or not isinstance(raw_path, str):
        raw_path = "orders.db"
    raw_path = raw_path.strip()

    # Determine base directory of the project
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Check if absolute or relative
    if os.path.isabs(raw_path):
        target_path = os.path.abspath(raw_path)
    else:
        target_path = os.path.abspath(os.path.join(base_dir, raw_path))

    # Ensure parent directory exists
    parent_dir = os.path.dirname(target_path)
    if parent_dir:
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as err:
            print(f"⚠️ [database] Unable to create directory '{parent_dir}': {err}. Falling back to app directory.")
            target_path = os.path.abspath(os.path.join(base_dir, "orders.db"))
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
            except Exception:
                pass

    return target_path

def get_db_connection(db_path=None):
    """
    Connects to SQLite with:
    - Path safety and directory creation (os.makedirs)
    - WAL journal mode for concurrent reads/writes between Flask and Telegram Bot
    - timeout=30.0 to prevent 'database is locked' errors
    - Multi-stage fallbacks to app directory or tempdir if cloud volume is inaccessible
    """
    path = get_resolved_db_path(db_path)

    # Attempt 1: Standard resolved path
    try:
        conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        return conn
    except sqlite3.OperationalError as e:
        print(f"⚠️ [database] OperationalError connecting to {path}: {e}")

    # Attempt 2: Local directory fallback ('orders.db' in script folder)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(base_dir, "orders.db")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        conn = sqlite3.connect(local_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        print(f"✅ [database] Connected using local app directory fallback: {local_path}")
        return conn
    except Exception as err2:
        print(f"⚠️ [database] Local directory fallback failed: {err2}")

    # Attempt 3: Temporary directory fallback (always writable on Linux/Render)
    import tempfile
    tmp_path = os.path.join(tempfile.gettempdir(), "orders.db")
    print(f"⚠️ [database] Connecting to temp directory fallback: {tmp_path}")
    conn = sqlite3.connect(tmp_path, timeout=30.0, check_same_thread=False)
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

    # Telegram bot conversation session table (for multi-step flows like Register / Search)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_sessions (
        user_id TEXT PRIMARY KEY,
        state TEXT NOT NULL DEFAULT 'idle',
        data TEXT DEFAULT '{}',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Fallback / mirror table for users (in case Supabase is offline or not yet configured)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS local_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        image_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully at {get_resolved_db_path(db_path)}")

def get_user_session(user_id, db_path=None):
    """Gets the active bot conversation session for a Telegram user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT state, data FROM bot_sessions WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"state": "idle", "data": {}}
    try:
        parsed_data = json.loads(row["data"]) if row["data"] else {}
    except Exception:
        parsed_data = {}
    return {"state": row["state"], "data": parsed_data}

def set_user_session(user_id, state, data=None, db_path=None):
    """Sets or updates the active bot conversation session for a Telegram user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    json_data = json.dumps(data or {})
    cursor.execute("""
        INSERT INTO bot_sessions (user_id, state, data, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            state = excluded.state,
            data = excluded.data,
            updated_at = CURRENT_TIMESTAMP
    """, (str(user_id), str(state), json_data))
    conn.commit()
    conn.close()

def clear_user_session(user_id, db_path=None):
    """Resets user session state back to idle."""
    set_user_session(user_id, "idle", {}, db_path)

def save_local_user(name, phone, image_name, image_url, db_path=None):
    """Saves user record to local SQLite (mirror / fallback)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO local_users (name, phone, image_name, image_url)
        VALUES (?, ?, ?, ?)
    """, (name.strip(), phone.strip(), image_name.strip(), image_url.strip()))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": user_id, "name": name, "phone": phone, "image_name": image_name, "image_url": image_url}

def search_local_users(image_name, db_path=None):
    """Searches local SQLite users by image_name."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    pattern = f"%{image_name.strip()}%"
    cursor.execute("""
        SELECT * FROM local_users
        WHERE image_name LIKE ?
        ORDER BY id DESC
    """, (pattern,))
    rows = cursor.fetchall()
    users = [dict(r) for r in rows]
    conn.close()
    return users

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

def get_orders_by_telegram_user(telegram_user_id, limit=10, db_path=None):
    """Retrieves orders placed by a specific Telegram user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM orders 
        WHERE telegram_user_id = ? 
        ORDER BY id DESC LIMIT ?
    """, (str(telegram_user_id), limit))
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
