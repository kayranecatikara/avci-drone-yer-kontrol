# -*- coding: utf-8 -*-
"""
filtre — hedefin BOZUK GNSS akisini temizleyen kestiriciler.

    gnss_filtre_v2.py — GNSSFilterV2  ⭐ KULLANIMDA OLAN
                        CT-EKF cekirdegi (durum: x, y, vx, vy, omega) ->
                        hedefin donusunu ONGORUR. Mahalanobis kapilari jammer
                        sicramalarini istatistiksel olarak reddeder; kapi ust
                        uste reddederse P sisirilip yeni rejime kilitlenilir
                        (kacis mekanizmasi). Kesintide olu-hesapla ileri
                        ekstrapolasyon (dr_max_s), cikisi lead_s kadar
                        ileri tasiyarak GNSS gecikmesini kapatir.

    gnss_filtre.py    — GNSSFilter    (ONCEKI SURUM, artik cagrilmiyor)
                        Pencere tabanli z/x/y spike kapilari + son-N noktadan
                        lineer hiz egimi + guven agirlikli lead. Karsilastirma
                        ve geri donus icin duruyor; silmeden once yenisinin
                        canlida dogrulandigindan emin olun.

Birimler her iki filtrede de SANTIMETRE (cm, cm/s) — SDK'nin verdigi birim.
cm -> m sinirini `control/gps_approach.py :: clean_target` gecer.

SOZLESME (ikisi de saglar; degistirmek isterseniz ikisini de saglayin):
    update(x, y, z) -> (x, y, z) TELAFILI temiz konum | None (isinmadi)
    guidance_state()     -> {"pos": (x,y,z), "vel": (vx,vy,vz)} | None

⭐ `vel` ZORUNLUDUR: istasyon yasasi hedefin hizini ILERI BESLER. Ileri
  besleme olmadan saf P kontrolcu hareketli hedefi asla yakalayamaz
  (denge e = V/Kp'de kurulur -> 18 m/s'de 20 m kalici hata).

⛔ Bu paketin cikisi YALNIZ GPS fazinda guduume girer. Gorsel temas
  kurulduktan sonra hedefe ait hicbir GNSS turevi komuta giremez
  (yarisma kurali; bkz. CLAUDE.md).
"""
