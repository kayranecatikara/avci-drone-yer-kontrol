# -*- coding: utf-8 -*-
"""
================================================================================
 MERKEZI YAPILANDIRMA (config) — sartname teslim kalemi "config"
================================================================================
Konuslandirma (host/port) ve baslangic model secimi burada. ALGORITMA
parametreleri ise ait olduklari modulun Cfg blogunda yasar: her sabit
yonettigi kodun yaninda durur -> tek yerde koparilmis dev sabit listesi yok,
her sabit baglaminda aciklanabilir (yarisma kurali 8). Parametre haritasi:

  guidance/ana_kontrol.py :: Cfg        -> guduum / yaklasma / gorsel esikleri
                                           (kilit isteri sayaci dahil, §6.1.4)
  guidance/ibvs_gorsel.py :: AvciIBVS   -> gorsel guduum yasasi (basit IBVS +
                                           pose roll acı-beslemesi; Cfg IBVS_*)
  fusion/inovasyonlu_j_v2.py            -> GNSS filtre / hiz kestirim kazanclari
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
# 2026-08-14: talon_v2 aktif edildi. Eskisi "best" = 5.4 MB (nano boyutu).
#   talon_v2 = yolo11s @960; 8998 kare (sim 5042 + elle etiketli 3455 + 2.pc 339),
#   sizintisiz blok bolme, 100 epoch.
#   val: mAP50 0.9796 | mAP50-95 0.8386 | precision 0.9782 | recall 0.9570
#   SAHI'siz TAM-KARE recall: 20-30 m %92.7 | 30-45 m %94.1  (eski model uzakta %0)
#   -> dilimlemeye gerek yok; yanindaki talon_v2.engine (TensorRT FP16) secilir.
# 2026-08-15: talon_v3 aktif edildi (v2 SILINMEDI, models/talon_v2.pt duruyor).
#   talon_v3 = talon_v2 uzerine ince ayar; 16332 kare (14023 train / 2309 val),
#   yolo11s @960, 60 epoch, lr0 0.002.
#   AYNI val setinde: v2 mAP50 0.9221 / mAP50-95 0.7697
#                     v3 mAP50 0.9419 / mAP50-95 0.8070   (+0.0373)
#   -> kutu oturmasi duzeldi. Yanindaki talon_v3.engine (TensorRT FP16) secilir.
#   Geri donmek icin bu satiri "talon_v2" yap (yedek: config.py.yedek_*).
VIS_MODEL_ADI = "talon_v5"         # models/<ad>.pt (yoksa ilk bulunan .pt'ye duser)
# 2026-08-24: v3 -> v5. Bu ayar guduemuen modelini SECMEZ (onu
#   Cfg.VIS_MODEL_PATH belirler) ama fps_olc.py bunu okuyor; v3'te kalinca
#   FPS olcumu BASKA modeli olcuyordu. Ikisi ayni kalmali.
