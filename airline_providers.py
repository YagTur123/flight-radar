import os
import sys
import re
import socket
import urllib.parse
import urllib.request
import urllib.error
import gzip
import concurrent.futures
import time
import random

# ==========================================
# 1. KAPSAMLI HAVALİMANI VERİTABANI (IATA)
# ==========================================
AIRPORTS = {
    # Türkiye - Büyük Metropoller & Hublar
    'ADB': {'city': 'İzmir', 'name': 'Adnan Menderes Havalimanı', 'country': 'Türkiye', 'popular': True},
    'SAW': {'city': 'İstanbul', 'name': 'Sabiha Gökçen Havalimanı', 'country': 'Türkiye', 'popular': True},
    'IST': {'city': 'İstanbul', 'name': 'İstanbul Havalimanı', 'country': 'Türkiye', 'popular': True},
    'ESB': {'city': 'Ankara', 'name': 'Esenboğa Havalimanı', 'country': 'Türkiye', 'popular': True},
    'AYT': {'city': 'Antalya', 'name': 'Antalya Havalimanı', 'country': 'Türkiye', 'popular': True},
    'BJV': {'city': 'Muğla / Bodrum', 'name': 'Milas-Bodrum Havalimanı', 'country': 'Türkiye', 'popular': True},
    'DLM': {'city': 'Muğla / Dalaman', 'name': 'Dalaman Havalimanı', 'country': 'Türkiye', 'popular': True},
    'TZX': {'city': 'Trabzon', 'name': 'Trabzon Havalimanı', 'country': 'Türkiye', 'popular': True},
    'ADA': {'city': 'Adana', 'name': 'Şakirpaşa Havalimanı', 'country': 'Türkiye', 'popular': True},
    'GZT': {'city': 'Gaziantep', 'name': 'Gaziantep Havalimanı', 'country': 'Türkiye', 'popular': True},

    # Türkiye - Diğer Şehirler
    'NAV': {'city': 'Nevşehir', 'name': 'Kapadokya Havalimanı', 'country': 'Türkiye'},
    'ASR': {'city': 'Kayseri', 'name': 'Erkilet Havalimanı', 'country': 'Türkiye'},
    'DIY': {'city': 'Diyarbakır', 'name': 'Diyarbakır Havalimanı', 'country': 'Türkiye'},
    'ERZ': {'city': 'Erzurum', 'name': 'Erzurum Havalimanı', 'country': 'Türkiye'},
    'GZP': {'city': 'Antalya / Alanya', 'name': 'Gazipaşa-Alanya Havalimanı', 'country': 'Türkiye'},
    'VAN': {'city': 'Van', 'name': 'Ferit Melen Havalimanı', 'country': 'Türkiye'},
    'SZF': {'city': 'Samsun', 'name': 'Çarşamba Havalimanı', 'country': 'Türkiye'},
    'DNZ': {'city': 'Denizli', 'name': 'Çardak Havalimanı', 'country': 'Türkiye'},
    'MLX': {'city': 'Malatya', 'name': 'Malatya Havalimanı', 'country': 'Türkiye'},
    'EZS': {'city': 'Elazığ', 'name': 'Elazığ Havalimanı', 'country': 'Türkiye'},
    'EDO': {'city': 'Balıkesir / Edremit', 'name': 'Koca Seyit Havalimanı', 'country': 'Türkiye'},
    'KCM': {'city': 'Kahramanmaraş', 'name': 'Kahramanmaraş Havalimanı', 'country': 'Türkiye'},
    'ONQ': {'city': 'Zonguldak', 'name': 'Çaycuma Havalimanı', 'country': 'Türkiye'},
    'RZE': {'city': 'Rize / Artvin', 'name': 'Rize-Artvin Havalimanı', 'country': 'Türkiye'},
    'TEQ': {'city': 'Tekirdağ', 'name': 'Çorlu Havalimanı', 'country': 'Türkiye'},
    'USQ': {'city': 'Uşak', 'name': 'Uşak Havalimanı', 'country': 'Türkiye'},
    'MQM': {'city': 'Mardin', 'name': 'Mardin Prof. Dr. Aziz Sancar', 'country': 'Türkiye'},
    'AJI': {'city': 'Ağrı', 'name': 'Ahmed-i Hani Havalimanı', 'country': 'Türkiye'},
    'IGY': {'city': 'Iğdır', 'name': 'Şehit Bülent Aydın Havalimanı', 'country': 'Türkiye'},
    'ISE': {'city': 'Isparta', 'name': 'Süleyman Demirel Havalimanı', 'country': 'Türkiye'},
    'KYA': {'city': 'Konya', 'name': 'Konya Havalimanı', 'country': 'Türkiye'},
    'VAS': {'city': 'Sivas', 'name': 'Nuri Demirağ Havalimanı', 'country': 'Türkiye'},
    'GNY': {'city': 'Şanlıurfa', 'name': 'GAP Havalimanı', 'country': 'Türkiye'},

    # Popüler Yurt Dışı Rotalar
    'BER': {'city': 'Berlin', 'name': 'Brandenburg Havalimanı', 'country': 'Almanya', 'popular': True},
    'FRA': {'city': 'Frankfurt', 'name': 'Frankfurt Havalimanı', 'country': 'Almanya', 'popular': True},
    'MUC': {'city': 'Münih', 'name': 'Franz Josef Strauss', 'country': 'Almanya'},
    'AMS': {'city': 'Amsterdam', 'name': 'Schiphol Havalimanı', 'country': 'Hollanda', 'popular': True},
    'LHR': {'city': 'Londra', 'name': 'Heathrow Havalimanı', 'country': 'İngiltere', 'popular': True},
    'STN': {'city': 'Londra', 'name': 'Stansted Havalimanı', 'country': 'İngiltere'},
    'CDG': {'city': 'Paris', 'name': 'Charles de Gaulle', 'country': 'Fransa', 'popular': True},
    'VIE': {'city': 'Viyana', 'name': 'Schwechat Havalimanı', 'country': 'Avusturya'},
    'DXB': {'city': 'Dubai', 'name': 'Dubai Uluslararası Havalimanı', 'country': 'BAE', 'popular': True},
    'DOH': {'city': 'Doha', 'name': 'Hamad Uluslararası', 'country': 'Katar'},
    'GYD': {'city': 'Bakü', 'name': 'Haydar Aliyev Havalimanı', 'country': 'Azerbaycan', 'popular': True},
    'ATH': {'city': 'Atina', 'name': 'Elefterios Venizelos', 'country': 'Yunanistan'},
    'SKG': {'city': 'Selanik', 'name': 'Makedonya Havalimanı', 'country': 'Yunanistan'},
    'FCO': {'city': 'Roma', 'name': 'Fiumicino Havalimanı', 'country': 'İtalya'},
    'PRG': {'city': 'Prag', 'name': 'Vaclav Havel Havalimanı', 'country': 'Çekya'},
}

def get_airport_display(code):
    code = (code or '').upper().strip()
    if code in AIRPORTS:
        info = AIRPORTS[code]
        return f"{code} - {info['city']} ({info['name']})"
    return code

def get_all_airports_list():
    items = []
    for code, info in AIRPORTS.items():
        items.append({
            'code': code,
            'city': info['city'],
            'name': info['name'],
            'country': info['country'],
            'popular': info.get('popular', False),
            'display': f"{code} - {info['city']} ({info['name']})"
        })
    # Popüler olanları başa al
    items.sort(key=lambda x: (not x['popular'], x['city']))
    return items

# ==========================================
def _clean_code(c):
    return re.sub(r'[^A-Za-z]', '', str(c or '')).upper()[:3]

def _clean_date(d):
    return re.sub(r'[^0-9\-]', '', str(d or ''))[:10]

# ==========================================
# 2. DOĞRUDAN HAVAYOLU REZERVASYON DERİN LİNKLERİ
# ==========================================
def get_pegasus_url(origin, dest, dep_date, ret_date=None):
    """Pegasus Havayolları doğrudan arama ve rezervasyon linki."""
    origin, dest = _clean_code(origin), _clean_code(dest)
    dep_date = _clean_date(dep_date)
    ret_date = _clean_date(ret_date) if ret_date else None
    dep_fmt = dep_date.replace('-', '')
    ret_fmt = ret_date.replace('-', '') if ret_date else ''
    if ret_date:
        return f"https://web.flypgs.com/booking?language=tr&origin={origin}&destination={dest}&departureDate={dep_fmt}&returnDate={ret_fmt}&adultCount=1"
    return f"https://web.flypgs.com/booking?language=tr&origin={origin}&destination={dest}&departureDate={dep_fmt}&adultCount=1"

def get_ajet_url(origin, dest, dep_date, ret_date=None):
    """AJet (AnadoluJet) doğrudan bilet arama linki."""
    if ret_date:
        return f"https://ajet.com/tr/bilet-al?from={origin}&to={dest}&departureDate={dep_date}&returnDate={ret_date}&adult=1"
    return f"https://ajet.com/tr/bilet-al?from={origin}&to={dest}&departureDate={dep_date}&adult=1"

def get_thy_url(origin, dest, dep_date, ret_date=None):
    """Türk Hava Yolları doğrudan rezervasyon linki."""
    if ret_date:
        return f"https://www.turkishairlines.com/tr-tr/ucak-bileti/rezervasyon/?origin={origin}&destination={dest}&departureDate={dep_date}&returnDate={ret_date}&adultCount=1"
    return f"https://www.turkishairlines.com/tr-tr/ucak-bileti/rezervasyon/?origin={origin}&destination={dest}&departureDate={dep_date}&adultCount=1"

def get_sunexpress_url(origin, dest, dep_date, ret_date=None):
    """SunExpress doğrudan arama linki."""
    if ret_date:
        return f"https://www.sunexpress.com/tr/ucak-bileti/?origin={origin}&destination={dest}&departure={dep_date}&return={ret_date}&adults=1"
    return f"https://www.sunexpress.com/tr/ucak-bileti/?origin={origin}&destination={dest}&departure={dep_date}&adults=1"

def get_skyscanner_url(origin, dest, dep_date, ret_date=None):
    """Skyscanner meta-arama linki."""
    dep_clean = dep_date.replace('-', '')[2:]
    if ret_date:
        ret_clean = ret_date.replace('-', '')[2:]
        return f"https://www.skyscanner.com.tr/tasima/ucak-seferleri/{origin.lower()}/{dest.lower()}/{dep_clean}/{ret_clean}/?adultsv2=1&cabinclass=economy"
    return f"https://www.skyscanner.com.tr/tasima/ucak-seferleri/{origin.lower()}/{dest.lower()}/{dep_clean}/?adultsv2=1&cabinclass=economy"

def get_enuygun_url(origin, dest, dep_date, ret_date=None):
    """Enuygun bilet karşılaştırma linki."""
    if ret_date:
        return f"https://www.enuygun.com/ucak-bileti/{origin}-{dest}/?gidis={dep_date}&donus={ret_date}&yetiskin=1"
    return f"https://www.enuygun.com/ucak-bileti/{origin}-{dest}/?gidis={dep_date}&yetiskin=1"

def get_google_flights_url(origin, dest, dep_date, ret_date=None, gl='TR', hl='tr', curr='TRY'):
    """Google Flights optimize edilmiş arama linki."""
    if ret_date:
        q = f"Flights from {origin} to {dest} on {dep_date} through {ret_date}"
    else:
        q = f"Flights from {origin} to {dest} on {dep_date}"
    return f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}&curr={curr}&gl={gl}&hl={hl}"

def get_all_provider_links(origin, dest, dep_date, ret_date=None):
    """Tüm havayolları ve karşılaştırma motorlarının doğrudan bağlantılarını döner."""
    origin, dest = _clean_code(origin), _clean_code(dest)
    dep_date = _clean_date(dep_date)
    ret_date = _clean_date(ret_date) if ret_date else None
    return [
        {
            'key': 'google',
            'name': 'Google Flights',
            'icon': '🌐',
            'color': '#1a73e8',
            'url': get_google_flights_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'pegasus',
            'name': 'Pegasus (Resmi)',
            'icon': '💛',
            'color': '#f5a623',
            'url': get_pegasus_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'ajet',
            'name': 'AJet (Resmi)',
            'icon': '💙',
            'color': '#00aeef',
            'url': get_ajet_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'thy',
            'name': 'Türk Hava Yolları',
            'icon': '🔴',
            'color': '#a00000',
            'url': get_thy_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'sunexpress',
            'name': 'SunExpress',
            'icon': '☀️',
            'color': '#d97706',
            'url': get_sunexpress_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'skyscanner',
            'name': 'Skyscanner',
            'icon': '🔍',
            'color': '#00b2d6',
            'url': get_skyscanner_url(origin, dest, dep_date, ret_date)
        },
        {
            'key': 'enuygun',
            'name': 'Enuygun',
            'icon': '⚡',
            'color': '#16a34a',
            'url': get_enuygun_url(origin, dest, dep_date, ret_date)
        }
    ]

# ==========================================
# 3. GİZLİ MOD & ÇEREZ KORUMA MOTORU (INCOGNITO)
# ==========================================
USER_AGENTS = [
    # Modern Android / Mobile
    'Mozilla/5.0 (Linux; Android 14; SM-X620 Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; SM-S931B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.70 Mobile Safari/537.36',
    # Modern Desktop
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0'
]

def get_clean_incognito_headers(market='TR', device='mobile'):
    """
    Kullanıcı takibini ve dinamik fiyat artışını önlemek için
    çerezsiz, izole ve anti-tracking gizli mod başlıkları üretir.
    """
    ua = USER_AGENTS[0] if device == 'mobile' else USER_AGENTS[2]
    lang_map = {
        'TR': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'DE': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'US': 'en-US,en;q=0.9'
    }

    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': lang_map.get(market, 'tr-TR,tr;q=0.9'),
        'DNT': '1', # Do Not Track (Takip Etme)
        'Sec-GPC': '1', # Global Privacy Control
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Cookie': 'SOCS=CAESEwgDEgk2OTQ3MjcxNDcaAnRyIAEaBgiA_LyaBg;' # Google zorunlu onay çerezi
    }

# ==========================================
# 4. GEO & SATIŞ NOKTASI ARBİTRAJ MOTORU (VPN/MARKET PROBE)
# ==========================================
def probe_single_market(market_code, gl, hl, origin, dest, dep_date, ret_date, proxy_url=None):
    """Belirli bir pazar (TR, DE, US) simülasyonu ile en düşük bilet fiyatını çeker."""
    if ret_date:
        q = f"Flights from {origin} to {dest} on {dep_date} through {ret_date}"
    else:
        q = f"Flights from {origin} to {dest} on {dep_date}"

    url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}&curr=TRY&gl={gl}&hl={hl}"
    headers = get_clean_incognito_headers(market=market_code)

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            
            html = None
            if proxy_url:
                try:
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))
                    with opener.open(req, timeout=8) as response:
                        data = response.read()
                        if data.startswith(b'\x1f\x8b'):
                            data = gzip.decompress(data)
                        html = data.decode('utf-8', errors='ignore')
                except Exception:
                    html = None

            if html is None:
                opener = urllib.request.build_opener()
                with opener.open(req, timeout=10) as response:
                    data = response.read()
                    if data.startswith(b'\x1f\x8b'):
                        data = gzip.decompress(data)
                    html = data.decode('utf-8', errors='ignore')

            # Uçuş aria-label regexi
            aria_matches = re.findall(r'aria-label=["\']([^"\']+)["\']', html)
            prices = []

            for text in aria_matches:
                price_match = re.search(r'(\d+[\.\d+]*)\s*(?:türk lirası|türkische lira|turkish lira|tl|try)', text, re.I)
                if not price_match:
                    price_match = re.search(r'(?:try|tl)\s*(\d+[\.\d+]*)', text, re.I)
                if price_match:
                    raw_val = price_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        p = int(float(raw_val))
                        if 400 < p < 200000:
                            prices.append(p)
                    except ValueError:
                        pass

            if prices:
                return market_code, min(prices)
            
            if attempt == 0:
                time.sleep(0.4)
                headers = get_clean_incognito_headers(market=market_code, device='desktop')
        except Exception:
            if attempt == 0:
                time.sleep(0.5)

    return market_code, None

def probe_geo_arbitrage(origin, dest, dep_date, ret_date=None, proxy_url=None):
    """
    3 farklı bölgesel satış pazarında (Türkiye, Almanya, ABD) eşzamanlı
    fiyat taraması yaparak coğrafi arbitraj fırsatını analiz eder.
    """
    origin = origin.upper().strip()
    dest = dest.upper().strip()
    dep_date = dep_date.strip()
    ret_date = ret_date.strip() if ret_date else None

    markets_info = {
        'TR': {'gl': 'TR', 'hl': 'tr', 'label': 'Türkiye (Yerel Pazar)', 'flag': '🇹🇷'},
        'DE': {'gl': 'DE', 'hl': 'de', 'label': 'Almanya (Avrupa Satış Noktası)', 'flag': '🇩🇪'},
        'US': {'gl': 'US', 'hl': 'en', 'label': 'ABD / Global Pazar', 'flag': '🇺🇸'}
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for code, info in markets_info.items():
            f = executor.submit(
                probe_single_market,
                code, info['gl'], info['hl'],
                origin, dest, dep_date, ret_date, proxy_url
            )
            futures[f] = code
            time.sleep(0.2)
        for future in concurrent.futures.as_completed(futures):
            code, price = future.result()
            results[code] = price

    # Analiz
    valid_prices = {k: v for k, v in results.items() if v is not None}
    
    if not valid_prices:
        return {
            'ok': False,
            'summary': 'Pazar karşılaştırması için yeterli veri alınamadı.',
            'markets': {},
            'savings_tl': 0,
            'best_market': 'TR'
        }

    cheapest_market = min(valid_prices.keys(), key=lambda k: valid_prices[k])
    cheapest_price = valid_prices[cheapest_market]
    tr_price = valid_prices.get('TR')

    savings = 0
    if tr_price and cheapest_price < tr_price:
        savings = tr_price - cheapest_price
        summary = f"🔥 {markets_info[cheapest_market]['flag']} {markets_info[cheapest_market]['label']} üzerinden bilet {savings} TL daha uygun!"
    elif tr_price:
        summary = f"✅ 🇹🇷 Türkiye yerel pazarı en avantajlı fiyatı sunuyor ({tr_price} TL)."
    else:
        summary = f"🌍 En ucuz bilet: {cheapest_price} TL ({markets_info[cheapest_market]['label']})."

    market_details = {}
    for code, info in markets_info.items():
        market_details[code] = {
            'label': info['label'],
            'flag': info['flag'],
            'price': results.get(code),
            'is_cheapest': (code == cheapest_market)
        }

    return {
        'ok': True,
        'best_market': cheapest_market,
        'cheapest_price': cheapest_price,
        'savings_tl': savings,
        'summary': summary,
        'markets': market_details
    }

# ==========================================
# 5. PROXY / VPN KONTROLÜ
# ==========================================
def test_proxy_live(proxy_url):
    """Proxy URL'sinin gerçekte çalışıp çalışmadığını 1.5 saniyede doğrular."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))
        req = urllib.request.Request('http://connectivitycheck.gstatic.com/generate_204', headers={'User-Agent': 'Mozilla/5.0'})
        with opener.open(req, timeout=1.5) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False

def get_active_proxy():
    """
    Sistemde aktif ve çalışan bir proxy/VPN bağlantısı olup olmadığını doğrular.
    Ortam değişkeni FLIGHT_PROXY veya yerel proxy portlarını test eder.
    """
    env_proxy = os.getenv('FLIGHT_PROXY')
    if env_proxy and test_proxy_live(env_proxy):
        return env_proxy

    # Yerel HTTP / SOCKS proxy portları
    for candidate in ['http://127.0.0.1:10809', 'socks5://127.0.0.1:10808']:
        if test_proxy_live(candidate):
            return candidate

    return None
