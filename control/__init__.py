# -*- coding: utf-8 -*-
"""
control — avci dronun guduum ve karar mekanizmasi.

    main.py         — GOREV GOZETMENI + giris noktasi (python3 -m control.main):
                      50 Hz kontrol dongusu, GPS <-> gorsel faz devir kapisi.
    gps_approach.py — GPSTakip: kalkis + BOZUK GNSS'i temizleyerek yaklasma
                      (fusion/gnss_filtre.py cikisiyla; standoff'ta pace eder).
    gorsel_takip.py — GorselTakip: basit IBVS gorsel guduum — komut YALNIZCA
                      bbox pikselinden turer (gorsel fazda GPS kullanilmaz).
    common.py       — iki hattin paylastigi skaler yardimcilar + KomutGonderici
                      (tek komut cikisi; faz devrinde surekliligi saglar).

Arac I/O'su sdk/drone_sdk.py'de, tespit hatti perception paketindedir.
"""
