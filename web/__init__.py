# -*- coding: utf-8 -*-
"""
web — yer kontrol istasyonu (yerel HTTP arayuzu). Gorevin KOSTURUCUSU burasidir.

    server.py   — 50 Hz kontrol dongusu + /api/telemetry, /api/command
                  (python -m web.server -> http://127.0.0.1:8001)
    server.html — tek sayfa arayuz: kusbakisi harita (avci / ham hedef /
                  temiz hedef / istasyon noktasi) + telemetri + olay gunlugu

IKI MOD
    GPS     — yalniz GPS fazi (kalkis + istasyon tutma). Kamera hatti HIC
              calismaz; dedektor (torch/ultralytics) yuklenmez.
    HIBRIT  — GPS + KAMERA. Ayni GPS faziyla baslar, devir kapisi acilinca
              (control.main.PhaseSupervisor) gorsel faza gecer ve komut
              YALNIZCA kameradan turer. Hedef kaybolursa GPS'e donulur.

Guduum control/ paketinden gelir; bu paket YALNIZ gozlem, baslat/durdur ve
donguyu kosturma kabugudur — GUDUM YASASI ICERMEZ:
    GPS fazi    control.gps_approach.GPSTracker
    gorsel faz  control.visual_tracking.VisualTracker
    faz kapisi  control.main.PhaseSupervisor
    komut kapisi control.common.CommandSender (TEK cikis)

⛔ Gorsel fazda GPS/GNSS komuta GIRMEZ (yarisma kurali). Cagrilan tek GPS
  islevi `clean_target()`'dir ve donen deger hicbir komuta girmez.
⛔ `get_debug_truth()` KULLANILMAZ — o kanal yarismada gelmez.
⚠ Ekran paylasimi/kamera goruntusu YOKTUR. Hibrit modda kamera hatti oyun
  EKRANINI yakalar; oyun penceresi GORUNUR/ONDE kalmalidir.
"""
