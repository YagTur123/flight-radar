#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Radar 2.0 - 24/7 Telegram İstihbarat & Alarm Botu
Bilet fiyatı hedefin altına düştüğünde veya dip rekor kırdığında
Telegram üzerinden doğrudan cebe/akıllı saate anlık bildirim iletir.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

import database

def get_telegram_config():
    """Bot token ve chat ID ayarlarını veritabanından veya ortamdan çeker."""
    token = database.get_setting('telegram_bot_token') or os.getenv('TELEGRAM_BOT_TOKEN') or ''
    chat_id = database.get_setting('telegram_chat_id') or os.getenv('TELEGRAM_CHAT_ID') or ''
    return {'bot_token': token, 'chat_id': chat_id}

def send_telegram_message(text, keyboard=None, bot_token=None, chat_id=None):
    """Telegram API üzerinden mesaj gönderir."""
    cfg = get_telegram_config()
    token = bot_token or cfg.get('bot_token')
    chat_id = chat_id or cfg.get('chat_id')

    if not token or not chat_id:
        return {'ok': False, 'error': 'Telegram Bot Token veya Chat ID tanımlanmamış.'}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }

    if keyboard:
        payload['reply_markup'] = {'inline_keyboard': keyboard}

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            return res_data
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def test_telegram_connection(bot_token=None, chat_id=None):
    """Verilen token ve chat ID ile bağlantı testi yapar."""
    cfg = get_telegram_config()
    token = bot_token or cfg.get('bot_token')
    cid = chat_id or cfg.get('chat_id')
    if not token or not cid:
        return {'ok': False, 'error': 'Telegram Bot Token veya Chat ID eksik.'}

    msg = (
        "<b>✈️ FLIGHT RADAR 2.0 BAĞLANTISI BAŞARILI!</b>\n\n"
        "Tebrikler! Radar bildirim botunuz başarıyla bağlandı.\n"
        "Takip ettiğiniz rotalarda hedef bütçenizin altına inen biletler veya "
        "rekor dip fiyatlar anında bu kanala iletilecektir."
    )
    res = send_telegram_message(msg, bot_token=token, chat_id=cid)
    return res

def dispatch_deal_alert(route, current_price, target_price, lowest_recorded, booking_url=None):
    """Fiyat düştüğünde zengin Telegram alarmı fırlatır."""
    r_title = route.get('title', f"{route['origin']} ⇄ {route['destination']}")
    airline = route.get('airline', 'Havayolu')
    dep_date = route.get('departure_date', '')
    ret_date = route.get('return_date') or 'Tek Yön'
    
    diff = target_price - current_price if target_price else 0
    
    msg = (
        f"🚨 <b>FİYAT ALARMI: {route['origin']} ⇄ {route['destination']}</b>\n\n"
        f"📌 <b>Rota:</b> {r_title}\n"
        f"📅 <b>Tarih:</b> {dep_date} - {ret_date}\n"
        f"✈️ <b>Havayolu:</b> {airline}\n\n"
        f"💰 <b>GÜNCEL FİYAT:</b> <code>{current_price:,.0f} TL</code>\n"
        f"🎯 <b>Hedef Bütçe:</b> <code>{target_price:,.0f} TL</code> "
        f"(<b>{diff:+,.0f} TL TASARRUF!</b>)\n"
    )
    
    if lowest_recorded and current_price <= lowest_recorded:
        msg += f"🔥 <b>Şimdiye kadarki EN UCUZ rekor dip fiyat!</b>\n"

    msg += f"\n⏰ <i>Tespit Zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

    keyboard = []
    if booking_url:
        keyboard.append([{'text': '✈️ Hemen Bilet Ara / Al ↗', 'url': booking_url}])

    return send_telegram_message(msg, keyboard=keyboard)

if __name__ == '__main__':
    cfg = get_telegram_config()
    print(f"Telegram Config -> Token Set: {bool(cfg.get('bot_token'))}, Chat ID Set: {bool(cfg.get('chat_id'))}")
