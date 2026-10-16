#!/usr/bin/env python3
"""
Flight Radar Web Arayüzü ve API Sunucusu (Port 8080)
Sıcak editoryal minimalist gazete stili (Newsreader + Plus Jakarta Sans + JetBrains Mono)
Fiyat Geçmişi & Saf SVG Trend Grafiği Entegrasyonu (Sıfır harici CDN bağımlılığı)
"""

import http.server
import json
import os
import sys
import subprocess
import urllib.parse
import datetime
import importlib.util
import html
from http.server import HTTPServer, BaseHTTPRequestHandler

import radar_helpers
import airline_providers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKS_FILE = os.path.join(BASE_DIR, 'tracked_flights.json')
RSS_DB_FILE = os.path.join(BASE_DIR, 'seen_campaigns.json')
LOG_FILE = os.path.join(BASE_DIR, 'radar.log')
RADAR_SCRIPT = os.path.join(BASE_DIR, 'flight_radar.py')
CRAWLER_SCRIPT = os.path.join(BASE_DIR, 'flight_crawler.py')

def log(msg):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now().isoformat()} | {msg}\n")
    except Exception:
        pass

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default

def clean_for_json(obj):
    if isinstance(obj, float):
        if obj != obj or obj == float('inf') or obj == float('-inf'):
            return None
        return obj
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    return obj

def save_json(path, data):
    try:
        cleaned = clean_for_json(data)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"save_json error ({path}): {e}")

def load_crawler():
    spec = importlib.util.spec_from_file_location("flight_crawler", CRAWLER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_flight_color(airline):
    if not airline:
        return '#777'
    a = airline.lower()
    if 'pegasus' in a:
        return '#F5A623'
    elif 'ajet' in a or 'anadolujet' in a:
        return '#00AEEF'
    elif 'thy' in a or 'türk hava' in a or 'turkish' in a:
        return '#A00000'
    elif 'sunexpress' in a:
        return '#d97706'
    return '#666'

def generate_google_flights_link(origin, destination, departure_date, return_date=None):
    q = f"Flights from {origin} to {destination} on {departure_date}"
    if return_date:
        q += f" through {return_date}"
    return f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}&curr=TRY&hl=tr"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aydın ⇄ İstanbul Seyahat Radarı</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,600;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #c25a36;
            --primary-dark: #9e3f20;
            --bg: #f9f5f0;
            --surface: #ffffff;
            --surface-subtle: #f4efe6;
            --border: #e4dfd3;
            --border-dark: #d0c9bc;
            --text: #181716;
            --text-muted: #6b665c;
            --font-serif: 'Newsreader', Georgia, serif;
            --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: var(--font-sans);
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 24px 16px 60px;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 900px; margin: 0 auto; }
        
        /* Masthead */
        .masthead {
            background: var(--surface);
            border: 1px solid var(--border);
            border-top: 4px solid var(--primary);
            padding: 24px;
            border-radius: 6px;
            margin-bottom: 24px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }
        .masthead-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 16px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .live-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #2e7d32;
            border-radius: 50%;
            margin-right: 6px;
        }
        .masthead h1 {
            font-family: var(--font-serif);
            font-size: clamp(26px, 4vw, 36px);
            font-weight: 600;
            color: var(--text);
            line-height: 1.2;
            margin-bottom: 8px;
        }
        .masthead p {
            color: var(--text-muted);
            font-size: 15px;
        }
        .masthead-actions {
            display: flex;
            gap: 10px;
            margin-top: 16px;
            flex-wrap: wrap;
        }

        /* Buttons */
        .btn {
            background: var(--text);
            color: #fff;
            border: none;
            padding: 10px 18px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn:hover { background: #333; }
        .btn-primary { background: var(--primary); color: #fff; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-secondary {
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border-dark);
        }
        .btn-secondary:hover { background: var(--surface-subtle); }
        .btn-danger { background: #b4341e; color: #fff; }
        .btn-danger:hover { background: #922512; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Card Section */
        .section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }
        .section-title {
            font-family: var(--font-serif);
            font-size: 22px;
            font-weight: 600;
            color: var(--text);
        }

        /* Travel Route Tips */
        .travel-tips {
            background: var(--surface-subtle);
            border-left: 3px solid var(--primary);
            padding: 16px;
            margin-bottom: 24px;
            border-radius: 0 4px 4px 0;
            font-size: 14px;
        }
        .travel-tips h3 {
            font-family: var(--font-serif);
            font-size: 17px;
            margin-bottom: 6px;
            color: var(--primary);
        }
        .travel-tips p {
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        /* Form */
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .form-group label {
            font-family: var(--font-mono);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }
        .form-group input {
            padding: 10px 12px;
            border: 1px solid var(--border-dark);
            border-radius: 4px;
            font-family: var(--font-sans);
            font-size: 14px;
            background: #fff;
            color: var(--text);
        }
        .form-group input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(194, 90, 54, 0.15);
        }
        .form-actions {
            margin-top: 18px;
            display: flex;
            gap: 10px;
        }

        /* Track Card */
        .track-list { display: flex; flex-direction: column; gap: 16px; }
        .track-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 20px;
            transition: border-color 0.15s ease;
        }
        .track-card:hover { border-color: var(--border-dark); }
        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }
        .card-title {
            font-family: var(--font-serif);
            font-size: 19px;
            font-weight: 600;
            color: var(--text);
        }
        .route-info {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 12px;
        }
        .route-badge {
            font-family: var(--font-mono);
            font-weight: 600;
            color: var(--text);
            background: var(--surface-subtle);
            padding: 2px 8px;
            border-radius: 3px;
        }
        .airline-tag {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 3px;
            color: #fff;
            text-transform: uppercase;
        }
        .price-box {
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 16px;
        }
        .current-price {
            font-family: var(--font-serif);
            font-size: 26px;
            font-weight: 600;
            color: var(--primary);
        }
        .target-price {
            font-family: var(--font-mono);
            font-size: 13px;
            color: var(--text-muted);
        }
        .target-reached {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
            font-size: 11px;
            font-family: var(--font-mono);
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 3px;
        }
        .card-actions {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        /* SVG Trend Chart Box */
        .chart-box {
            margin-top: 16px;
            padding: 16px;
            background: var(--surface-subtle);
            border-radius: 4px;
            border: 1px solid var(--border);
        }

        /* Campaign Feed */
        .campaign-list { display: flex; flex-direction: column; gap: 10px; }
        .campaign-item {
            padding: 12px 14px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 3px solid var(--primary);
            border-radius: 3px;
        }
        .campaign-item a {
            color: var(--text);
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
        }
        .campaign-item a:hover { text-decoration: underline; }
        .campaign-date {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .empty-state {
            padding: 36px 16px;
            text-align: center;
            color: var(--text-muted);
            font-style: italic;
        }

        /* Daemon Pill */
        .daemon-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 12px;
            letter-spacing: 0.02em;
        }
        .daemon-pill-running {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
        }
        .daemon-pill-stopped {
            background: #fbe9e7;
            color: #b4341e;
            border: 1px solid #ffccbc;
        }
        .daemon-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
        }

        /* Preset Chips */
        .preset-container {
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .preset-title {
            font-family: var(--font-mono);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }
        .preset-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .chip-btn {
            background: var(--surface);
            border: 1px solid var(--border-dark);
            color: var(--text);
            padding: 5px 11px;
            border-radius: 20px;
            font-size: 12px;
            font-family: var(--font-sans);
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .chip-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
            background: var(--surface-subtle);
        }

        /* Filter Bar */
        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
            align-items: center;
        }
        .filter-btn {
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-family: var(--font-mono);
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .filter-btn:hover { border-color: var(--border-dark); color: var(--text); }
        .filter-btn.active {
            background: var(--text);
            color: #fff;
            border-color: var(--text);
            font-weight: 600;
        }

        /* Deal Badges */
        .deal-status-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
            flex-wrap: wrap;
        }
        .deal-badge {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 3px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .badge-success { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
        .badge-warning { background: #fff8e1; color: #b78103; border: 1px solid #ffe082; }
        .badge-danger { background: #fbe9e7; color: #b4341e; border: 1px solid #ffccbc; }
        .badge-neutral { background: #eceff1; color: #546e7a; border: 1px solid #cfd8dc; }
        .deal-desc {
            font-size: 12px;
            color: var(--text-muted);
            font-style: italic;
        }

        /* Stat Pills */
        .stat-pills {
            display: inline-flex;
            gap: 6px;
            align-items: center;
            margin-left: 8px;
            flex-wrap: wrap;
        }
        .stat-pill {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            background: var(--surface-subtle);
            padding: 2px 7px;
            border-radius: 3px;
            border: 1px solid var(--border);
        }

        /* Flexible Dates Box */
        .flex-box {
            margin-top: 14px;
            padding: 12px;
            background: #fdfbf7;
            border: 1px dashed var(--border-dark);
            border-radius: 4px;
        }
        .flex-box-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 8px;
            font-family: var(--font-mono);
        }
        .flex-chip-list {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .flex-chip {
            text-decoration: none;
            background: #fff;
            border: 1px solid var(--border-dark);
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: var(--font-mono);
            color: var(--text);
            transition: all 0.15s ease;
        }
        .flex-chip:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        .flex-current {
            background: var(--surface-subtle);
            font-weight: 600;
            border-color: var(--primary);
        }

        /* Modal Overlay */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            padding: 16px;
        }
        .modal-content {
            background: #181716;
            color: #d1d5db;
            border-radius: 8px;
            max-width: 800px;
            width: 100%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            border: 1px solid #333;
        }
        .modal-header {
            padding: 14px 18px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: var(--font-mono);
            font-size: 13px;
        }
        .modal-body {
            padding: 14px 18px;
            overflow-y: auto;
            flex: 1;
        }
        .log-pre {
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-all;
            color: #a3e635;
        }

        /* Direct Airline Provider Drawer */
        .provider-box {
            margin-top: 14px;
            padding: 14px;
            background: #fdfaf6;
            border: 1px solid var(--border);
            border-left: 3px solid var(--text);
            border-radius: 4px;
        }
        .provider-box-title {
            font-size: 12px;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 10px;
            font-family: var(--font-mono);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .provider-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
            gap: 8px;
        }
        .provider-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 4px;
            background: var(--surface);
            border: 1px solid var(--border-dark);
            color: var(--text);
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.15s ease;
        }
        .provider-btn:hover {
            border-color: var(--primary);
            background: var(--surface-subtle);
            transform: translateY(-1px);
        }

        /* Arbitrage & Geo-Market Drawer */
        .arbitrage-box {
            margin-top: 14px;
            padding: 16px;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-left: 3px solid #0284c7;
            border-radius: 4px;
        }
        .arbitrage-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .arbitrage-title {
            font-size: 13px;
            font-weight: 700;
            color: #0369a1;
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .arbitrage-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
            margin-bottom: 12px;
        }
        .arbitrage-card {
            background: #fff;
            padding: 12px;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
            text-align: center;
        }
        .arbitrage-card.best-deal {
            border-color: #16a34a;
            background: #f0fdf4;
            box-shadow: 0 0 0 1px #16a34a;
        }
        .arbitrage-flag { font-size: 20px; margin-bottom: 4px; }
        .arbitrage-market-name { font-size: 11px; font-family: var(--font-mono); color: var(--text-muted); }
        .arbitrage-market-price { font-family: var(--font-serif); font-size: 20px; font-weight: 700; color: var(--text); margin-top: 4px; }
        .arbitrage-footer {
            font-size: 12px;
            color: #475569;
            background: #f1f5f9;
            padding: 8px 12px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
        }
        .incognito-tag {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #0f172a;
            color: #f8fafc;
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Masthead -->
        <header class="masthead">
            <div class="masthead-top">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span><span class="live-dot"></span> Radar Paneli</span>
                    <span id="daemonStatusPill" class="daemon-pill daemon-pill-stopped"><span class="daemon-dot"></span> Radar: Durduruldu</span>
                </div>
                <span id="lastCheckMeta">__LAST_CHECK__</span>
            </div>
            <h1>Aydın ⇄ İstanbul Seyahat Radarı</h1>
            <p>İzmir (ADB) çıkışlı uçuşlar, tren aktarması, 2 saatte bir arka plan taraması ve akıllı fiyat tahmini.</p>
            <div class="masthead-actions">
                <button type="button" class="btn btn-primary" onclick="scanNow()" id="btnScan">⚡ Şimdi Tara</button>
                <button type="button" class="btn btn-secondary" onclick="toggleDaemon()" id="btnDaemon">▶ Radarı Başlat</button>
                <button type="button" class="btn btn-secondary" onclick="openLogModal()">📜 Günlük</button>
                <button type="button" class="btn btn-secondary" onclick="testNotify()">🔔 Test Bildirimi</button>
            </div>
        </header>

        <!-- Travel Tips -->
        <div class="travel-tips">
            <h3>🚆 Akıllı Rota: Aydın Tren + İzmir (ADB) Uçak</h3>
            <p>• Aydın Gar ⇄ Adnan Menderes Havalimanı treni 1 saat 15 dk sürer (~45 TL).</p>
            <p>• İzmir ADB ⇄ İstanbul SAW/IST uçuşu 1 saat 15 dk sürer (AJet ve Pegasus dip fiyatları yakalanabilir).</p>
        </div>

        <!-- Add Track Form -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">➕ Yeni Seyahat Takibi Ekle</h2>
            </div>
            
            <div class="preset-container">
                <span class="preset-title">⚡ Hızlı Şablonlar & Akıllı Doldurma:</span>
                <div class="preset-row">
                    <button type="button" class="chip-btn" onclick="applyPreset('weekend_this')">📅 Bu Hafta Sonu</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('weekend_next')">📅 Gelecek Hafta Sonu</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('route_saw')">✈️ ADB ⇄ SAW (Sabiha)</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('route_ist')">✈️ ADB ⇄ IST (Havalimanı)</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('route_esb')">✈️ ADB ⇄ ESB (Ankara)</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('budget', 2500)">🎯 2.500 TL</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('budget', 3000)">🎯 3.000 TL</button>
                    <button type="button" class="chip-btn" onclick="applyPreset('budget', 3500)">🎯 3.500 TL</button>
                </div>
            </div>

            <div class="preset-container" style="margin-top:-6px;">
                <span class="preset-title">🛫 Hızlı Havalimanı Seçimi:</span>
                <div class="preset-row">
                    <button type="button" class="chip-btn" onclick="selectAirport('ADB')">İzmir (ADB)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('SAW')">Sabiha (SAW)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('IST')">İstanbul (IST)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('ESB')">Ankara (ESB)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('AYT')">Antalya (AYT)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('TZX')">Trabzon (TZX)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('BJV')">Bodrum (BJV)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('DLM')">Dalaman (DLM)</button>
                    <button type="button" class="chip-btn" onclick="selectAirport('BER')">Berlin (BER)</button>
                </div>
            </div>

            <datalist id="airportsList">
                __AIRPORTS_DATALIST__
            </datalist>

            <form id="addTrackForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Takip Başlığı</label>
                        <input type="text" name="title" placeholder="Örn: Kasım Ara Tatili" required>
                    </div>
                    <div class="form-group">
                        <label>Kalkış Havalimanı (IATA)</label>
                        <input type="text" name="origin" list="airportsList" value="ADB" placeholder="Örn: ADB veya İzmir" maxlength="40" required onchange="sanitizeIATA(this)">
                    </div>
                    <div class="form-group">
                        <label>Varış Havalimanı (IATA)</label>
                        <input type="text" name="destination" list="airportsList" value="IST" placeholder="Örn: IST veya İstanbul" maxlength="40" required onchange="sanitizeIATA(this)">
                    </div>
                    <div class="form-group">
                        <label>Gidiş Tarihi</label>
                        <input type="date" name="departure_date" required>
                    </div>
                    <div class="form-group">
                        <label>Dönüş Tarihi (Opsiyonel)</label>
                        <input type="date" name="return_date">
                    </div>
                    <div class="form-group">
                        <label>Hedef Bütçe (TL)</label>
                        <input type="number" name="target_price" placeholder="3000" min="500" step="50" required>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Takibe Al ve İlk Fiyatı Çek</button>
                </div>
            </form>
        </section>

        <!-- Active Tracks -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">✈️ Aktif Takipler & Trendler</h2>
                <span id="activeCount" style="font-family:var(--font-mono); font-size:12px; color:var(--text-muted);">__TRACK_COUNT__ Aktif Rota</span>
            </div>

            <div class="filter-bar">
                <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); margin-right:4px;">FİLTRE:</span>
                <button type="button" class="filter-btn active" onclick="setFilter('all', this)">Tümü</button>
                <button type="button" class="filter-btn" onclick="setFilter('deal', this)">🎯 Sadece Fırsatlar</button>
                <button type="button" class="filter-btn" onclick="setFilter('pegasus', this)">Pegasus</button>
                <button type="button" class="filter-btn" onclick="setFilter('ajet', this)">AJet</button>
                <button type="button" class="filter-btn" onclick="setFilter('thy', this)">THY</button>
            </div>

            <div class="track-list" id="trackList">
                __TRACK_ITEMS__
            </div>
        </section>

        <!-- Campaigns -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">📰 Yakalanan Kampanyalar</h2>
            </div>
            <div class="campaign-list" id="campaignList">
                __CAMPAIGN_ITEMS__
            </div>
        </section>

        <!-- Log Modal -->
        <div id="logModal" class="modal-overlay" onclick="if(event.target===this)closeLogModal()">
            <div class="modal-content">
                <div class="modal-header">
                    <span>📜 RADAR GÜNLÜĞÜ (radar.log)</span>
                    <button type="button" class="btn btn-secondary" onclick="closeLogModal()" style="padding:4px 10px; font-size:12px;">Kapat ✕</button>
                </div>
                <div class="modal-body">
                    <pre id="logContent" class="log-pre">Loglar yükleniyor...</pre>
                </div>
            </div>
        </div>

        <!-- Toast Notification -->
        <div id="toast" style="position:fixed; bottom:24px; right:24px; background:var(--text); color:#fff; padding:12px 20px; border-radius:6px; font-size:13px; font-weight:600; box-shadow:0 4px 16px rgba(0,0,0,0.18); display:none; z-index:9999; transition:all 0.2s ease;"></div>
    </div>

    <script>
        let openedCharts = new Set();
        let currentTracks = [];

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            if (!t) return;
            t.innerText = msg;
            t.style.background = isError ? '#b4341e' : '#181716';
            t.style.display = 'block';
            t.style.opacity = '1';
            clearTimeout(t.timer);
            t.timer = setTimeout(() => {
                t.style.opacity = '0';
                setTimeout(() => { t.style.display = 'none'; }, 200);
            }, 3000);
        }

        function renderPriceChart(history, targetPrice) {
            if (!history || history.length === 0) {
                return '<div style="color:var(--text-muted); font-size:12px; padding:8px 0;">Henüz geçmiş fiyat kaydı bulunmuyor. Bir sonraki taramayla grafik burada oluşacak.</div>';
            }

            const prices = history.map(h => h.price);
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const firstPrice = history[0].price;
            const lastPrice = history[history.length - 1].price;
            
            // Trend özeti
            let trendBadge = '';
            if (history.length >= 2) {
                const diff = lastPrice - firstPrice;
                const pct = ((diff / firstPrice) * 100).toFixed(1);
                if (diff < 0) {
                    trendBadge = `<span style="color:#2e7d32; font-weight:600; font-size:12px;">📉 %${Math.abs(pct)} Düşüşte (Fırsat)</span>`;
                } else if (diff > 0) {
                    trendBadge = `<span style="color:#b4341e; font-weight:600; font-size:12px;">📈 %${pct} Artışta</span>`;
                } else {
                    trendBadge = `<span style="color:var(--text-muted); font-weight:600; font-size:12px;">➡️ Stabil</span>`;
                }
            } else {
                trendBadge = `<span style="color:var(--text-muted); font-size:12px;">📍 İlk Kayıt Alındı</span>`;
            }

            const width = 500;
            const height = 150;
            const padX = 50;
            const padY = 25;

            const allVals = [...prices, targetPrice].filter(Boolean);
            const yMin = Math.min(...allVals) * 0.96;
            const yMax = Math.max(...allVals) * 1.04;
            const range = (yMax - yMin) || 1;

            const getY = (val) => height - padY - ((val - yMin) / range) * (height - 2 * padY);
            const getX = (idx, total) => total <= 1 ? width / 2 : padX + (idx / (total - 1)) * (width - 2 * padX);

            const pointsArr = history.map((h, i) => `${getX(i, history.length).toFixed(1)},${getY(h.price).toFixed(1)}`);
            const pointsStr = pointsArr.join(' ');

            const firstX = getX(0, history.length).toFixed(1);
            const lastX = getX(history.length - 1, history.length).toFixed(1);
            const bottomY = (height - padY).toFixed(1);
            const areaPoints = `${firstX},${bottomY} ${pointsStr} ${lastX},${bottomY}`;

            // Target Line
            const targetY = targetPrice ? getY(targetPrice).toFixed(1) : null;
            const targetLine = (targetY && targetY >= padY && targetY <= height - padY) ? `
                <line x1="${padX}" y1="${targetY}" x2="${width - padX}" y2="${targetY}" stroke="#2e7d32" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.85" />
                <text x="${width - padX + 5}" y="${parseFloat(targetY) + 3}" fill="#2e7d32" font-size="10" font-family="'JetBrains Mono', monospace">Hedef: ${targetPrice} TL</text>
            ` : '';

            // Circles & Tooltips
            const circles = history.map((h, i) => {
                const cx = getX(i, history.length).toFixed(1);
                const cy = getY(h.price).toFixed(1);
                const isMin = (h.price === minPrice);
                const isMax = (h.price === maxPrice && minPrice !== maxPrice);
                const color = isMin ? '#2e7d32' : (isMax ? '#b4341e' : '#c25a36');
                return `
                    <circle cx="${cx}" cy="${cy}" r="${isMin || isMax ? 5 : 3.5}" fill="${color}" stroke="#fff" stroke-width="1.5">
                        <title>${h.time} | ${h.airline}: ${h.price} TL</title>
                    </circle>
                    ${isMin ? `<text x="${cx}" y="${parseFloat(cy) - 8}" text-anchor="middle" font-size="10" font-weight="bold" fill="#2e7d32" font-family="'JetBrains Mono', monospace">Dip: ${h.price} TL</text>` : ''}
                `;
            }).join('');

            const xLabels = `
                <text x="${padX}" y="${height - 6}" font-size="10" fill="#888" font-family="'JetBrains Mono', monospace">${history[0].time}</text>
                <text x="${width - padX}" y="${height - 6}" text-anchor="end" font-size="10" fill="#888" font-family="'JetBrains Mono', monospace">${history[history.length - 1].time}</text>
            `;

            const gradId = 'grad-' + Math.random().toString(36).substr(2, 8);

            return `
                <div style="margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:'Newsreader', serif; font-size:15px; font-weight:600;">Fiyat Trendi (Zaman Serisi)</span>
                    ${trendBadge}
                </div>
                <svg viewBox="0 0 ${width} ${height}" style="width:100%; height:auto; overflow:visible; display:block;">
                    <defs>
                        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#c25a36" stop-opacity="0.22" />
                            <stop offset="100%" stop-color="#c25a36" stop-opacity="0.0" />
                        </linearGradient>
                    </defs>
                    <polygon points="${areaPoints}" fill="url(#${gradId})" />
                    <polyline fill="none" stroke="#c25a36" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="${pointsStr}" />
                    ${targetLine}
                    ${circles}
                    ${xLabels}
                </svg>
            `;
        }

        let openedFlexBoxes = new Set();
        let openedProviders = new Set();
        let openedArbitrages = new Set();
        let currentFilter = 'all';
        let isDaemonRunning = false;

        function setFilter(type, btn) {
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            renderTracksDOM(currentTracks);
        }

        function formatISODate(d) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${y}-${m}-${day}`;
        }

        function applyPreset(type, val) {
            const form = document.getElementById('addTrackForm');
            const originInput = form.querySelector('input[name="origin"]');
            const destInput = form.querySelector('input[name="destination"]');
            const depInput = form.querySelector('input[name="departure_date"]');
            const retInput = form.querySelector('input[name="return_date"]');
            const titleInput = form.querySelector('input[name="title"]');
            const targetInput = form.querySelector('input[name="target_price"]');

            if (type === 'weekend_this' || type === 'weekend_next') {
                const now = new Date();
                const day = now.getDay(); // 0: Paz, 5: Cum
                let diffToFri = (5 - day + 7) % 7;
                if (diffToFri === 0 && now.getHours() >= 18) diffToFri = 7;
                if (type === 'weekend_next') diffToFri += 7;

                const fri = new Date(now.getTime() + diffToFri * 86400000);
                const sun = new Date(fri.getTime() + 2 * 86400000);

                depInput.value = formatISODate(fri);
                retInput.value = formatISODate(sun);
                retInput.min = depInput.value;
                if (!titleInput.value) {
                    titleInput.value = type === 'weekend_this' ? 'Bu Hafta Sonu Kaçamağı' : 'Gelecek Hafta Sonu';
                }
                showToast(`📅 ${type === 'weekend_this' ? 'Bu Hafta Sonu' : 'Gelecek Hafta Sonu'} tarihleri seçildi.`);
            } else if (type === 'route_saw') {
                originInput.value = 'ADB';
                destInput.value = 'SAW';
                if (!titleInput.value) titleInput.value = 'Aydın/İzmir ⇄ Sabiha Gökçen';
                showToast('✈️ Rota: ADB ⇄ SAW ayarlandı.');
            } else if (type === 'route_ist') {
                originInput.value = 'ADB';
                destInput.value = 'IST';
                if (!titleInput.value) titleInput.value = 'Aydın/İzmir ⇄ İstanbul Havalimanı';
                showToast('✈️ Rota: ADB ⇄ IST ayarlandı.');
            } else if (type === 'route_esb') {
                originInput.value = 'ADB';
                destInput.value = 'ESB';
                if (!titleInput.value) titleInput.value = 'İzmir ⇄ Ankara Esenboğa';
                showToast('✈️ Rota: ADB ⇄ ESB ayarlandı.');
            } else if (type === 'budget') {
                targetInput.value = val;
                showToast(`🎯 Hedef bütçe ${val} TL olarak ayarlandı.`);
            }
        }

        function toggleChart(trackId) {
            const box = document.getElementById('chart-box-' + trackId);
            if (!box) return;
            if (box.style.display === 'none' || !box.style.display) {
                box.style.display = 'block';
                openedCharts.add(trackId);
                const track = currentTracks.find(t => String(t.id) === String(trackId));
                if (track) {
                    box.innerHTML = renderPriceChart(track.price_history || [], track.target_price);
                }
            } else {
                box.style.display = 'none';
                openedCharts.delete(trackId);
            }
        }

        function toggleFlex(trackId) {
            const box = document.getElementById('flex-box-' + trackId);
            if (!box) return;
            if (box.style.display === 'none' || !box.style.display) {
                box.style.display = 'block';
                openedFlexBoxes.add(trackId);
            } else {
                box.style.display = 'none';
                openedFlexBoxes.delete(trackId);
            }
        }

        function toggleProviders(trackId) {
            const box = document.getElementById('provider-box-' + trackId);
            if (!box) return;
            if (box.style.display === 'none' || !box.style.display) {
                box.style.display = 'block';
                openedProviders.add(trackId);
            } else {
                box.style.display = 'none';
                openedProviders.delete(trackId);
            }
        }

        function toggleArbitrage(trackId, origin, dest, depDate, retDate) {
            const box = document.getElementById('arbitrage-box-' + trackId);
            if (!box) return;
            if (box.style.display === 'none' || !box.style.display) {
                box.style.display = 'block';
                openedArbitrages.add(trackId);
            } else {
                box.style.display = 'none';
                openedArbitrages.delete(trackId);
            }
        }

        async function runArbitrage(trackId, origin, dest, depDate, retDate) {
            const container = document.getElementById('arbitrage-results-' + trackId);
            if (!container) return;
            container.innerHTML = `
                <div style="font-size:12px; color:var(--text); padding:12px 0; display:flex; align-items:center; gap:8px;">
                    <span class="live-dot" style="background:#0284c7;"></span> 
                    <b>Pazar Arbitrajı Taranıyor:</b> TR 🇹🇷, DE 🇩🇪 ve US 🇺🇸 pazarları sorgulanıyor (Gizli Mod + Temiz Çerez)... Lütfen bekleyin.
                </div>
            `;

            try {
                const payload = {
                    origin: origin,
                    destination: dest,
                    departure_date: depDate,
                    return_date: retDate || null
                };
                const res = await fetch('/api/arbitrage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (!data.ok && data.error) {
                    container.innerHTML = `<div style="color:#b4341e; font-size:12px; padding:8px 0;">⚠️ Arbitraj hatası: ${data.error}</div>`;
                    return;
                }

                const markets = data.markets || {};
                let cardsHtml = '';
                for (const [code, m] of Object.entries(markets)) {
                    const priceText = m.price ? `${m.price} TL` : 'Fiyat Alınamadı';
                    const isBest = m.is_cheapest;
                    cardsHtml += `
                        <div class="arbitrage-card ${isBest ? 'best-deal' : ''}">
                            <div class="arbitrage-flag">${m.flag}</div>
                            <div class="arbitrage-market-name">${m.label}</div>
                            <div class="arbitrage-market-price" style="${isBest ? 'color:#16a34a;' : ''}">${priceText}</div>
                            ${isBest ? '<div style="font-size:10px; font-weight:700; color:#16a34a; margin-top:2px;">EN UCUZ PAZAR 🎯</div>' : ''}
                        </div>
                    `;
                }

                const proxyStatus = data.active_proxy 
                    ? `🟢 Aktif Yerel Proxy/VPN Tespit Edildi (${data.active_proxy})` 
                    : `⚪ Doğrudan Bağlantı (VPN/Proxy tespit edilmedi, yerel port 10808 pasif)`;

                container.innerHTML = `
                    <div class="arbitrage-grid">
                        ${cardsHtml}
                    </div>
                    <div class="arbitrage-footer">
                        <div><b>Özet & Tavsiye:</b> ${data.summary || 'Tarama tamamlandı.'}</div>
                        <div style="font-size:11px; color:#64748b; margin-top:4px;">${proxyStatus}</div>
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<div style="color:#b4341e; font-size:12px; padding:8px 0;">⚠️ Bağlantı hatası: ${err.message}</div>`;
            }
        }

        function generateProviderButtonsClient(origin, dest, depDate, retDate) {
            if (!origin || !dest || !depDate) return '';
            const depClean = depDate.replace(/-/g, '');
            const retClean = retDate ? retDate.replace(/-/g, '') : '';
            const depSky = depClean.slice(2);
            const retSky = retClean ? retClean.slice(2) : '';

            let gq = `Flights from ${origin} to ${dest} on ${depDate}`;
            if (retDate) gq += ` through ${retDate}`;
            const gUrl = `https://www.google.com/travel/flights?q=${encodeURIComponent(gq)}&curr=TRY&gl=TR&hl=tr`;

            const pegasusUrl = retDate
                ? `https://web.flypgs.com/booking?language=tr&origin=${origin}&destination=${dest}&departureDate=${depClean}&returnDate=${retClean}&adultCount=1`
                : `https://web.flypgs.com/booking?language=tr&origin=${origin}&destination=${dest}&departureDate=${depClean}&adultCount=1`;

            const ajetUrl = retDate
                ? `https://ajet.com/tr/bilet-al?from=${origin}&to=${dest}&departureDate=${depDate}&returnDate=${retDate}&adult=1`
                : `https://ajet.com/tr/bilet-al?from=${origin}&to=${dest}&departureDate=${depDate}&adult=1`;

            const thyUrl = retDate
                ? `https://www.turkishairlines.com/tr-tr/ucak-bileti/rezervasyon/?origin=${origin}&destination=${dest}&departureDate=${depDate}&returnDate=${retDate}&adultCount=1`
                : `https://www.turkishairlines.com/tr-tr/ucak-bileti/rezervasyon/?origin=${origin}&destination=${dest}&departureDate=${depDate}&adultCount=1`;

            const sunUrl = retDate
                ? `https://www.sunexpress.com/tr/ucak-bileti/?origin=${origin}&destination=${dest}&departure=${depDate}&return=${retDate}&adults=1`
                : `https://www.sunexpress.com/tr/ucak-bileti/?origin=${origin}&destination=${dest}&departure=${depDate}&adults=1`;

            const skyUrl = retDate
                ? `https://www.skyscanner.com.tr/tasima/ucak-seferleri/${origin.toLowerCase()}/${dest.toLowerCase()}/${depSky}/${retSky}/?adultsv2=1&cabinclass=economy`
                : `https://www.skyscanner.com.tr/tasima/ucak-seferleri/${origin.toLowerCase()}/${dest.toLowerCase()}/${depSky}/?adultsv2=1&cabinclass=economy`;

            const enuygunUrl = retDate
                ? `https://www.enuygun.com/ucak-bileti/${origin}-${dest}/?gidis=${depDate}&donus=${retDate}&yetiskin=1`
                : `https://www.enuygun.com/ucak-bileti/${origin}-${dest}/?gidis=${depDate}&yetiskin=1`;

            const providers = [
                { name: 'Google Flights', icon: '🌐', color: '#1a73e8', url: gUrl },
                { name: 'Pegasus (Resmi)', icon: '💛', color: '#f5a623', url: pegasusUrl },
                { name: 'AJet (Resmi)', icon: '💙', color: '#00aeef', url: ajetUrl },
                { name: 'Türk Hava Yolları', icon: '🔴', color: '#a00000', url: thyUrl },
                { name: 'SunExpress', icon: '☀️', color: '#d97706', url: sunUrl },
                { name: 'Skyscanner', icon: '🔍', color: '#00b2d6', url: skyUrl },
                { name: 'Enuygun', icon: '⚡', color: '#16a34a', url: enuygunUrl }
            ];

            return providers.map(p => `
                <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="provider-btn" style="border-left: 3px solid ${p.color};">
                    <span>${p.icon}</span> <span>${p.name}</span> <span style="font-size:10px; color:var(--text-muted);">↗</span>
                </a>
            `).join('');
        }

        function selectAirport(code) {
            const form = document.getElementById('addTrackForm');
            if (!form) return;
            const origInput = form.querySelector('input[name="origin"]');
            const destInput = form.querySelector('input[name="destination"]');
            if (!origInput || !destInput) return;
            if (!origInput.value || origInput.value.length < 3) {
                origInput.value = code;
                showToast(`Kalkış: ${code}`);
            } else if (!destInput.value || destInput.value.length < 3) {
                destInput.value = code;
                showToast(`Varış: ${code}`);
            } else {
                destInput.value = code;
                showToast(`Varış güncellendi: ${code}`);
            }
        }

        function sanitizeIATA(input) {
            if (!input || !input.value) return;
            let val = input.value.trim().toUpperCase();
            const match = val.match(/^([A-Z]{3})\b/);
            if (match) {
                input.value = match[1];
            } else if (val.length >= 3) {
                input.value = val.substring(0, 3);
            }
        }

        function generateFlexLinksClient(origin, destination, depStr, retStr) {
            if (!depStr) return '';
            const shifts = [
                { shift: -1, label: '1 Gün Önce' },
                { shift: 0, label: 'Orijinal' },
                { shift: 1, label: '1 Gün Sonra' }
            ];
            const depDate = new Date(depStr);
            const retDate = retStr ? new Date(retStr) : null;

            return shifts.map(s => {
                const nd = new Date(depDate.getTime() + s.shift * 86400000);
                const ndStr = formatISODate(nd);
                let display = `${String(nd.getDate()).padStart(2,'0')}.${String(nd.getMonth()+1).padStart(2,'0')}`;
                let q = `Flights from ${origin} to ${destination} on ${ndStr}`;

                if (retDate) {
                    const nr = new Date(retDate.getTime() + s.shift * 86400000);
                    const nrStr = formatISODate(nr);
                    display += ` - ${String(nr.getDate()).padStart(2,'0')}.${String(nr.getMonth()+1).padStart(2,'0')}`;
                    q += ` through ${nrStr}`;
                }

                const url = `https://www.google.com/travel/flights?q=${encodeURIComponent(q)}&curr=TRY&hl=tr`;
                const isCurr = (s.shift === 0);
                return `<a href="${url}" target="_blank" class="flex-chip ${isCurr ? 'flex-current' : ''}">${s.label} (${display}) ↗</a>`;
            }).join('');
        }

        function evaluateDealClient(track) {
            const price = (track.current_price !== null && track.current_price !== undefined) ? track.current_price : track.last_price;
            const target = track.target_price || 0;
            const lowest = track.lowest_recorded;
            const history = track.price_history || [];

            if (!price) {
                return {
                    badge: '<span class="deal-badge badge-neutral">⏳ FİYAT BEKLENİYOR</span>',
                    desc: 'İlk taramadan sonra analiz gösterilecek.',
                    minPrice: '—',
                    avgPrice: '—',
                    status: 'unknown'
                };
            }

            const prices = history.map(h => h.price).filter(Boolean);
            const avgPrice = prices.length ? Math.round(prices.reduce((a,b)=>a+b, 0) / prices.length) : price;
            const minPrice = prices.length ? Math.min(...prices) : price;

            let badge = '';
            let desc = '';
            let status = 'fair';

            if (price <= target) {
                const diff = target - price;
                badge = `<span class="deal-badge badge-success">🎯 HEDEF ALTI (${price} TL)</span>`;
                desc = `Hedefinizin ${diff} TL altındasınız! Kaçırmadan değerlendirin.`;
                status = 'deal';
            } else if (lowest && price <= lowest) {
                badge = `<span class="deal-badge badge-success">🔥 REKOR DİP FİYAT</span>`;
                desc = 'Şimdiye kadar kaydedilen en ucuz bilet seviyesinde.';
                status = 'deal';
            } else if (price <= target * 1.10 || price <= avgPrice) {
                badge = `<span class="deal-badge badge-warning">🟡 MAKUL SEVİYE</span>`;
                desc = `Ortalama piyasa fiyatında (~${avgPrice} TL), takipte kalın.`;
                status = 'fair';
            } else {
                badge = `<span class="deal-badge badge-danger">🔴 YÜKSEK FİYAT</span>`;
                desc = `Ortalamanın (${avgPrice} TL) üzerinde, indirim bekleyin.`;
                status = 'high';
            }

            return { badge, desc, minPrice, avgPrice, status };
        }

        function renderTracksDOM(tracks) {
            currentTracks = tracks;
            const list = document.getElementById('trackList');

            let filtered = tracks;
            if (currentFilter === 'deal') {
                filtered = tracks.filter(t => {
                    const p = t.current_price ?? t.last_price;
                    return p && (p <= t.target_price || (t.lowest_recorded && p <= t.lowest_recorded));
                });
            } else if (currentFilter === 'pegasus') {
                filtered = tracks.filter(t => (t.airline || (t.best_flight && t.best_flight.airline) || '').toLowerCase().includes('pegasus'));
            } else if (currentFilter === 'ajet') {
                filtered = tracks.filter(t => {
                    const a = (t.airline || (t.best_flight && t.best_flight.airline) || '').toLowerCase();
                    return a.includes('ajet') || a.includes('anadolu');
                });
            } else if (currentFilter === 'thy') {
                filtered = tracks.filter(t => {
                    const a = (t.airline || (t.best_flight && t.best_flight.airline) || '').toLowerCase();
                    return a.includes('thy') || a.includes('türk hava') || a.includes('turkish');
                });
            }

            document.getElementById('activeCount').innerText = `${filtered.length} / ${tracks.length} Aktif Rota`;

            if (!filtered.length) {
                list.innerHTML = `<div class="empty-state">${currentFilter !== 'all' ? 'Seçilen filtreye uygun rota bulunamadı.' : 'Henüz takip edilen rota yok. Yukarıdaki formdan ekleyebilirsiniz.'}</div>`;
                return;
            }

            list.innerHTML = filtered.map(t => {
                const best = t.best_flight || {};
                const price = (t.current_price !== null && t.current_price !== undefined) ? t.current_price : (t.last_price ?? '—');
                const target = t.target_price;
                const airline = t.airline || best.airline || 'Havayolu';
                const flightTime = t.flight_time || (best.departure_time ? `${best.departure_time} - ${best.arrival_time}` : '');
                
                let airlineBg = '#666';
                const low = airline.toLowerCase();
                if (low.includes('pegasus')) airlineBg = '#F5A623';
                else if (low.includes('ajet') || low.includes('anadolu')) airlineBg = '#00AEEF';
                else if (low.includes('thy') || low.includes('türk hava') || low.includes('turkish')) airlineBg = '#A00000';

                const link = t.search_url || `https://www.google.com/travel/flights?q=Flights+from+${t.origin}+to+${t.destination}+on+${t.departure_date}&curr=TRY&hl=tr`;
                const trackId = String(t.id);
                const isChartOpen = openedCharts.has(trackId);
                const isFlexOpen = openedFlexBoxes.has(trackId);
                const isProviderOpen = openedProviders.has(trackId);
                const isArbitrageOpen = openedArbitrages.has(trackId);

                const deal = evaluateDealClient(t);
                const flexChipsHtml = generateFlexLinksClient(t.origin, t.destination, t.departure_date, t.return_date);
                const providerButtonsHtml = generateProviderButtonsClient(t.origin, t.destination, t.departure_date, t.return_date);

                return `
                <div class="track-card" id="card-${trackId}">
                    <div class="card-top">
                        <div>
                            <div class="card-title">${t.title}</div>
                            <div class="deal-status-row">
                                ${deal.badge}
                                <span class="deal-desc">${deal.desc}</span>
                            </div>
                        </div>
                        <button type="button" class="btn btn-secondary" onclick="deleteTrack('${trackId}')" style="padding:4px 10px; font-size:12px; color:#b4341e;">Sil</button>
                    </div>
                    <div class="route-info">
                        <span class="route-badge">${t.origin} ⇄ ${t.destination}</span>
                        <span>(${t.departure_date} - ${t.return_date || 'Tek Yön'})</span>
                        <span class="airline-tag" style="background:${airlineBg}">${airline}</span>
                        ${flightTime ? `<span>🕒 ${flightTime}</span>` : ''}
                    </div>
                    <div class="price-box">
                        <div class="current-price">${price} TL</div>
                        <div class="target-price">/ Hedef: ${target} TL</div>
                        <div class="stat-pills">
                            <span class="stat-pill">Dip: ${deal.minPrice} TL</span>
                            <span class="stat-pill">Ort: ${deal.avgPrice} TL</span>
                        </div>
                    </div>
                    <div class="card-actions">
                        <a href="${link}" target="_blank" class="btn btn-primary" style="padding:7px 14px; font-size:12px;">✈️ Bilet Ara / Gör ↗</a>
                        <button type="button" class="btn btn-secondary" onclick="toggleProviders('${trackId}')" style="padding:7px 14px; font-size:12px;">🏢 Tüm Havayolları (7) ▾</button>
                        <button type="button" class="btn btn-secondary" onclick="toggleArbitrage('${trackId}', '${t.origin}', '${t.destination}', '${t.departure_date}', '${t.return_date || ''}')" style="padding:7px 14px; font-size:12px;">🌍 VPN & Pazar Arbitrajı 🔍</button>
                        <button type="button" class="btn btn-secondary" onclick="toggleChart('${trackId}')" style="padding:7px 14px; font-size:12px;">📊 Fiyat Trendi</button>
                        <button type="button" class="btn btn-secondary" onclick="toggleFlex('${trackId}')" style="padding:7px 14px; font-size:12px;">📅 Esnek Günler (±1 Gün)</button>
                    </div>
                    <div id="provider-box-${trackId}" class="provider-box" style="display:${isProviderOpen ? 'block' : 'none'};">
                        <div class="provider-box-title">
                            <span>🏢 Resmi Havayolu Siteleri & Karşılaştırma Motorları</span>
                            <span class="incognito-tag">🕵️ Gizli Mod / Temiz Oturum</span>
                        </div>
                        <div class="provider-grid">
                            ${providerButtonsHtml}
                        </div>
                    </div>
                    <div id="arbitrage-box-${trackId}" class="arbitrage-box" style="display:${isArbitrageOpen ? 'block' : 'none'};">
                        <div class="arbitrage-header">
                            <div class="arbitrage-title">🌍 Çoklu Pazar & VPN Fiyat Arbitrajı (Gizli Mod + Temiz Çerez)</div>
                            <button type="button" class="btn btn-primary" onclick="runArbitrage('${trackId}', '${t.origin}', '${t.destination}', '${t.departure_date}', '${t.return_date || ''}')" style="padding:4px 10px; font-size:11px;">🔄 Canlı Tara</button>
                        </div>
                        <div id="arbitrage-results-${trackId}">
                            <div style="font-size:12px; color:var(--text-muted); padding:6px 0;">TR 🇹🇷, DE 🇩🇪 ve US 🇺🇸 pazarlarındaki bölgesel bilet fiyatlarını ve yerel VPN/Proxy avantajını canlı karşılaştırmak için <b>'Canlı Tara'</b> butonuna tıklayın.</div>
                        </div>
                    </div>
                    <div id="flex-box-${trackId}" class="flex-box" style="display:${isFlexOpen ? 'block' : 'none'};">
                        <div class="flex-box-title">📅 Alternatif Tarih Fiyatları (±1 Gün):</div>
                        <div class="flex-chip-list">${flexChipsHtml}</div>
                    </div>
                    <div id="chart-box-${trackId}" class="chart-box" style="display:${isChartOpen ? 'block' : 'none'};">
                        ${isChartOpen ? renderPriceChart(t.price_history || [], t.target_price) : ''}
                    </div>
                </div>`;
            }).join('');
        }

        function renderCampaignsDOM(campaigns) {
            const list = document.getElementById('campaignList');
            const items = Array.isArray(campaigns) ? campaigns : (campaigns.seen || []);
            if (!items.length) {
                list.innerHTML = '<div class="empty-state">Henüz kampanya duyurusu bulunamadı.</div>';
                return;
            }
            list.innerHTML = items.slice(0, 10).map(c => {
                const title = typeof c === 'string' ? c : (c.title || 'Kampanya');
                const link = (typeof c === 'object' && c.link) ? c.link : ('https://www.google.com/search?q=' + encodeURIComponent(title));
                const date = (typeof c === 'object' && c.date) ? c.date : '';
                return `
                <div class="campaign-item">
                    <a href="${link}" target="_blank">${title}</a>
                    ${date ? `<div class="campaign-date">${date}</div>` : ''}
                </div>`;
            }).join('');
        }

        function updateDaemonUI(daemon) {
            const pill = document.getElementById('daemonStatusPill');
            const btn = document.getElementById('btnDaemon');
            if (!pill || !btn) return;

            isDaemonRunning = !!(daemon && daemon.running);
            if (isDaemonRunning) {
                pill.className = 'daemon-pill daemon-pill-running';
                pill.innerHTML = `<span class="daemon-dot"></span> Radar: Aktif (PID: ${daemon.pid})`;
                btn.innerText = '⏹ Radarı Durdur';
                btn.style.color = '#b4341e';
            } else {
                pill.className = 'daemon-pill daemon-pill-stopped';
                pill.innerHTML = `<span class="daemon-dot"></span> Radar: Durduruldu`;
                btn.innerText = '▶ Radarı Başlat';
                btn.style.color = 'var(--text)';
            }
        }

        async function toggleDaemon() {
            const btn = document.getElementById('btnDaemon');
            btn.disabled = true;
            try {
                const endpoint = isDaemonRunning ? '/api/daemon/stop' : '/api/daemon/start';
                const res = await fetch(endpoint, { method: 'POST' });
                const data = await res.json();
                updateDaemonUI(data);
                showToast(isDaemonRunning ? '🟢 Radar arka planda başlatıldı (2 saatte bir tarama).' : '⏹ Radar durduruldu.');
            } catch (e) {
                showToast('⚠️ Radar işlemi hatası: ' + e, true);
            } finally {
                btn.disabled = false;
            }
        }

        async function openLogModal() {
            const modal = document.getElementById('logModal');
            const pre = document.getElementById('logContent');
            modal.style.display = 'flex';
            pre.innerText = 'Loglar okunuyor...';
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                pre.innerText = (data.logs && data.logs.length) ? data.logs.join('\n') : 'Log kaydı bulunamadı.';
                modal.querySelector('.modal-body').scrollTop = modal.querySelector('.modal-body').scrollHeight;
            } catch (e) {
                pre.innerText = 'Log yükleme hatası: ' + e;
            }
        }

        function closeLogModal() {
            document.getElementById('logModal').style.display = 'none';
        }

        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.last_check) {
                    document.getElementById('lastCheckMeta').innerText = data.last_check;
                }
                if (data.daemon) {
                    updateDaemonUI(data.daemon);
                }
                renderTracksDOM(data.tracks || []);
                renderCampaignsDOM(data.campaigns || []);
            } catch (err) {
                console.error("Status error:", err);
            }
        }

        async function scanNow() {
            const btn = document.getElementById('btnScan');
            btn.disabled = true;
            btn.innerText = '⚡ Taranıyor...';
            try {
                const res = await fetch('/api/scan', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('⚡ Tarama tamamlandı, fiyatlar güncellendi.');
                    await updateStatus();
                } else {
                    showToast('⚠️ Tarama hatası: ' + (data.error || 'Bilinmeyen hata'), true);
                }
            } catch (e) {
                showToast('⚠️ Bağlantı hatası: ' + e, true);
            } finally {
                btn.disabled = false;
                btn.innerText = '⚡ Şimdi Tara';
            }
        }

        async function deleteTrack(id) {
            try {
                const res = await fetch('/api/tracks/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });
                const data = await res.json();
                if (data.success) {
                    openedCharts.delete(String(id));
                    openedFlexBoxes.delete(String(id));
                    openedProviders.delete(String(id));
                    openedArbitrages.delete(String(id));
                    showToast('🗑️ Rota takipten çıkarıldı.');
                    await updateStatus();
                }
            } catch (e) {
                showToast('⚠️ Silme hatası: ' + e, true);
            }
        }

        async function testNotify() {
            try {
                const res = await fetch('/api/notify-test', { method: 'POST' });
                const data = await res.json();
                if (data.success) showToast('🔔 Test bildirimi cihaza gönderildi!');
            } catch (e) {
                showToast('⚠️ Bildirim hatası: ' + e, true);
            }
        }

        // Gidiş tarihi seçilince dönüş tarihinin minimumunu gidişe eşitle
        const depInput = document.querySelector('input[name="departure_date"]');
        const retInput = document.querySelector('input[name="return_date"]');
        if (depInput && retInput) {
            depInput.addEventListener('change', () => {
                retInput.min = depInput.value;
                if (retInput.value && retInput.value < depInput.value) {
                    retInput.value = depInput.value;
                }
            });
        }

        document.getElementById('addTrackForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerText = 'Uçuş aranıyor...';

            const formData = new FormData(form);
            const depDate = formData.get('departure_date');
            const retDate = formData.get('return_date');

            if (retDate && retDate < depDate) {
                showToast('⚠️ Dönüş tarihi gidiş tarihinden önce olamaz!', true);
                submitBtn.disabled = false;
                submitBtn.innerText = 'Takibe Al ve İlk Fiyatı Çek';
                return;
            }

            const payload = {
                title: formData.get('title'),
                origin: formData.get('origin'),
                destination: formData.get('destination'),
                departure_date: depDate,
                return_date: retDate,
                target_price: parseFloat(formData.get('target_price'))
            };

            try {
                const res = await fetch('/api/tracks/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    form.reset();
                    form.querySelector('input[name="origin"]').value = 'ADB';
                    form.querySelector('input[name="destination"]').value = 'IST';
                    showToast('✅ Yeni rota başarıyla takibe alındı!');
                    await updateStatus();
                } else {
                    showToast('⚠️ Hata: ' + (data.error || 'Rota eklenemedi'), true);
                }
            } catch (err) {
                showToast('⚠️ İstek hatası: ' + err, true);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = 'Takibe Al ve İlk Fiyatı Çek';
            }
        });

        // Sayfa açıldığında ilk durumu çek ve 10 saniyede bir güncelle
        updateStatus();
        setInterval(updateStatus, 10000);
    </script>
</body>
</html>
"""

class RadarHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        cleaned = clean_for_json(data)
        self.wfile.write(json.dumps(cleaned, ensure_ascii=False).encode('utf-8'))

    def send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ['/', '/index.html']:
            self.handle_index()
        elif parsed.path == '/api/status':
            self.handle_status()
        elif parsed.path == '/api/daemon':
            self.send_json(radar_helpers.get_daemon_status())
        elif parsed.path == '/api/logs':
            self.send_json({'logs': radar_helpers.get_recent_logs(50)})
        elif parsed.path == '/api/airports':
            self.send_json({'airports': airline_providers.get_all_airports_list()})
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/scan':
            self.handle_scan()
        elif parsed.path == '/api/tracks/add':
            self.handle_add_track()
        elif parsed.path == '/api/tracks/delete':
            self.handle_delete_track()
        elif parsed.path == '/api/notify-test':
            self.handle_notify_test()
        elif parsed.path == '/api/daemon/start':
            self.send_json(radar_helpers.start_daemon())
        elif parsed.path == '/api/daemon/stop':
            self.send_json(radar_helpers.stop_daemon())
        elif parsed.path == '/api/arbitrage':
            self.handle_arbitrage()
        else:
            self.send_error(404)

    def handle_arbitrage(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            origin = data.get('origin', 'ADB')
            dest = data.get('destination', 'SAW')
            dep_date = data.get('departure_date', '')
            ret_date = data.get('return_date', None)
            proxy_url = airline_providers.get_active_proxy()
            res = airline_providers.probe_geo_arbitrage(origin, dest, dep_date, ret_date, proxy_url)
            res['active_proxy'] = proxy_url
            self.send_json(res)
        except Exception as e:
            log(f"Arbitrage error: {e}")
            self.send_json({'ok': False, 'error': str(e)}, 500)

    def handle_index(self):
        tracks = load_json(TRACKS_FILE, [])
        campaigns = load_json(RSS_DB_FILE, [])
        last_check = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

        # Static rendering for fast first paint
        track_items = ''
        for t in tracks:
            price = t.get('current_price') or t.get('last_price')
            target = t.get('target_price', 0)
            best = t.get('best_flight') or {}
            airline = t.get('airline') or best.get('airline') or 'Havayolu'
            flight_time = t.get('flight_time') or (f"{best.get('departure_time')} - {best.get('arrival_time')}" if best.get('departure_time') else '')
            color = get_flight_color(airline)
            deal = radar_helpers.evaluate_deal(t)
            price_display = f"{price} TL" if price else '—'
            raw_link = t.get('search_url') or generate_google_flights_link(t['origin'], t['destination'], t['departure_date'], t.get('return_date'))
            link = html.escape(str(raw_link))
            t_id = html.escape(str(t.get('id', '')))
            t_title = html.escape(str(t.get('title', '')))
            t_origin = html.escape(str(t.get('origin', '')))
            t_destination = html.escape(str(t.get('destination', '')))
            t_dep = html.escape(str(t.get('departure_date', '')))
            t_ret = html.escape(str(t.get('return_date') or 'Tek Yön'))
            t_airline = html.escape(str(airline))
            t_time = html.escape(str(flight_time))

            flex_links = radar_helpers.get_flexible_date_links(t_origin, t_destination, t_dep, t.get('return_date'))
            flex_chips = ''.join([
                f'<a href="{html.escape(fl["url"])}" target="_blank" class="flex-chip {"flex-current" if fl["is_current"] else ""}">{html.escape(fl["label"])} ({html.escape(fl["dates"])}) ↗</a>'
                for fl in flex_links
            ])

            p_links = airline_providers.get_all_provider_links(t_origin, t_destination, t_dep, t.get('return_date'))
            provider_buttons = ''.join([
                f'<a href="{html.escape(p["url"])}" target="_blank" rel="noopener noreferrer" class="provider-btn" style="border-left: 3px solid {p["color"]};">'
                f'<span>{p["icon"]}</span> <span>{html.escape(p["name"])}</span> <span style="font-size:10px; color:var(--text-muted);">↗</span>'
                f'</a>'
                for p in p_links
            ])

            track_items += f'''
            <div class="track-card" id="card-{t_id}">
                <div class="card-top">
                    <div>
                        <div class="card-title">{t_title}</div>
                        <div class="deal-status-row">
                            {deal['badge']}
                            <span class="deal-desc">{deal['desc']}</span>
                        </div>
                    </div>
                    <button type="button" class="btn btn-secondary" onclick="deleteTrack('{t_id}')" style="padding:4px 10px; font-size:12px; color:#b4341e;">Sil</button>
                </div>
                <div class="route-info">
                    <span class="route-badge">{t_origin} ⇄ {t_destination}</span>
                    <span>({t_dep} - {t_ret})</span>
                    <span class="airline-tag" style="background:{color}">{t_airline}</span>
                    {f"<span>🕒 {t_time}</span>" if flight_time else ""}
                </div>
                <div class="price-box">
                    <div class="current-price">{price_display}</div>
                    <div class="target-price">/ Hedef: {target} TL</div>
                    <div class="stat-pills">
                        <span class="stat-pill">Dip: {deal.get('min_price', '—')} TL</span>
                        <span class="stat-pill">Ort: {deal.get('avg_price', '—')} TL</span>
                    </div>
                </div>
                <div class="card-actions">
                    <a href="{link}" target="_blank" class="btn btn-primary" style="padding:7px 14px; font-size:12px;">✈️ Bilet Ara / Gör ↗</a>
                    <button type="button" class="btn btn-secondary" onclick="toggleProviders('{t_id}')" style="padding:7px 14px; font-size:12px;">🏢 Tüm Havayolları (7) ▾</button>
                    <button type="button" class="btn btn-secondary" onclick="toggleArbitrage('{t_id}', '{t_origin}', '{t_destination}', '{t_dep}', '{t_ret}')" style="padding:7px 14px; font-size:12px;">🌍 VPN & Pazar Arbitrajı 🔍</button>
                    <button type="button" class="btn btn-secondary" onclick="toggleChart('{t_id}')" style="padding:7px 14px; font-size:12px;">📊 Fiyat Trendi</button>
                    <button type="button" class="btn btn-secondary" onclick="toggleFlex('{t_id}')" style="padding:7px 14px; font-size:12px;">📅 Esnek Günler (±1 Gün)</button>
                </div>
                <div id="provider-box-{t_id}" class="provider-box" style="display:none;">
                    <div class="provider-box-title">
                        <span>🏢 Resmi Havayolu Siteleri & Karşılaştırma Motorları</span>
                        <span class="incognito-tag">🕵️ Gizli Mod / Temiz Oturum</span>
                    </div>
                    <div class="provider-grid">
                        {provider_buttons}
                    </div>
                </div>
                <div id="arbitrage-box-{t_id}" class="arbitrage-box" style="display:none;">
                    <div class="arbitrage-header">
                        <div class="arbitrage-title">🌍 Çoklu Pazar & VPN Fiyat Arbitrajı (Gizli Mod + Temiz Çerez)</div>
                        <button type="button" class="btn btn-primary" onclick="runArbitrage('{t_id}', '{t_origin}', '{t_destination}', '{t_dep}', '{t_ret}')" style="padding:4px 10px; font-size:11px;">🔄 Canlı Tara</button>
                    </div>
                    <div id="arbitrage-results-{t_id}">
                        <div style="font-size:12px; color:var(--text-muted); padding:6px 0;">TR 🇹🇷, DE 🇩🇪 ve US 🇺🇸 pazarlarındaki bölgesel bilet fiyatlarını ve yerel VPN/Proxy avantajını canlı karşılaştırmak için <b>'Canlı Tara'</b> butonuna tıklayın.</div>
                    </div>
                </div>
                <div id="flex-box-{t_id}" class="flex-box" style="display:none;">
                    <div class="flex-box-title">📅 Alternatif Tarih Fiyatları (±1 Gün):</div>
                    <div class="flex-chip-list">{flex_chips}</div>
                </div>
                <div id="chart-box-{t_id}" class="chart-box" style="display:none;"></div>
            </div>'''

        campaign_items = ''
        campaign_list = campaigns if isinstance(campaigns, list) else campaigns.get('seen', [])
        for c in campaign_list[:10]:
            raw_title = c if isinstance(c, str) else c.get('title', 'Kampanya')
            title = html.escape(str(raw_title))
            link = c.get('link') if isinstance(c, dict) and c.get('link') else f"https://www.google.com/search?q={urllib.parse.quote(str(raw_title))}"
            date = html.escape(str(c.get('date', ''))) if isinstance(c, dict) else ''
            campaign_items += f'''
            <div class="campaign-item">
                <a href="{link}" target="_blank">{title}</a>
                {f'<div class="campaign-date">{date}</div>' if date else ''}
            </div>'''

        airports_options = "".join([f'<option value="{code}">{code} - {info["city"]} ({info["name"]})</option>' for code, info in airline_providers.AIRPORTS.items()])
        rendered = HTML_TEMPLATE.replace('__LAST_CHECK__', last_check)
        rendered = rendered.replace('__TRACK_COUNT__', str(len(tracks)))
        rendered = rendered.replace('__AIRPORTS_DATALIST__', airports_options)
        rendered = rendered.replace('__TRACK_ITEMS__', track_items if tracks else '<div class="empty-state">Henüz takip edilen rota yok.</div>')
        rendered = rendered.replace('__CAMPAIGN_ITEMS__', campaign_items if campaign_list else '<div class="empty-state">Henüz kampanya yok.</div>')

        self.send_html(rendered)

    def handle_status(self):
        tracks = load_json(TRACKS_FILE, [])
        campaigns = load_json(RSS_DB_FILE, [])
        last_check = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
        daemon_status = radar_helpers.get_daemon_status()
        self.send_json({
            'status': 'online',
            'last_check': last_check,
            'tracks': tracks,
            'campaigns': campaigns,
            'daemon': daemon_status
        })

    def handle_scan(self):
        try:
            cmd = [sys.executable, RADAR_SCRIPT, '--scan']
            subprocess.run(cmd, check=True)
            tracks = load_json(TRACKS_FILE, [])
            log("Manuel tarama tetiklendi")
            self.send_json({'success': True, 'count': len(tracks)})
        except Exception as e:
            log(f"Scan failed: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_add_track(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)

            required = ['origin', 'destination', 'departure_date', 'target_price', 'title']
            for field in required:
                if field not in data or not data[field]:
                    self.send_json({'success': False, 'error': f'Eksik alan: {field}'}, 400)
                    return

            tracks = load_json(TRACKS_FILE, [])
            new_id = f"trk_{int(datetime.datetime.now().timestamp())}"
            now_str = datetime.datetime.now().strftime('%d.%m %H:%M')

            try:
                target_price = float(data['target_price'])
            except (ValueError, TypeError):
                self.send_json({'success': False, 'error': 'Geçersiz hedef fiyat formatı'}, 400)
                return

            track = {
                'id': new_id,
                'title': data['title'].strip(),
                'origin': data['origin'].upper().strip(),
                'destination': data['destination'].upper().strip(),
                'departure_date': data['departure_date'].strip(),
                'return_date': data.get('return_date', '').strip() or None,
                'target_price': target_price,
                'current_price': None,
                'last_price': None,
                'lowest_recorded': None,
                'airline': None,
                'flight_time': None,
                'best_flight': {},
                'search_url': None,
                'last_checked': now_str,
                'price_history': []
            }

            try:
                crawler = load_crawler()
                res = crawler.search_flights(track['origin'], track['destination'], track['departure_date'], track.get('return_date'))
                if res.get('ok') and res.get('flights'):
                    cheapest = res['flights'][0]
                    p = cheapest.get('price')
                    track['current_price'] = p
                    track['last_price'] = p
                    track['lowest_recorded'] = p
                    track['airline'] = cheapest.get('airline')
                    track['flight_time'] = f"{cheapest.get('departure_time')} - {cheapest.get('arrival_time')}"
                    track['best_flight'] = cheapest
                    track['search_url'] = res.get('search_url')
                    track['price_history'] = [{
                        'time': now_str,
                        'price': p,
                        'airline': cheapest.get('airline', 'Havayolu')
                    }]
            except Exception as e:
                log(f"Yeni rota ilk tarama hatası: {e}")

            tracks.append(track)
            save_json(TRACKS_FILE, tracks)
            log(f"Yeni rota eklendi: {track['title']}")
            self.send_json({'success': True, 'track': track})
        except Exception as e:
            log(f"Add track error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_delete_track(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            track_id = data.get('id')

            if track_id is None:
                self.send_json({'success': False, 'error': 'Eksik id'}, 400)
                return

            tracks = load_json(TRACKS_FILE, [])
            tracks = [t for t in tracks if str(t.get('id')) != str(track_id)]
            save_json(TRACKS_FILE, tracks)
            log(f"Takip silindi: {track_id}")
            self.send_json({'success': True})
        except Exception as e:
            log(f"Delete track error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_notify_test(self):
        try:
            subprocess.run([
                'termux-notification',
                '--title', '✈️ Test Bildirimi',
                '--content', 'Flight Radar test mesajı başarıyla iletildi!'
            ], check=False)
            self.send_json({'success': True})
        except Exception as e:
            log(f"Notify test failed: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

def run(port=8080):
    server = HTTPServer(('0.0.0.0', port), RadarHandler)
    log(f"Server started on port {port}")
    print(f"Flight Radar Web Server running on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Server stopped")
        server.shutdown()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
