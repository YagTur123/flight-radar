#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Radar 2.0 - Akıllı Şehir & Çoklu Hub Eşleştirme (Smart Radius Search)
Büyük metropollerdeki havalimanlarını (IST+SAW, LHR+STN, vb.) otomatik birleştirir
ve yakındaki alternatif havalimanları için fiyat avantajlarını keşfeder.
"""

from airline_providers import AIRPORTS

MULTI_HUBS = {
    'IST_ALL': {
        'name': 'İstanbul (Tümü - SAW & IST)',
        'city': 'İstanbul',
        'airports': ['SAW', 'IST']
    },
    'EGE_ALL': {
        'name': 'Ege Sahilleri (İzmir, Bodrum, Dalaman)',
        'city': 'Ege Bölgesi',
        'airports': ['ADB', 'BJV', 'DLM']
    },
    'AKDENIZ_ALL': {
        'name': 'Akdeniz Sahilleri (Antalya, Alanya, Adana)',
        'city': 'Akdeniz Bölgesi',
        'airports': ['AYT', 'GZP', 'ADA']
    },
    'LON_ALL': {
        'name': 'Londra (Tümü - Heathrow, Stansted)',
        'city': 'Londra',
        'airports': ['LHR', 'STN']
    },
    'GER_ALL': {
        'name': 'Almanya Ana Hublar (Berlin, Frankfurt, Münih)',
        'city': 'Almanya',
        'airports': ['BER', 'FRA', 'MUC']
    }
}

def get_hub_info(hub_code):
    """Hub veya tekil havalimanı detayını döner."""
    code = hub_code.upper().strip()
    if code in MULTI_HUBS:
        return MULTI_HUBS[code]
    if code in AIRPORTS:
        return {
            'name': f"{AIRPORTS[code]['name']} ({code})",
            'city': AIRPORTS[code]['city'],
            'airports': [code]
        }
    return None

def get_all_hubs_and_airports():
    """Form seçenekleri için hem çoklu hubları hem de tekil havalimanlarını listeler."""
    items = []
    # Çoklu Hublar önce
    for code, info in MULTI_HUBS.items():
        items.append({
            'code': code,
            'label': f"⭐ {info['name']}",
            'is_hub': True,
            'children': info['airports']
        })
    # Tekil havalimanları
    for code, info in AIRPORTS.items():
        items.append({
            'code': code,
            'label': f"{code} - {info['city']} ({info['name']})",
            'is_hub': False,
            'children': [code]
        })
    return items

def expand_routes_for_hub(origin, destination):
    """
    Örn: origin 'ADB', destination 'IST_ALL' verildiğinde:
    [('ADB', 'SAW'), ('ADB', 'IST')] rota çiftlerini üretir.
    """
    orig_airports = MULTI_HUBS[origin]['airports'] if origin in MULTI_HUBS else [origin]
    dest_airports = MULTI_HUBS[destination]['airports'] if destination in MULTI_HUBS else [destination]

    pairs = []
    for o in orig_airports:
        for d in dest_airports:
            if o != d:
                pairs.append((o, d))
    return pairs

if __name__ == '__main__':
    print("Hub Pairs (ADB -> IST_ALL):", expand_routes_for_hub('ADB', 'IST_ALL'))
