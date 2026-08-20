# -*- coding: utf-8 -*-
"""
fusion — sensor fuzyonu / filtreleme.

    gnss_filtre.py — GNSSFiltre: hedefin BOZUK GNSS akisini nedensel olarak
                     temizler (z-spike + x/y-spike kapilari), son-N noktadan
                     lineer hiz kestirir ve gecikmeyi guven-agirlikli lead ile
                     telafi eder. Cikisi control/gps_approach.py'nin TEK hedef
                     girdisidir; gorsel fazda KULLANILMAZ.
"""
