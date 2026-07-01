# -*- coding: utf-8 -*-
"""
================================================================================
 AVCI DRONE — GIRIS NOKTASI (main)
================================================================================
Tum sistemi baslatan tek dosya. Web arayuzu + kontrol beyni + gorsel tespit
thread'lerini web.server.main() uzerinden ayaga kaldirir.

Calistir:   python main.py
Tarayici:   http://127.0.0.1:8000
Kapat:      Ctrl + C

PAKET HARITASI (sartname teslim eslemesi):
  sdk/        -> simulasyon I/O (telemetri/kontrol)          [drone_sdk]
  fusion/     -> sensor fuzyonu / GNSS filtre + hiz kestirim [inovasyonlu_j_v2]
  guidance/   -> guduum ve karar (GPS yaklasma + IBVS)       [ana_kontrol, ibvs_guidance]
  detection/  -> hedef tespit + tracking + kare yakalama     [gorsel_tespit, pencere_yakala]
  web/        -> arayuz + sunucu (telemetri, FPV, butonlar)  [server, index.html]
  models/     -> egitilmis YOLO agirligi (.pt)               [best.pt]
  arac/       -> bagimsiz GPS analiz/gorsellestirme          [gps_*]
  veri/       -> calisma ciktilari (log/json/png; uretilir)
================================================================================
"""
from web.server import main

if __name__ == "__main__":
    main()
