# ✈️ Flight Radar & Geo-Arbitrage Engine

Kişiselleştirilmiş, yerel ve çoklu havayolu entegrasyonuna sahip akıllı uçak bileti takip ve fiyat arbitraj radarı.

## 🌟 Öne Çıkan Özellikler

- **🏢 7 Sağlayıcı & Doğrudan Biletleme**:
  - Pegasus (`flypgs.com`)
  - AJet (`ajet.com`)
  - Türk Hava Yolları (`turkishairlines.com`)
  - SunExpress (`sunexpress.com`)
  - Skyscanner
  - Enuygun
  - Google Flights
- **🌍 Çoklu Pazar & Geo-Arbitraj (VPN & Pazar Taraması)**:
  - Türkiye 🇹🇷 (`gl=TR`), Almanya 🇩🇪 (`gl=DE`) ve ABD 🇺🇸 (`gl=US`) satış noktalarını eşzamanlı sorgular.
  - Hangi bölgesel pazardan bilet almanın daha avantajlı olduğunu ve potansiyel TL kazancını canlı hesaplar.
- **🕵️ Gizli Mod & Çerez Kalkanı**:
  - Fiyat şişirmelerini ve kullanıcı takibini önlemek için izole `DNT: 1`, `Sec-GPC: 1` ve rotasyonel mobil/masaüstü User-Agent başlıkları.
- **📍 48 Havalimanı (IATA)**:
  - Türkiye'deki tüm havalimanları ve popüler yurt dışı aktarma merkezleri (BER, FRA, MUC, AMS, LHR).
- **📰 Editoryal Sıcak Gazete Arayüzü**:
  - Newsreader Serif + Plus Jakarta Sans + JetBrains Mono tipografisi, rekor dip/ortalamalar ve SVG trend grafikleri.
- **🌐 Cloudflare Tunnel ile Global Erişim**:
  - Port yönlendirme gerektirmeden internet üzerinden her yerden güvenli HTTPS erişimi.

## 🚀 Başlangıç

### Gereksinimler
- Python 3.10+
- Termux (Android) veya Linux / macOS

### Çalıştırma
```bash
# Web Sunucusunu Başlat (Port 8080)
python3 web_server.py 8080

# Arka Plan Radar Taraması
python3 flight_radar.py --scan

# 2 Saatte Bir Arka Plan Daemon'ı
python3 flight_radar.py --daemon
```

### Global İnternet Erişimi (Cloudflare Tunnel)
```bash
cloudflared tunnel --url http://localhost:8080
```

---
*Geliştirici: YagTur123*
