#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Radar 2.0 - Canlı TCMB & Forex Çapraz Kur Arbitraj Motoru
Havayollarının iç döviz kurunu gecikmeli güncellemesinden doğan
fiyat makasını (TRY vs EUR vs USD) gerçek zamanlı tespit eder.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time

CACHE_DURATION = 3600 # 1 saat önbellek
_forex_cache = {'rates': None, 'timestamp': 0}

def get_live_rates():
    """TCMB resmi XML servisinden veya fallback API'den canlı döviz kurlarını çeker."""
    now = time.time()
    if _forex_cache['rates'] and (now - _forex_cache['timestamp'] < CACHE_DURATION):
        return _forex_cache['rates']

    rates = {'USD': 38.50, 'EUR': 42.10, 'GBP': 50.20, 'source': 'fallback'}

    # 1. Kaynak: TCMB Resmi XML
    try:
        tcmb_url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(tcmb_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            
            for currency in root.findall('Currency'):
                code = currency.get('CurrencyCode')
                if code in ['USD', 'EUR', 'GBP']:
                    forex_selling = currency.find('ForexSelling')
                    if forex_selling is not None and forex_selling.text:
                        rates[code] = float(forex_selling.text.replace(',', '.'))
            rates['source'] = 'TCMB Resmi'
            _forex_cache['rates'] = rates
            _forex_cache['timestamp'] = now
            return rates
    except Exception:
        pass

    # 2. Kaynak: Free Exchange API Fallback
    try:
        api_url = "https://open.er-api.com/v6/latest/TRY"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            api_rates = data.get('rates', {})
            if 'USD' in api_rates and api_rates['USD'] > 0:
                rates['USD'] = round(1.0 / api_rates['USD'], 2)
            if 'EUR' in api_rates and api_rates['EUR'] > 0:
                rates['EUR'] = round(1.0 / api_rates['EUR'], 2)
            if 'GBP' in api_rates and api_rates['GBP'] > 0:
                rates['GBP'] = round(1.0 / api_rates['GBP'], 2)
            rates['source'] = 'Global Forex API'
            _forex_cache['rates'] = rates
            _forex_cache['timestamp'] = now
            return rates
    except Exception:
        pass

    return rates

def evaluate_currency_arbitrage(price_try, price_foreign, currency_code='EUR'):
    """
    Yerel TL fiyatı ile yabancı para birimindeki fiyatı canlı kur üzerinden karşılaştırır.
    Örn: TL fiyatı 4200 TL iken, Avrupa pazarında bilet 90 EUR (Canlı kurla 3780 TL) ise
    420 TL (%10) tasarruf fırsatını hesaplar.
    """
    if not price_try or not price_foreign:
        return {'has_arbitrage': False, 'advice': 'Fiyat verisi yetersiz.'}

    rates = get_live_rates()
    rate = rates.get(currency_code.upper(), 42.0)
    real_try_cost = round(price_foreign * rate, 2)

    diff = round(price_try - real_try_cost, 2)
    diff_pct = round((diff / price_try) * 100, 1)

    if diff > 150: # En az 150 TL kazanç varsa
        return {
            'has_arbitrage': True,
            'advantage_currency': currency_code.upper(),
            'savings_try': diff,
            'savings_pct': diff_pct,
            'tcmb_rate': rate,
            'real_cost_try': real_try_cost,
            'advice': f"🔥 {currency_code} ile ödeme {diff:.0f} TL (%{diff_pct}) daha hesaplı! (TCMB {currency_code}: {rate:.2f} TL)"
        }
    elif diff < -150:
        return {
            'has_arbitrage': False,
            'advantage_currency': 'TRY',
            'savings_try': abs(diff),
            'savings_pct': abs(diff_pct),
            'tcmb_rate': rate,
            'real_cost_try': real_try_cost,
            'advice': f"✅ Türkiye yerel TL ödemesi en avantajlı seçenek."
        }
    else:
        return {
            'has_arbitrage': False,
            'advantage_currency': 'DENGE',
            'savings_try': 0,
            'savings_pct': 0,
            'tcmb_rate': rate,
            'real_cost_try': real_try_cost,
            'advice': f"Kur farkı dengede (Fark < 150 TL)."
        }

if __name__ == '__main__':
    r = get_live_rates()
    print("Canlı Kurlar:", r)
    arb = evaluate_currency_arbitrage(4200, 92, 'EUR')
    print("Arbitraj Testi (4200 TL vs 92 EUR):", arb)
