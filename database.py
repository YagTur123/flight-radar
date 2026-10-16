#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Radar 2.0 - SQLite WAL Time-Series Database Layer
Thread-safe, high-concurrency, ACID-compliant database for flight tracking,
price history time-series, campaign intelligence, and system settings.
"""

import os
import sqlite3
import json
import math
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'flight_radar.db')
TRACKS_JSON = os.path.join(BASE_DIR, 'tracked_flights.json')
CAMPAIGNS_JSON = os.path.join(BASE_DIR, 'seen_campaigns.json')

def get_connection():
    """Returns a SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Initializes schema and runs automatic migration from legacy JSON files."""
    conn = get_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS routes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT,
            target_price REAL NOT NULL,
            last_price REAL,
            lowest_recorded REAL,
            last_checked TEXT,
            airline TEXT,
            flight_time TEXT,
            search_url TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id TEXT NOT NULL,
            price REAL NOT NULL,
            airline TEXT,
            market TEXT DEFAULT 'TR',
            recorded_at TEXT NOT NULL,
            FOREIGN KEY(route_id) REFERENCES routes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_history_route_time ON price_history(route_id, recorded_at);

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            link TEXT,
            date TEXT,
            discovered_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
    conn.close()

    # Otomatik JSON Migrasyonu
    migrate_from_json_if_needed()

def migrate_from_json_if_needed():
    """Migrates tracked_flights.json and seen_campaigns.json if database is empty."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM routes")
    count = cur.fetchone()[0]

    if count == 0 and os.path.exists(TRACKS_JSON):
        try:
            with open(TRACKS_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    r_id = str(item.get('id', ''))
                    if not r_id:
                        continue
                    best = item.get('best_flight') or {}
                    airline = item.get('airline') or best.get('airline') or 'Havayolu'
                    flight_time = item.get('flight_time') or (
                        f"{best.get('departure_time')} - {best.get('arrival_time')}" if best.get('departure_time') else ''
                    )
                    
                    cur.execute("""
                    INSERT OR REPLACE INTO routes (
                        id, title, origin, destination, departure_date, return_date,
                        target_price, last_price, lowest_recorded, last_checked,
                        airline, flight_time, search_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r_id,
                        item.get('title', 'Rota'),
                        item.get('origin', 'ADB'),
                        item.get('destination', 'IST'),
                        item.get('departure_date', ''),
                        item.get('return_date'),
                        item.get('target_price', 0),
                        item.get('last_price') or item.get('current_price'),
                        item.get('lowest_recorded'),
                        item.get('last_checked'),
                        airline,
                        flight_time,
                        item.get('search_url')
                    ))

                    # Geçmiş Fiyatlar
                    for h in item.get('price_history', []):
                        p = h.get('price')
                        if p:
                            cur.execute("""
                            INSERT INTO price_history (route_id, price, airline, recorded_at)
                            VALUES (?, ?, ?, ?)
                            """, (r_id, float(p), h.get('airline', airline), h.get('time', '')))
                conn.commit()
                print(f"✓ SQLite: {len(data)} rota tracked_flights.json'dan aktarıldı.")
        except Exception as e:
            print(f"⚠️ JSON rota migrasyon hatası: {e}")

    # Kampanyalar
    cur.execute("SELECT COUNT(*) FROM campaigns")
    c_count = cur.fetchone()[0]
    if c_count == 0 and os.path.exists(CAMPAIGNS_JSON):
        try:
            with open(CAMPAIGNS_JSON, 'r', encoding='utf-8') as f:
                c_data = json.load(f)
            items = c_data.get('seen', []) if isinstance(c_data, dict) else c_data
            if isinstance(items, list):
                for c in items:
                    title = c if isinstance(c, str) else c.get('title', '')
                    if title:
                        link = c.get('link') if isinstance(c, dict) else None
                        date = c.get('date') if isinstance(c, dict) else None
                        cur.execute("INSERT OR IGNORE INTO campaigns (title, link, date) VALUES (?, ?, ?)", (title, link, date))
                conn.commit()
                print(f"✓ SQLite: {len(items)} kampanya seen_campaigns.json'dan aktarıldı.")
        except Exception as e:
            print(f"⚠️ JSON kampanya migrasyon hatası: {e}")

    conn.close()

# ==========================================
# ROTA CRUD FONKSİYONLARI
# ==========================================
def get_all_routes():
    """Tüm aktif rotaları geçmiş fiyatları ile birlikte sözlük listesi olarak döner."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM routes WHERE active = 1 ORDER BY created_at DESC")
    rows = cur.fetchall()

    routes = []
    for r in rows:
        d = dict(r)
        # Geçmiş Fiyatlar
        cur.execute("SELECT price, airline, market, recorded_at FROM price_history WHERE route_id = ? ORDER BY id ASC", (d['id'],))
        h_rows = cur.fetchall()
        d['price_history'] = [{'time': h['recorded_at'], 'price': h['price'], 'airline': h['airline'], 'market': h['market']} for h in h_rows]
        d['current_price'] = d['last_price']
        
        # Best flight yapısı
        d['best_flight'] = {
            'airline': d.get('airline'),
            'price': d.get('last_price'),
            'departure_time': d.get('flight_time').split(' - ')[0] if d.get('flight_time') and ' - ' in d.get('flight_time') else '',
            'arrival_time': d.get('flight_time').split(' - ')[1] if d.get('flight_time') and ' - ' in d.get('flight_time') else ''
        }
        routes.append(d)
    conn.close()
    return routes

def get_route(route_id):
    """Belirli bir rotayı geçmişiyle çeker."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM routes WHERE id = ?", (route_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    cur.execute("SELECT price, airline, market, recorded_at FROM price_history WHERE route_id = ? ORDER BY id ASC", (route_id,))
    h_rows = cur.fetchall()
    d['price_history'] = [{'time': h['recorded_at'], 'price': h['price'], 'airline': h['airline'], 'market': h['market']} for h in h_rows]
    d['current_price'] = d['last_price']
    d['best_flight'] = {
        'airline': d.get('airline'),
        'price': d.get('last_price')
    }
    conn.close()
    return d

def add_route(data):
    """Yeni rota ekler."""
    conn = get_connection()
    cur = conn.cursor()
    r_id = data.get('id') or f"trk_{data['origin'].lower()}_{data['destination'].lower()}_{int(datetime.now().timestamp())}"
    
    cur.execute("""
    INSERT INTO routes (
        id, title, origin, destination, departure_date, return_date,
        target_price, last_price, lowest_recorded, last_checked,
        airline, flight_time, search_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r_id,
        data.get('title', f"{data['origin']} - {data['destination']}"),
        data['origin'].upper().strip(),
        data['destination'].upper().strip(),
        data['departure_date'].strip(),
        data.get('return_date'),
        float(data.get('target_price', 0)),
        data.get('last_price'),
        data.get('lowest_recorded'),
        data.get('last_checked') or datetime.now().strftime('%Y-%m-%d %H:%M'),
        data.get('airline'),
        data.get('flight_time'),
        data.get('search_url')
    ))

    if data.get('last_price'):
        time_str = datetime.now().strftime('%d.%m %H:%M')
        cur.execute("""
        INSERT INTO price_history (route_id, price, airline, recorded_at)
        VALUES (?, ?, ?, ?)
        """, (r_id, float(data['last_price']), data.get('airline', 'Havayolu'), time_str))

    conn.commit()
    conn.close()
    sync_to_legacy_json()
    return r_id

def delete_route(route_id):
    """Rotayı ve geçmişini siler."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM routes WHERE id = ?", (route_id,))
    conn.commit()
    conn.close()
    sync_to_legacy_json()
    return True

def update_route_price(route_id, price, airline, flight_time=None, search_url=None, market='TR'):
    """Rotanın güncel fiyatını ve zaman serisi geçmişini günceller."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT lowest_recorded FROM routes WHERE id = ?", (route_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    lowest = row['lowest_recorded']
    new_lowest = min(lowest, price) if lowest is not None else price
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    time_stamp = datetime.now().strftime('%d.%m %H:%M')

    cur.execute("""
    UPDATE routes SET
        last_price = ?,
        lowest_recorded = ?,
        last_checked = ?,
        airline = COALESCE(?, airline),
        flight_time = COALESCE(?, flight_time),
        search_url = COALESCE(?, search_url)
    WHERE id = ?
    """, (price, new_lowest, now_str, airline, flight_time, search_url, route_id))

    cur.execute("""
    INSERT INTO price_history (route_id, price, airline, market, recorded_at)
    VALUES (?, ?, ?, ?, ?)
    """, (route_id, price, airline, market, time_stamp))

    conn.commit()
    conn.close()
    sync_to_legacy_json()
    return True

# ==========================================
# KAMPANYA FONKSİYONLARI
# ==========================================
def get_all_campaigns(limit=30):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, link, date FROM campaigns ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_campaign(title, link=None, date=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO campaigns (title, link, date) VALUES (?, ?, ?)", (title, link, date))
        conn.commit()
        return True
    finally:
        conn.close()

# ==========================================
# AYARLAR (SETTINGS) FONKSİYONLARI
# ==========================================
def get_setting(key, default=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    return True

# ==========================================
# GERİYE DÖNÜK JSON EŞİTLEME (SYNC)
# ==========================================
def sync_to_legacy_json():
    """Geriye dönük uyumluluk için güncel SQLite verisini tracked_flights.json'a yazar."""
    try:
        tracks = get_all_routes()
        with open(TRACKS_JSON, 'w', encoding='utf-8') as f:
            json.dump(tracks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Legacy JSON sync error: {e}")

if __name__ == '__main__':
    init_db()
    routes = get_all_routes()
    print(f"SQLite DB initialized. Total active routes: {len(routes)}")
