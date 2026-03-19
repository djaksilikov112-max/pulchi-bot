import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from config import config

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            phone TEXT, age INTEGER, region TEXT, employment TEXT,
            is_subscribed INTEGER DEFAULT 0, sub_type TEXT,
            sub_expires TEXT, prev_sub_end TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            short_name TEXT, logo_emoji TEXT DEFAULT '🏦',
            credit_types TEXT, min_rate REAL, max_rate REAL,
            min_amount INTEGER, max_amount INTEGER,
            min_term INTEGER, max_term INTEGER,
            requirements TEXT, advantages TEXT, regions TEXT,
            phone TEXT, website TEXT, is_active INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, provider TEXT, transaction_id TEXT,
            amount INTEGER, sub_type TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')), paid_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS ai_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, role TEXT, message TEXT,
            created_at TEXT DEFAULT (datetime('now')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT, user_id INTEGER, data TEXT,
            created_at TEXT DEFAULT (datetime('now')))""")
        conn.commit()
    _seed_data()
    logger.info("Ma'lumotlar bazasi tayyor.")

def _seed_data():
    with get_connection() as conn:
        c = conn.cursor()
        banks = [
            ("Agrobank","Agrobank","🌾",'["micro","unemployed","business"]',24.0,28.0,1000000,500000000,6,84,"O'zbekiston fuqarosi, 18-65 yosh","Temir daftar, Ishga marhamat",'["Toshkent","Samarqand"]',"1200","https://agrobank.uz"),
            ("Mikrokreditbank","MKB","🏦",'["micro","unemployed"]',27.0,32.0,500000,100000000,3,60,"O'zbekiston fuqarosi, 18-60 yosh","Ishsizlar uchun maxsus dasturlar",'["Toshkent","Samarqand"]',"1202","https://mikrokreditbank.uz"),
            ("Xalq Banki","Xalq","🏛️",'["micro","business","ipoteka"]',29.0,33.0,1000000,1000000000,12,120,"O'zbekiston fuqarosi, 18-65 yosh","Keng tarmoq, davlat kafolati",'["Toshkent","Samarqand"]',"1209","https://xb.uz"),
            ("Anor Bank","Anor","🍎",'["micro","business","auto"]',27.0,31.0,1000000,300000000,6,60,"O'zbekiston fuqarosi, 21-65 yosh","To'liq onlayn ariza",'["Toshkent","Samarqand"]',"71 200-00-00","https://anorbank.uz"),
            ("Kapitalbank","Kapital","💼",'["micro","business","auto","ipoteka"]',26.0,30.0,2000000,500000000,6,84,"O'zbekiston fuqarosi, 21-65 yosh","Barcha kredit turlari",'["Toshkent","Samarqand"]',"78 140-00-00","https://kapitalbank.uz"),
            ("Ipoteka Bank","Ipoteka","🏠",'["ipoteka","business"]',25.0,28.0,50000000,3000000000,60,240,"O'zbekiston fuqarosi, 21-65 yosh","Ipotekaga ixtisoslashgan",'["Toshkent","Samarqand"]',"1212","https://ipotekabank.uz"),
            ("SQB","SQB","🏗️",'["business","auto","ipoteka"]',23.0,27.0,5000000,2000000000,12,120,"O'zbekiston fuqarosi, 21-65 yosh","Eng past stavkalar",'["Toshkent","Samarqand"]',"1203","https://sqb.uz"),
            ("Asaka Bank","Asaka","🚗",'["auto","business","micro"]',28.0,32.0,5000000,500000000,12,84,"O'zbekiston fuqarosi, 21-60 yosh","Avtokreditga ixtisoslashgan",'["Toshkent","Samarqand"]',"71 207-00-00","https://asakabank.uz"),
            ("Hamkorbank","Hamkor","🤝",'["micro","business","unemployed"]',26.0,30.0,500000,200000000,3,60,"O'zbekiston fuqarosi, 18-63 yosh","Mikrokredit uchun ixtisoslashgan",'["Toshkent","Samarqand"]',"71 202-07-77","https://hamkorbank.uz"),
            ("Tenge Bank","Tenge","💳",'["micro","business","auto"]',25.0,29.0,1000000,300000000,6,72,"O'zbekiston fuqarosi, 21-63 yosh","Onlayn xizmatlar",'["Toshkent","Samarqand"]',"71 200-10-10","https://tengebank.uz"),
        ]
        c.executemany("""INSERT OR IGNORE INTO banks
            (name,short_name,logo_emoji,credit_types,min_rate,max_rate,
            min_amount,max_amount,min_term,max_term,
            requirements,advantages,regions,phone,website)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", banks)
        conn.commit()

def get_user(user_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def upsert_user(user_id, username=None, full_name=None):
    with get_connection() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if existing:
            conn.execute("UPDATE users SET last_active=datetime('now'), username=COALESCE(?,username), full_name=COALESCE(?,full_name) WHERE user_id=?", (username, full_name, user_id))
        else:
            conn.execute("INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)", (user_id, username, full_name))
        conn.commit()

def update_user_profile(user_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {fields} WHERE user_id=?", values)
        conn.commit()

def is_subscribed(user_id):
    user = get_user(user_id)
    if not user or not user["is_subscribed"]:
        return False
    if user["sub_expires"]:
        try:
            exp = datetime.fromisoformat(user["sub_expires"])
            if datetime.now() > exp:
                with get_connection() as conn:
                    conn.execute("UPDATE users SET is_subscribed=0, prev_sub_end=sub_expires WHERE user_id=?", (user_id,))
                    conn.commit()
                return False
        except Exception:
            pass
    return True

def activate_subscription(user_id, sub_type):
    days_map = {"1day": 1, "3day": 3, "weekly": 7}
    days = days_map.get(sub_type, 1)
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_subscribed=1, sub_type=?, sub_expires=? WHERE user_id=?", (sub_type, expires, user_id))
        conn.commit()

def has_reconnect_discount(user_id):
    user = get_user(user_id)
    if not user or not user["prev_sub_end"]:
        return False
    try:
        prev = datetime.fromisoformat(user["prev_sub_end"])
        diff = datetime.now() - prev
        return 0 < diff.days <= 7
    except Exception:
        return False

def get_all_banks(active_only=True):
    cond = "WHERE is_active=1" if active_only else ""
    with get_connection() as conn:
        rows = conn.execute(f"SELECT * FROM banks {cond} ORDER BY min_rate").fetchall()
        return [dict(r) for r in rows]

def get_bank(bank_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
        return dict(row) if row else None

def update_bank_rate(bank_id, min_rate, max_rate):
    with get_connection() as conn:
        conn.execute("UPDATE banks SET min_rate=?, max_rate=?, updated_at=datetime('now') WHERE id=?", (min_rate, max_rate, bank_id))
        conn.commit()

def get_banks_by_credit_type(credit_type_code):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM banks WHERE credit_types LIKE ? AND is_active=1 ORDER BY min_rate", (f"%{credit_type_code}%",)).fetchall()
        return [dict(r) for r in rows]

def create_payment(user_id, provider, amount, sub_type):
    with get_connection() as conn:
        c = conn.execute("INSERT INTO payments (user_id, provider, amount, sub_type) VALUES (?,?,?,?)", (user_id, provider, amount, sub_type))
        conn.commit()
        return c.lastrowid

def confirm_payment(payment_id, transaction_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if not row:
            return
        conn.execute("UPDATE payments SET status='paid', transaction_id=?, paid_at=datetime('now') WHERE id=?", (transaction_id, payment_id))
        conn.commit()
        activate_subscription(row["user_id"], row["sub_type"])

def save_ai_message(user_id, role, message):
    with get_connection() as conn:
        conn.execute("INSERT INTO ai_sessions (user_id, role, message) VALUES (?,?,?)", (user_id, role, message))
        conn.commit()

def get_ai_history(user_id, limit=10):
    with get_connection() as conn:
        rows = conn.execute("SELECT role, message FROM ai_sessions WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
        return [{"role": r["role"], "content": r["message"]} for r in reversed(rows)]

def clear_ai_history(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ai_sessions WHERE user_id=?", (user_id,))
        conn.commit()

def log_event(event, user_id=None, data=None):
    with get_connection() as conn:
        conn.execute("INSERT INTO stats (event, user_id, data) VALUES (?,?,?)", (event, user_id, data))
        conn.commit()

def get_stats():
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_subs = conn.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1").fetchone()[0]
        total_revenue = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'").fetchone()[0]
        calc_count = conn.execute("SELECT COUNT(*) FROM stats WHERE event='calc_used'").fetchone()[0]
        ai_count = conn.execute("SELECT COUNT(*) FROM stats WHERE event='ai_used'").fetchone()[0]
        today_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM stats WHERE date(created_at)=date('now')").fetchone()[0]
        return {"total_users": total_users, "active_subs": active_subs, "total_revenue": total_revenue, "calc_count": calc_count, "ai_count": ai_count, "today_users": today_users}
