import os
import sys
import subprocess
import time
import math
import urllib.parse
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'radar.log')
RADAR_SCRIPT = os.path.join(BASE_DIR, 'flight_radar.py')

def get_daemon_status():
    """Arka plan radarı (daemon) sürecini pgrep ile kontrol eder."""
    try:
        res = subprocess.run(['pgrep', '-fa', '[f]light_radar.py --daemon'], capture_output=True, text=True)
        lines = [l.strip() for l in res.stdout.strip().split('\n') if l.strip()]
        if lines:
            parts = lines[0].split()
            pid = int(parts[0])
            return {'running': True, 'pid': pid}
        return {'running': False, 'pid': None}
    except Exception as e:
        return {'running': False, 'pid': None, 'error': str(e)}

def start_daemon():
    """Radarı arka planda yeni bir oturumda (setsid / daemon) başlatır."""
    status = get_daemon_status()
    if status['running']:
        return status

    try:
        log_fp = open(LOG_FILE, 'a', encoding='utf-8')
        subprocess.Popen(
            [sys.executable, '-u', RADAR_SCRIPT, '--daemon'],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        time.sleep(0.6)
    except Exception as e:
        return {'running': False, 'pid': None, 'error': str(e)}

    return get_daemon_status()

def stop_daemon():
    """Arka plan radarı sürecini zarifçe sonlandırır."""
    status = get_daemon_status()
    if not status['running']:
        return {'running': False, 'pid': None, 'stopped': True}

    pid = status['pid']
    try:
        os.kill(pid, 15) # SIGTERM
        time.sleep(0.5)
        new_status = get_daemon_status()
        if new_status['running']:
            os.kill(pid, 9) # SIGKILL fallback
            time.sleep(0.3)
            new_status = get_daemon_status()
        return {'running': new_status['running'], 'pid': new_status['pid'], 'stopped': not new_status['running']}
    except Exception as e:
        return {'running': False, 'error': str(e)}

def get_recent_logs(max_lines=40):
    """radar.log dosyasından son N satırı döner."""
    if not os.path.exists(LOG_FILE):
        return ["Henüz log kaydı oluşturulmadı."]
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return [l.strip() for l in lines[-max_lines:]]
    except Exception as e:
        return [f"Log okunamadı: {e}"]

def evaluate_deal(track):
    """
    Fiyat geçmişi ve hedef fiyata göre akıllı analiz ve editoryal rozet üretir.
    """
    price = track.get('current_price') or track.get('last_price')
    target = track.get('target_price', 0)
    lowest = track.get('lowest_recorded')
    history = track.get('price_history', [])

    if not price:
        return {
            'badge': '<span class="deal-badge badge-neutral">⏳ FİYAT BEKLENİYOR</span>',
            'status': 'unknown',
            'label': 'Bekleniyor',
            'desc': 'İlk tarama tamamlanınca analiz gösterilecek.'
        }

    prices = [h['price'] for h in history if isinstance(h, dict) and 'price' in h and h['price']]
    avg_price = int(sum(prices) / len(prices)) if (prices and len(prices) > 0) else (price or 0)
    min_price = min(prices) if prices else (price or 0)
    max_price = max(prices) if prices else (price or 0)

    diff = (price - target) if (price is not None and target is not None) else 0
    diff_pct = round(((price - target) / target) * 100, 1) if (target and target > 0 and price is not None) else 0

    if price <= target:
        badge = f'<span class="deal-badge badge-success">🎯 HEDEF ALTI ({price} TL)</span>'
        status = 'deal'
        label = 'Alım Fırsatı'
        desc = f'Hedefinizin {abs(diff)} TL altındasınız! Kaçırmadan değerlendirin.'
    elif lowest and price <= lowest:
        badge = f'<span class="deal-badge badge-success">🔥 REKOR DİP FİYAT</span>'
        status = 'record_low'
        label = 'Tarihi Dip'
        desc = 'Kaydedilen en ucuz bilet seviyesinde.'
    elif price <= target * 1.10 or price <= avg_price:
        badge = f'<span class="deal-badge badge-warning">🟡 MAKUL SEVİYE (+%{abs(diff_pct)})</span>'
        status = 'fair'
        label = 'Takipte Kal'
        desc = f'Hedefe {diff} TL uzaklıkta, ortalama piyasa fiyatında.'
    else:
        badge = f'<span class="deal-badge badge-danger">🔴 YÜKSEK FİYAT (+%{diff_pct})</span>'
        status = 'high'
        label = 'Fiyat Şişkin'
        desc = f'Ortalama ({avg_price} TL) ve hedefin üzerinde, indirim bekleyin.'

    return {
        'badge': badge,
        'status': status,
        'label': label,
        'desc': desc,
        'avg_price': avg_price,
        'min_price': min_price,
        'max_price': max_price,
        'diff': diff,
        'diff_pct': diff_pct
    }

def get_flexible_date_links(origin, destination, dep_date_str, ret_date_str=None):
    """
    Seçilen tarihin ±1 gün varyasyonlarını ve Google Flights linklerini üretir.
    """
    links = []
    try:
        dep_date = datetime.strptime(dep_date_str, '%Y-%m-%d')
        ret_date = datetime.strptime(ret_date_str, '%Y-%m-%d') if ret_date_str else None

        shifts = [(-1, '1 Gün Önce'), (0, 'Orijinal Tarih'), (1, '1 Gün Sonra')]
        for shift, label in shifts:
            new_dep = dep_date + timedelta(days=shift)
            new_dep_str = new_dep.strftime('%Y-%m-%d')

            if ret_date:
                new_ret = ret_date + timedelta(days=shift)
                new_ret_str = new_ret.strftime('%Y-%m-%d')
                q = f"Flights from {origin} to {destination} on {new_dep_str} through {new_ret_str}"
                display_date = f"{new_dep.strftime('%d.%m')} - {new_ret.strftime('%d.%m')}"
            else:
                new_ret_str = None
                q = f"Flights from {origin} to {destination} on {new_dep_str}"
                display_date = new_dep.strftime('%d.%m')

            encoded_q = urllib.parse.quote(q)
            url = f"https://www.google.com/travel/flights?q={encoded_q}&curr=TRY&hl=tr"
            links.append({
                'label': label,
                'dates': display_date,
                'departure': new_dep_str,
                'return': new_ret_str,
                'url': url,
                'is_current': (shift == 0)
            })
    except Exception:
        pass
    return links

# ==========================================
# CLOUDFLARE GLOBAL INTERNET TUNNEL MOTORU
# ==========================================
TUNNEL_LOG = os.path.join(BASE_DIR, 'tunnel.log')
TUNNEL_URL_FILE = os.path.join(BASE_DIR, 'tunnel_url.txt')

def get_tunnel_status():
    """Cloudflare Tunnel durumunu ve güncel public HTTPS URL'sini döner."""
    try:
        res = subprocess.run(['pgrep', '-fa', 'cloudflared tunnel'], capture_output=True, text=True)
        lines = [l.strip() for l in res.stdout.strip().split('\n') if l.strip()]
        if lines:
            parts = lines[0].split()
            pid = int(parts[0])
            url = None
            if os.path.exists(TUNNEL_URL_FILE):
                try:
                    with open(TUNNEL_URL_FILE, 'r', encoding='utf-8') as f:
                        url = f.read().strip()
                except Exception:
                    pass
            return {'running': True, 'pid': pid, 'url': url}
        return {'running': False, 'pid': None, 'url': None}
    except Exception as e:
        return {'running': False, 'pid': None, 'url': None, 'error': str(e)}

def start_tunnel(port=8080):
    """Cloudflare Quick Tunnel başlatır ve public URL'yi tespit eder."""
    status = get_tunnel_status()
    if status['running'] and status.get('url'):
        return status

    try:
        stop_tunnel()
        if os.path.exists(TUNNEL_URL_FILE):
            os.remove(TUNNEL_URL_FILE)

        log_fp = open(TUNNEL_LOG, 'w', encoding='utf-8')
        proc = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', f'http://127.0.0.1:{port}'],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

        tunnel_url = None
        import re
        for _ in range(24):
            time.sleep(0.5)
            if os.path.exists(TUNNEL_LOG):
                try:
                    with open(TUNNEL_LOG, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        m = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', content)
                        if m:
                            tunnel_url = m.group(0)
                            with open(TUNNEL_URL_FILE, 'w', encoding='utf-8') as uf:
                                uf.write(tunnel_url)
                            break
                except Exception:
                    pass

        return {'running': True, 'pid': proc.pid, 'url': tunnel_url}
    except Exception as e:
        return {'running': False, 'pid': None, 'url': None, 'error': str(e)}

def stop_tunnel():
    """Cloudflare Tunnel sürecini sonlandırır."""
    try:
        subprocess.run(['pkill', '-f', 'cloudflared tunnel'], check=False)
        time.sleep(0.4)
        if os.path.exists(TUNNEL_URL_FILE):
            os.remove(TUNNEL_URL_FILE)
        return {'running': False, 'stopped': True}
    except Exception as e:
        return {'running': False, 'error': str(e)}

