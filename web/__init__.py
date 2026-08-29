# -*- coding: utf-8 -*-
"""
web — yer kontrol istasyonu (yerel HTTP arayuzu). Gorevin KOSTURUCUSU burasidir.

    server.py   — 50 Hz kontrol dongusu + /api/telemetry, /api/command
                  (python -m web.server -> http://127.0.0.1:8001)
    server.html — tek sayfa arayuz: kusbakisi harita (avci / ham hedef /
                  temiz hedef / istasyon noktasi) + telemetri + olay gunlugu

UC MOD (ucu de AYNI control/ kodunu cagirir; fark yalnizca HANGI FAZLARIN
acilabildigidir — yasa, kapi ve zarf sabitleri MODA GORE DEGISMEZ)
    GPS            — kalkis + istasyon tutma. Kamera hatti HIC calismaz;
                     dedektor (torch/ultralytics) yuklenmez.
    HIBRIT         — GPS + KAMERA. Ayni kalkis/GPS fazlariyla baslar, devir
                     kapisi acilinca (control.main.PhaseSupervisor) gorsel faza
                     gecer ve komut YALNIZCA kameradan turer. Arac hedefin
                     kuyrugunda OTURUR ve KALIR; carpma fazi ACILMAZ. Hedef
                     kaybolursa GPS'e donulur.
    HIBRIT+CARPMA  — HIBRIT ile birebir ayni akis; tek fark, gorsel gudum
                     10 s kesintisiz surunce CARPMA fazinin (control.spike)
                     acilabilmesidir.

Guduum control/ paketinden gelir; bu paket YALNIZ gozlem, baslat/durdur ve
donguyu kosturma kabugudur — GUDUM YASASI ICERMEZ:
    kalkis fazi  control.takeoff.TakeoffLaw
    GPS fazi     control.gps_approach.GPSTracker
    gorsel faz   control.visual_tracking.VisualTracker
    carpma fazi  control.spike.SpikeLaw
    faz kapisi   control.main.PhaseSupervisor  (KALKIS -> GPS -> GORSEL -> CARPMA)
    komut kapisi control.common.CommandSender  (TEK cikis)

⛔ Gorsel fazda GPS/GNSS komuta GIRMEZ (yarisma kurali). Cagrilan tek GPS
  islevi `clean_target()`'dir ve donen deger hicbir komuta girmez.
⛔ `get_debug_truth()` KULLANILMAZ — o kanal yarismada gelmez.
⚠ Ekran paylasimi/kamera goruntusu YOKTUR. Hibrit modda kamera hatti oyun
  EKRANINI yakalar; oyun penceresi GORUNUR/ONDE kalmalidir.
"""
