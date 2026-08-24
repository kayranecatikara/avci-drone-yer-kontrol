# -*- coding: utf-8 -*-
"""VERISETI araclari — DETECTION (tek sinif bbox) veri hatti.

Burasi pose/ DEGIL: uretilen etiketler saf detection'dir.
  negatif_topla.py -> BOS .txt (background ornegi; hard negative madencisi)
  bbox_etiketle.py -> "0 cx cy w h" (tek sinif bbox; canli etiketleyici)

negatif_topla, pose/geometri.py'yi KULLANIR ama keypoint URETMEZ: 6 kp yalnizca
ucagin 3B sekil modeli olarak, "hedef kadrajda mi" sorusunu cozmek icin
projekte edilir. Ciktiya girmez.

GELISTIRME ARACLARI — teslim paketine girmez.
"""
