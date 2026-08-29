# -*- coding: utf-8 -*-
"""
control — avci dronun guduum ve karar mekanizmasi.

    main.py         — PhaseSupervisor: YALNIZ faz gecisi (KALKIS -> GPS -> GORSEL
                      -> CARPMA kapilari).
                      Komut uretmez, dongu tutmaz, giris noktasi degildir;
                      kosturucu web/server.py'dir (hibrit mod).
    takeoff.py      — TakeoffLaw: KALKIS fazi. Yalniz dikey tirmanis
                      (TakeoffCfg.VZ = 12 m/s); yatay komut URETMEZ ve bu bir
                      korumadir — GNSS filtresinin isinma transientini maskeler.
    gps_approach.py — GPSTracker: BOZUK GNSS'i temizleyerek hedefin
                      KUYRUGUNDAKI istasyon noktasina oturma
                      (filter/gnss_filtre_v2.py cikisiyla; hedef hizi ILERI
                      BESLENIR).
    visual_tracking.py — VisualTracker: IBVS gorsel guduum + olculmus kamera modeli.
                      Komut YALNIZCA bbox pikselinden ve KENDI IMU'muzdan turer.
                      Hedefin KUYRUGUNA oturur (TRAIL_RANGE_M) ve orada kalir.
    spike.py        — SpikeLaw: CARPMA fazi. Gorsel fazdan SONRA gelir; kuyrukta
                      oturmayi birakip TEMAS menziline (ATTACK_RANGE_M) kadar
                      kapanir. Girdisi yine YALNIZ bbox pikseli + kendi IMU'muz.
                      Kapi: 10 s kesintisiz gorsel guduum (Cfg.SPIKE_AFTER_VISUAL_S).
    common.py       — birim siniri (Telemetri), olculmus HIZ->CUBUK cevirici
                      (VelocityToStick) ve TEK komut cikisi (CommandSender).

KATMANLAR
    yasa (m/s hiz setpoint'i)  ->  cevirici (olculmus zarf)  ->  komut kapisi
    takeoff.py / gps_approach.py / visual_tracking.py / spike.py  ->  hepsi YASA
    Yasaya dokunmadan cevirici degistirilebilir; tersi de dogru.

Arac I/O'su sdk/drone_sdk.py'de, tespit hatti perception paketindedir.
"""
