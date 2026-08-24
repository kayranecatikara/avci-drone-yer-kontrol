# -*- coding: utf-8 -*-
"""
control — avci dronun guduum ve karar mekanizmasi.

    main.py         — PhaseSupervisor: YALNIZ faz gecisi (GPS <-> GORSEL kapilari).
                      Komut uretmez, dongu tutmaz, giris noktasi degildir;
                      kosturucu web/server.py'dir (hibrit mod).
    gps_approach.py — GPSTracker: kalkis + BOZUK GNSS'i temizleyerek hedefin
                      KUYRUGUNDAKI istasyon noktasina oturma
                      (filter/gnss_filtre_v2.py cikisiyla; hedef hizi ILERI
                      BESLENIR).
    visual_tracking.py — VisualTracker: IBVS gorsel guduum + olculmus kamera modeli.
                      Komut YALNIZCA bbox pikselinden ve KENDI IMU'muzdan turer.
    common.py       — birim siniri (Telemetri), olculmus HIZ->CUBUK cevirici
                      (VelocityToStick) ve TEK komut cikisi (CommandSender).

KATMANLAR
    yasa (m/s hiz setpoint'i)  ->  cevirici (olculmus zarf)  ->  komut kapisi
    Yasaya dokunmadan cevirici degistirilebilir; tersi de dogru.

Arac I/O'su sdk/drone_sdk.py'de, tespit hatti perception paketindedir.
"""
