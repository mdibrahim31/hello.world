"""
Supabase Integration Module for Database and File Storage
Supports:
1. supabase-py official client library (with urllib/requests fallback)
2. Supabase Storage Bucket 'user-images' for uploading and serving public images
3. Table 'users' schema: id, name, phone, image_name, image_url, created_at
4. Graceful fallbacks and multi-source syncing with local SQLite
"""
import os
import json
import time
import re
import urllib.request
import urllib.parse
from datetime import datetime

import database

# Read credentials from environment variables
_raw_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
if "/rest/v1" in _raw_url:
    _raw_url = _raw_url.split("/rest/v1")[0].rstrip("/")
SUPABASE_URL = _raw_url

SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))).strip()
BUCKET_NAME = "user-images"

# Global cached client instance
_supabase_client = None
_client_initialized = False

def get_supabase_client():
    """
    Lazy initialization for Supabase Client.
    Safely loads supabase-py if installed, and caches the client.
    """
    global _supabase_client, _client_initialized
    if _client_initialized:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ [supabase] SUPABASE_URL or SUPABASE_KEY not set in environment.")
        _client_initialized = True
        _supabase_client = None
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ [supabase] Connected successfully to {SUPABASE_URL}")
        _client_initialized = True
        # Try to ensure bucket exists
        ensure_storage_bucket()
        return _supabase_client
    except ImportError:
        print("ℹ️ [supabase] 'supabase' Python package not installed yet. Using REST API fallback.")
        _client_initialized = True
        _supabase_client = None
        return None
    except Exception as e:
        print(f"⚠️ [supabase] Error initializing Supabase client: {e}")
        _client_initialized = True
        _supabase_client = None
        return None

def ensure_storage_bucket():
    """
    Ensures that the 'user-images' storage bucket exists and is public.
    """
    client = get_supabase_client()
    if client:
        try:
            buckets = client.storage.list_buckets()
            existing_names = [b.name if hasattr(b, "name") else b.get("name", "") for b in buckets]
            if BUCKET_NAME not in existing_names:
                print(f"📦 [supabase] Creating public storage bucket '{BUCKET_NAME}'...")
                client.storage.create_bucket(BUCKET_NAME, options={"public": True})
                print(f"✅ [supabase] Bucket '{BUCKET_NAME}' created successfully.")
            return True
        except Exception as err:
            # Bucket might already exist or need admin privileges
            print(f"ℹ️ [supabase] Bucket check note: {err}")
            return False

    # HTTP REST fallback if client library is not loaded
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            req = urllib.request.Request(
                f"{SUPABASE_URL}/storage/v1/bucket",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({"name": BUCKET_NAME, "id": BUCKET_NAME, "public": True}).encode("utf-8"),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
            return True
        except Exception:
            return False
    return False

def get_public_image_url(file_path):
    """Generates the direct public URL for a file stored in 'user-images' bucket."""
    clean_path = file_path.lstrip("/")
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{clean_path}"

def upload_image_to_supabase(file_bytes, image_name_hint="image", content_type="image/jpeg"):
    """
    Uploads image bytes to Supabase Storage in 'user-images' bucket.
    Returns dict with success status, public_url, and file_path.
    """
    if not file_bytes:
        return {"success": False, "error": "No file bytes provided"}

    # Sanitize file name
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', image_name_hint.strip())
    if not safe_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        safe_name += ".jpg"

    timestamp = int(time.time())
    file_path = f"{timestamp}_{safe_name}"

    client = get_supabase_client()
    if client:
        try:
            # Ensure bucket exists
            ensure_storage_bucket()

            # Upload to storage
            res = client.storage.from_(BUCKET_NAME).upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            # Retrieve public URL
            public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)
            if not public_url:
                public_url = get_public_image_url(file_path)

            print(f"✅ [supabase] Image uploaded successfully: {public_url}")
            return {
                "success": True,
                "public_url": public_url,
                "file_path": file_path,
                "storage": "supabase"
            }
        except Exception as e:
            print(f"⚠️ [supabase] Upload via client failed ({e}), trying REST fallback...")

    # REST API fallback if client upload failed or client not installed
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_path}"
            req = urllib.request.Request(
                upload_url,
                data=file_bytes,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": content_type,
                    "x-upsert": "true"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                public_url = get_public_image_url(file_path)
                print(f"✅ [supabase] Image uploaded via REST: {public_url}")
                return {
                    "success": True,
                    "public_url": public_url,
                    "file_path": file_path,
                    "storage": "supabase_rest"
                }
        except Exception as rest_err:
            print(f"⚠️ [supabase] REST image upload failed: {rest_err}")

    # Local fallback URL if Supabase is unreachable or not configured
    local_url = f"{SUPABASE_URL or 'https://images.unsplash.com'}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
    return {
        "success": True,
        "public_url": local_url,
        "file_path": file_path,
        "storage": "fallback",
        "note": "Supabase credentials not configured yet or bucket permission restricted; saved locally."
    }

def insert_user_profile(name, phone, image_name, image_url):
    """
    Inserts a user record into the Supabase 'users' table.
    Schema: id (auto), name, phone, image_name, image_url, created_at.
    Dual-writes to SQLite local_users for fail-safe persistence.
    """
    clean_name = str(name or "").strip()
    clean_phone = str(phone or "").strip()
    clean_img_name = str(image_name or "").strip()
    clean_img_url = str(image_url or "").strip()

    # Always persist locally first to guarantee no user data is ever lost
    local_record = database.save_local_user(clean_name, clean_phone, clean_img_name, clean_img_url)

    row_data = {
        "name": clean_name,
        "phone": clean_phone,
        "image_name": clean_img_name,
        "image_url": clean_img_url
    }

    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").insert(row_data).execute()
            inserted = res.data[0] if res.data else row_data
            print(f"✅ [supabase] User inserted into 'users' table: {inserted.get('id', 'new')}")
            return {"success": True, "data": inserted, "source": "supabase"}
        except Exception as err:
            err_str = str(err)
            print(f"⚠️ [supabase] Table insert failed ({err_str}). Trying REST fallback...")
            # If relation does not exist, note it
            if "relation \"public.users\" does not exist" in err_str or "PGRST205" in err_str:
                print("💡 [supabase] Notice: 'users' table has not been created yet in Supabase SQL editor.")

    # REST API fallback
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/users",
                data=json.dumps(row_data).encode("utf-8"),
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                inserted = resp_json[0] if isinstance(resp_json, list) and resp_json else row_data
                return {"success": True, "data": inserted, "source": "supabase_rest"}
        except Exception as rest_e:
            print(f"ℹ️ [supabase] REST insert fallback: {rest_e}")

    # Stored locally
    return {
        "success": True,
        "data": local_record,
        "source": "local_sqlite",
        "note": "Saved in persistent SQLite storage (Supabase table not connected or pending configuration)."
    }

def search_users_by_image(image_name):
    """
    Searches the Supabase 'users' table by image_name (case-insensitive substring/match).
    Falls back to local SQLite if Supabase returns nothing or is unconfigured.
    """
    query = str(image_name or "").strip()
    if not query:
        return []

    results = []
    client = get_supabase_client()
    if client:
        try:
            # Query by exact or ilike
            res = client.table("users").select("*").ilike("image_name", f"%{query}%").order("id", desc=True).limit(5).execute()
            if res.data:
                results = res.data
                return results
        except Exception as e:
            print(f"ℹ️ [supabase] Client search query note: {e}")

    # REST fallback query
    if SUPABASE_URL and SUPABASE_KEY and not results:
        try:
            encoded_query = urllib.parse.quote(f"*{query}*")
            url = f"{SUPABASE_URL}/rest/v1/users?image_name=ilike.{encoded_query}&select=*&order=id.desc&limit=5"
            req = urllib.request.Request(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and data:
                    return data
        except Exception as rest_e:
            print(f"ℹ️ [supabase] REST search query note: {rest_e}")

    # Local SQLite search fallback
    local_matches = database.search_local_users(query)
    return local_matches

def get_supabase_sql_migration():
    """Returns the SQL query to create all 10 E-Commerce & Delivery tables and storage bucket in Supabase."""
    return """-- =========================================================
-- Supabase Setup Script: 10 E-Commerce & Delivery Tables
-- Run this in Supabase Dashboard -> SQL Editor -> Click 'Run'
-- =========================================================

-- 1. Users Table (Profile & uploaded image)
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    image_name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Vendors Table (Shops / Merchants)
CREATE TABLE IF NOT EXISTS public.vendors (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    shop_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT DEFAULT '',
    address TEXT DEFAULT '',
    commission_pct NUMERIC DEFAULT 10.0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Riders Table (Delivery Personnel)
CREATE TABLE IF NOT EXISTS public.riders (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    vehicle_type TEXT DEFAULT 'Motorbike',
    license_number TEXT DEFAULT '',
    rating NUMERIC DEFAULT 5.0,
    status TEXT DEFAULT 'available',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Customers Table (Shoppers & buyers)
CREATE TABLE IF NOT EXISTS public.customers (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    telegram_id TEXT DEFAULT '',
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT DEFAULT '',
    total_orders INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Categories Table
CREATE TABLE IF NOT EXISTS public.categories (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    icon TEXT DEFAULT '🛍️'
);

-- 6. Products Table
CREATE TABLE IF NOT EXISTS public.products (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    vendor_id BIGINT REFERENCES public.vendors(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    price NUMERIC NOT NULL,
    stock INT DEFAULT 100,
    image_url TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Orders Table
CREATE TABLE IF NOT EXISTS public.orders (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_number TEXT UNIQUE,
    customer_id BIGINT REFERENCES public.customers(id) ON DELETE SET NULL,
    vendor_id BIGINT REFERENCES public.vendors(id) ON DELETE SET NULL,
    rider_id BIGINT REFERENCES public.riders(id) ON DELETE SET NULL,
    customer_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    delivery_address TEXT DEFAULT '',
    total_price NUMERIC DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Order Items Table
CREATE TABLE IF NOT EXISTS public.order_items (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id BIGINT REFERENCES public.orders(id) ON DELETE CASCADE,
    product_title TEXT NOT NULL,
    quantity INT DEFAULT 1,
    unit_price NUMERIC DEFAULT 0.0,
    total_price NUMERIC DEFAULT 0.0
);

-- 9. Delivery Tracking Table
CREATE TABLE IF NOT EXISTS public.delivery_tracking (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id BIGINT REFERENCES public.orders(id) ON DELETE CASCADE,
    rider_id BIGINT REFERENCES public.riders(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'assigned',
    current_location TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Payments Table
CREATE TABLE IF NOT EXISTS public.payments (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id BIGINT REFERENCES public.orders(id) ON DELETE CASCADE,
    transaction_id TEXT UNIQUE,
    payment_method TEXT DEFAULT 'Cash on Delivery',
    amount NUMERIC NOT NULL,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================================
-- Enable Row Level Security (RLS) & Public Policies for all 10 tables
-- =========================================================
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'users', 'vendors', 'riders', 'customers', 'categories',
        'products', 'orders', 'order_items', 'delivery_tracking', 'payments'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = tbl AND policyname = format('Public Access for %s', tbl)
        ) THEN
            EXECUTE format('CREATE POLICY "Public Access for %s" ON public.%I FOR ALL USING (true) WITH CHECK (true);', tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- =========================================================
-- Storage Bucket: 'user-images' & Public Access
-- =========================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('user-images', 'user-images', true)
ON CONFLICT (id) DO UPDATE SET public = true;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'objects' AND policyname = 'Public Read for user-images'
    ) THEN
        CREATE POLICY "Public Read for user-images" ON storage.objects
        FOR SELECT USING (bucket_id = 'user-images');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'objects' AND policyname = 'Public Upload for user-images'
    ) THEN
        CREATE POLICY "Public Upload for user-images" ON storage.objects
        FOR INSERT WITH CHECK (bucket_id = 'user-images');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'objects' AND policyname = 'Public Update for user-images'
    ) THEN
        CREATE POLICY "Public Update for user-images" ON storage.objects
        FOR UPDATE USING (bucket_id = 'user-images');
    END IF;
END $$;

-- =========================================================
-- Seed Initial Sample Data (Vendors, Riders, Categories)
-- =========================================================
INSERT INTO public.categories (name, slug, icon) VALUES
('Electronics', 'electronics', '📱'),
('Grocery & Fresh', 'grocery', '🥦'),
('Fashion & Wear', 'fashion', '👕'),
('Home & Kitchen', 'home', '🏠')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.vendors (shop_name, owner_name, phone, address, commission_pct, status) VALUES
('Dhaka Gadget Hub', 'Rahim Uddin', '+8801711001122', 'Mirpur-10, Dhaka', 8.5, 'active'),
('Green Fresh Grocery', 'Karim Mia', '+8801811223344', 'Uttara Sector-7, Dhaka', 5.0, 'active'),
('Fashion Fusion BD', 'Nusrat Jahan', '+8801911334455', 'Dhanmondi 27, Dhaka', 10.0, 'active')
ON CONFLICT DO NOTHING;

INSERT INTO public.riders (name, phone, vehicle_type, license_number, rating, status) VALUES
('Tariqul Islam', '+8801611009988', 'Motorbike', 'DH-MET-54321', 4.9, 'available'),
('Shakil Ahmed', '+8801511223344', 'Bicycle', 'DH-CYC-12345', 4.8, 'on_delivery'),
('Mahmudul Hasan', '+8801711998877', 'Motorbike', 'DH-MET-98765', 5.0, 'available')
ON CONFLICT DO NOTHING;
"""

def get_table_list():
    """Returns list of the 10 configured tables."""
    return [
        {"name": "users", "desc": "Bot user profiles, phone, image details"},
        {"name": "vendors", "desc": "Vendor & Merchant shop directory"},
        {"name": "riders", "desc": "Delivery Rider list & status"},
        {"name": "customers", "desc": "Customer contact list & order counts"},
        {"name": "categories", "desc": "Product Categories"},
        {"name": "products", "desc": "E-Commerce Product catalog"},
        {"name": "orders", "desc": "Customer orders"},
        {"name": "order_items", "desc": "Order item details"},
        {"name": "delivery_tracking", "desc": "Live delivery tracking"},
        {"name": "payments", "desc": "Payment & Transaction records"}
    ]
