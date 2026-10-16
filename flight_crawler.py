import urllib.request
import urllib.parse
import re
import json
import sys
from datetime import datetime


def search_flights(origin, destination, departure_date, return_date=None, currency='TRY'):
    try:
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        departure_date = departure_date.strip()
        if return_date:
            return_date = return_date.strip()

        # Input validation
        if not re.match(r'^[A-Z]{3,4}$', origin) or not re.match(r'^[A-Z]{3,4}$', destination):
            return {'ok': False, 'error': f'Geçersiz IATA havalimanı kodu: {origin} -> {destination}', 'flights': []}

        date_regex = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_regex, departure_date) or (return_date and not re.match(date_regex, return_date)):
            return {'ok': False, 'error': 'Tarih formatı YYYY-MM-DD olmalıdır.', 'flights': []}

        if return_date and departure_date > return_date:
            return {'ok': False, 'error': 'Dönüş tarihi gidiş tarihinden önce olamaz.', 'flights': []}

        if return_date:
            query = f'Flights from {origin} to {destination} on {departure_date} through {return_date}'
        else:
            query = f'Flights from {origin} to {destination} on {departure_date}'

        encoded_query = urllib.parse.quote(query)
        url = f'https://www.google.com/travel/flights?q={encoded_query}&curr={currency}&hl=tr'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': 'SOCS=CAESEwgDEgk2OTQ3MjcxNDcaAnRyIAEaBgiA_LyaBg;',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')

        pattern = r'aria-label=["\']([^"\']*(?:Türk lirası|TL)[^"\']*)["\']'
        matches = re.findall(pattern, html)

        flights = []
        seen = set()

        for text in matches:
            try:
                # Sadece gerçek uçuş kartlarını işle (buton ve filtre etiketlerini ele)
                if 'ile' not in text or 'uçuş' not in text:
                    continue

                price_match = re.search(r'(\d+[\.\d+]*)\s*(?:Türk lirası|TL)', text)
                if not price_match:
                    continue
                raw_price = price_match.group(1).replace('.', '').replace(',', '.')
                try:
                    price = int(float(raw_price))
                except ValueError:
                    continue

                airline = None
                for carrier, display_name in [
                    ('Pegasus', 'Pegasus'),
                    ('AJet', 'AJet'),
                    ('Turkish Airlines', 'Türk Hava Yolları'),
                    ('Türk Hava Yolları', 'Türk Hava Yolları'),
                    ('THY', 'Türk Hava Yolları'),
                    ('SunExpress', 'SunExpress'),
                    ('AnadoluJet', 'AJet')
                ]:
                    if carrier.lower() in text.lower():
                        airline = display_name
                        break
                if not airline:
                    airline = 'Diğer'

                time_pattern = r'(\d{1,2}:\d{2})'
                times = re.findall(time_pattern, text)
                if len(times) >= 2:
                    departure_time, arrival_time = times[0], times[1]
                elif len(times) == 1:
                    departure_time, arrival_time = times[0], None
                else:
                    departure_time, arrival_time = None, None

                duration_match = re.search(r'(\d+\s*sa\.?\s*\d*\s*dk\.?)', text)
                duration = duration_match.group(1) if duration_match else None

                direct = 'aktarmasız' in text.lower()

                flight_key = (airline, departure_time, arrival_time, price)
                if flight_key in seen:
                    continue
                seen.add(flight_key)

                flight = {
                    'airline': airline,
                    'departure_time': departure_time,
                    'arrival_time': arrival_time,
                    'duration': duration,
                    'direct': direct,
                    'price': price
                }
                flights.append(flight)
            except Exception:
                continue

        flights.sort(key=lambda x: x['price'])

        return {
            'ok': True,
            'query': query,
            'search_url': url,
            'flights': flights,
            'count': len(flights)
        }

    except Exception as e:
        return {
            'ok': False,
            'error': str(e),
            'flights': []
        }


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(json.dumps({'ok': False, 'error': 'Usage: python flights.py ORIGIN DESTINATION DEPARTURE_DATE [RETURN_DATE]', 'flights': []}))
        sys.exit(1)

    origin = sys.argv[1].upper()
    destination = sys.argv[2].upper()
    departure_date = sys.argv[3]
    return_date = sys.argv[4] if len(sys.argv) > 4 else None

    result = search_flights(origin, destination, departure_date, return_date)
    print(json.dumps(result, ensure_ascii=False, indent=2))
