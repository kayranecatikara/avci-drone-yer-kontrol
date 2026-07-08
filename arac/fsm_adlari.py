# -*- coding: utf-8 -*-
"""
GELISTIRME ARACI YARDIMCISI — FSM durum ad eslemesi (TEK KAYNAK; pakete girmez).

Uretim kodu YALNIZ yeni adlari kullanir: YAKLASMA (GNSS'li kapanis),
GORSEL_TAKIP (gorsel yonelim; §6.1.2). Onceki TARIHLI ucus CSV'leri ESKI
etiketlerle kayitli: TAKIP, GORSEL_GUDUM. Araclar iki adlandirmayi da
okuyabilsin diye esleme BURADA (tek yerde); referans CSV kaydi eski adlarla kalir.
"""
ESKI_YENI = {"TAKIP": "YAKLASMA", "GORSEL_GUDUM": "GORSEL_TAKIP"}
YENI_ESKI = {v: k for k, v in ESKI_YENI.items()}
GORSEL_AILE = ("GORSEL_TAKIP", "KILIT_BILDIR", "ANGAJMAN")


def normalize(durum):
    """Eski VEYA yeni ad -> YENI ad (araclar tek dille calissin). Bilinmeyen aynen doner."""
    return ESKI_YENI.get(durum, durum)


def gorsel_mi(durum):
    """durum gorsel-takip ailesinde mi (eski/yeni ad fark etmez)?"""
    return normalize(durum) in GORSEL_AILE
