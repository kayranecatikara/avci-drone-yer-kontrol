# -*- coding: utf-8 -*-
"""
================================================================================
 MERKEZI YAPILANDIRMA (config) — sartname teslim kalemi "config"
================================================================================
Konuslandirma (host/port) ve baslangic model secimi burada. ALGORITMA
parametreleri ise ait olduklari modulun Cfg blogunda yasar: her sabit
yonettigi kodun yaninda durur -> tek yerde koparilmis dev sabit listesi yok,
her sabit baglaminda aciklanabilir (yarisma kurali 8). Parametre haritasi:

  guidance/ana_kontrol.py :: Cfg        -> FSM (gorsel-devir) + gorsel esikleri
                                           (kilit isteri sayaci dahil, §6.1.4)
  guidance/gps_takip.py   :: GPSCfg     -> GPS-yaklasma guduumu (kalkis/PD/PID/DR)
  guidance/ibvs_gorsel.py :: AvciIBVS   -> gorsel guduum yasasi (basit IBVS; Cfg IBVS_*)
  fusion/gnss_filtre.py                 -> GNSS spike temizleme + hiz kestirimi
  detection/kamera_model.py             -> kamera ic parametreleri (K)
  detection/model_yonetici.py           -> model registry (hot-swap)

Bu dosya UCUS pipeline'inin parcasidir (teslim paketine GIRER). Import-hafif
tutulur (numpy/cv2 cekmez) ki server disi araclar da ucuz okuyabilsin.
================================================================================
"""
import os

PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Konuslandirma (deployment) ---
WEB_HOST = "127.0.0.1"     # yerel arayuz adresi (yalniz localhost dinler)
WEB_PORT = 8000            # arayuz portu; baska bir ornek calisiyorsa degistir

# --- Baslangic model secimi (registry ilk tercih; models/ altindaki .pt adi) ---
# Ayrinti: detection/model_yonetici.py canli hot-swap yapar; bu yalniz baslangic.
# 2026-07-08: aktif model models/best.pt = best_son @1280 (19 MB, detect/talon).
# yarisma-pipeline'daki "best_kayra_son.pt" bu dosyayla bayt-bayt AYNIYDI
# (blob f3f776e) -> tek kopya best.pt olarak yasar.
VIS_MODEL_ADI = "best"             # models/<ad>.pt (yoksa ilk bulunan .pt'ye duser)
