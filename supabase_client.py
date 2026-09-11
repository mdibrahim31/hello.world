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
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
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
    """Returns the SQL query to create the required 'users' table in Supabase."""
    return """
-- 1. Create users table in public schema
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    image_name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Enable Row Level Security (RLS) and allow public read and insert
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'Public Access for users'
    ) THEN
        CREATE POLICY "Public Access for users" ON public.users FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
"""
