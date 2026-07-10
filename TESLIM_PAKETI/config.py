# -*- coding: utf-8 -*-
"""Merkezi yapilandirma: konuslandirma (host/port) + baslangic model secimi.
Algoritma parametreleri ait olduklari modulun kendi Cfg blogunda yasar."""
import os

PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Konuslandirma ---
WEB_HOST = "127.0.0.1"     # yerel arayuz adresi
WEB_PORT = 8000            # arayuz portu

# --- Baslangic model secimi (models/ altindaki .pt adi; canli hot-swap: model_yonetici) ---
VIS_MODEL_ADI = "best"             # models/<ad>.pt (yoksa ilk bulunan .pt'ye duser)
