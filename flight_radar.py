import sys
import os
import json
import time
import subprocess
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import traceback
import math

from flight_crawler import search_flights
import database
import telegram_bot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKS_FILE = os.path.join(BASE_DIR, 'tracked_flights.json')
RSS_DB_FILE = os.path.join(BASE_DIR, 'seen_campaigns.json')
LOG_FILE = os.path.join(BASE_DIR, 'radar.log')

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except Exception as e:
        print(f"⚠️ Log yazma hatası: {e}")

def send_notification(title, content, url=None):
    try:
        cmd = ['termux-notification', '--title', title, '--content', content]
        if url:
            cmd.extend(['--action', url])
        subprocess.run(cmd, check=False)
    except Exception as e:
        log(f"⚠️ Bildirim gönderme hatası: {e}")

def load_json_file(filepath, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log(f"⚠️ JSON okuma hatası ({filepath}): {e}")
    return default

def clean_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    return obj

def load_rss_db():
    raw = load_json_file(RSS_DB_FILE, {})
    if isinstance(raw, list):
        return {'seen': raw, 'bulletin_sent': {}}
    elif isinstance(raw, dict):
        if 'seen' not in raw:
            raw['seen'] = []
        if 'bulletin_sent' not in raw:
            raw['bulletin_sent'] = {}
        return raw
    return {'seen': [], 'bulletin_sent': {}}

def save_json_file(filepath, data):
    try:
        cleaned = clean_for_json(data)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ JSON yazma hatası ({filepath}): {e}")

def fetch_rss_campaigns():
    rss_url = "https://news.google.com/rss/search?q=pegasus+ajet+kampanya&hl=tr&gl=TR&ceid=TR:tr"
    rss_db = load_rss_db()
    seen_set = set(rss_db.get('seen', []))

    new_items = []

    try:
        req = urllib.request.Request(rss_url, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14) FlightRadar/2.0'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            for item in items:
                title_el = item.find('title')
                link_el = item.find('link')
                if title_el is None:
                    continue
                title = title_el.text.strip()
                link = link_el.text.strip() if link_el is not None else ""
                key = title.split(" - ")[0].strip().lower()
                if key not in seen_set:
                    seen_set.add(key)
                    new_items.append({'title': title, 'link': link})

        # Son 300 kaydı sakla
        rss_db['seen'] = list(seen_set)[-300:]
        save_json_file(RSS_DB_FILE, rss_db)
        
        # SQLite DB'ye de kaydet
        for item in new_items:
            database.add_campaign(item['title'], item.get('link'))
    except Exception as e:
        log(f"⚠️ RSS tarama hatası: {e}")

    for item in new_items:
        title = item['title']
        link = item['link']
        log(f"📢 Yeni kampanya tespit edildi: {title}")
        send_notification("✈️ Yeni Kampanya!", title, link)

    return new_items

def run_tracked_flights_scan(force_bulletin=False):
    database.init_db()
    tracks = database.get_all_routes()

    if not tracks:
        log("ℹ️ Takip edilen aktif uçuş bulunamadı.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    rss_db = load_rss_db()
    bulletin_sent_today = rss_db.get('bulletin_sent', {}).get(today_str, False)

    for track in tracks:
        origin = track.get('origin', 'ADB')
        destination = track.get('destination', 'IST')
        departure_date = track.get('departure_date', '')
        return_date = track.get('return_date', None)
        target_price = track.get('target_price', 0)
        title = track.get('title', f"{origin} ⇄ {destination}")

        if not departure_date:
            continue

        log(f"🔎 Uçuş taranıyor: {title} ({departure_date} -> {return_date or 'Tek Yön'})")
        try:
            res = search_flights(origin, destination, departure_date, return_date)
        except Exception as e:
            log(f"⚠️ Uçuş arama hatası ({title}): {e}")
            continue

        if not res.get('ok') or not res.get('flights'):
            log(f"ℹ️ Uygun uçuş listelenemedi: {title}")
            continue

        flights = res['flights']
        cheapest = flights[0] # Fiyata göre sıralı geliyor
        current_price = cheapest.get('price', 0)
        lowest_recorded = track.get('lowest_recorded', float('inf'))
        airline = cheapest.get('airline', 'Havayolu')
        dep_time = cheapest.get('departure_time', '')
        arr_time = cheapest.get('arrival_time', '')
        flight_time = f"{dep_time} - {arr_time}" if dep_time else ""
        search_url = res.get('search_url', '')

        # Hedef fiyatın altına düştü mü?
        if current_price <= target_price:
            msg = f"✈️ Bilet Hedef Fiyatın Altında!\n{title}: {current_price} TL (Hedef: {target_price} TL)\n{airline} ({dep_time} - {arr_time})"
            log(f"🎯 {msg}")
            send_notification("✈️ Bilet Hedef Fiyatın Altında!", msg, url=search_url)
            telegram_bot.dispatch_deal_alert(track, current_price, target_price, lowest_recorded, search_url)

        # Yeni dip fiyat (rekor ucuzluk) görüldü mü?
        if current_price < lowest_recorded:
            msg = f"🔥 Yeni Rekor Dip Fiyat! {title}: {current_price} TL ({airline})"
            log(f"🔥 {msg}")
            send_notification("🔥 Yeni Rekor Dip Fiyat!", msg, url=search_url)
            telegram_bot.dispatch_deal_alert(track, current_price, target_price, lowest_recorded, search_url)

        # SQLite veritabanına ve zaman serisine kaydet
        database.update_route_price(track['id'], current_price, airline, flight_time, search_url)

    # Günlük bülten kontrolü (saat 9 veya sonrası ve bugün henüz gönderilmediyse)
    if force_bulletin or (datetime.now().hour >= 9 and not bulletin_sent_today):
        summary_lines = []
        for track in tracks:
            t_title = track.get('title', f"{track.get('origin')} ⇄ {track.get('destination')}")
            best = track.get('best_flight', {})
            if best:
                price = best.get('price', 0)
                airline = best.get('airline', '')
                dep = best.get('departure_time', '')
                arr = best.get('arrival_time', '')
                summary_lines.append(f"• {t_title}: {price} TL ({airline} {dep}-{arr})")
            else:
                summary_lines.append(f"• {t_title}: Fiyat henüz yok")

        if summary_lines:
            summary = "\n".join(summary_lines)
            log("🌅 Günlük bülten gönderiliyor...")
            send_notification("🌅 Günlük Seyahat Özeti", summary)
            rss_db['bulletin_sent'][today_str] = True
            save_json_file(RSS_DB_FILE, rss_db)

def main():
    args = sys.argv[1:]

    if '--daemon' in args:
        log("🚀 Daemon modu başlatıldı (2 saatte bir döngü)")
        while True:
            try:
                fetch_rss_campaigns()
                run_tracked_flights_scan()

                log("⏳ 2 saat bekleniyor...")
                time.sleep(7200)
            except KeyboardInterrupt:
                log("🛑 Daemon durduruldu.")
                break
            except Exception as e:
                log(f"⚠️ Daemon hatası: {e}")
                traceback.print_exc()
                time.sleep(60)

    elif '--scan' in args:
        log("🔍 Tek seferlik tarama başlatıldı")
        fetch_rss_campaigns()
        run_tracked_flights_scan()
        log("✅ Tarama tamamlandı.")

    elif '--bulletin' in args:
        log("📢 Günlük bülten manuel tetiklendi")
        run_tracked_flights_scan(force_bulletin=True)

    else:
        print("Kullanım:")
        print("  python flight_radar.py [--daemon|--scan|--bulletin]")

if __name__ == '__main__':
    main()
