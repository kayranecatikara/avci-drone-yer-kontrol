# -*- coding: utf-8 -*-
"""
================================================================================
  GECERLILIK SUZGECI  --  her olcumden ONCE uygulanmali
================================================================================
⚠⚠ DONMUS TELEMETRI TUZAGI (2026-08-18, ucusta yakalandi)
--------------------------------------------------------------------------------
Oyun sureci coktugunde sunucu SON BILINEN degerleri yazmaya devam eder.
Satirlar "gecerli" gorunur: menzil 32.6, d_hiz sifir degil, faz dolu --
ama hicbiri DEGISMEZ. Olculdu:

    kampanya_iz_20260818_121445.csv : 8569 satirin **2562'si (%29.9)** donmus
    en uzun donmus seri            : 2354 satir = **235 saniye**
    mevcut `menzil>=0.5 & d_hiz>0.5` suzgecinden gecen: **8568 / 8569**

Yani suzgec bu copu OLDUGU GIBI iceri aliyordu. Bir kolun ucte biri
donmus veriyse CPA/aspect/dikey ne olcerseniz olcun ANLAMSIZDIR.

Nobetci cokmeyi yakalayip toparliyor (olculdu: 275 s) ama o sure boyunca
kampanya kaydetmeye devam ediyor. Yani kayit ile gercek arasindaki bu
bosluk KAPANMAZ; olcum tarafinda ayiklanmali.

KULLANIM
    from arac.gecerlilik import donmus_maske, temizle
    R = temizle(R)                     # donmus satirlari at
    # ya da
    m = donmus_maske(R); ...           # kendin karar ver
================================================================================
"""

# Bir satirin "kimligi": bunlarin HEPSI ayniysa telemetri ilerlememis demektir.
# ⚠ Yalniz menzile bakma: menzil dogal olarak da sabit kalabilir (yan yana
#   ucus). Konumlarin da donmus olmasi gerekir.
IMZA_ALANLARI = ("menzil", "dx", "dy", "hx", "hy")

# Kac ardisik ayni satirdan sonra "donmus" sayilsin. 2 = ikinci tekrar
# atilir. 10 Hz'de 2 satir = 0.2 s; gercek telemetride bu bile nadirdir.
ESIK = 2


def _imza(r, alanlar=IMZA_ALANLARI):
    return tuple((r.get(k) or "") for k in alanlar)


def donmus_maske(R, alanlar=IMZA_ALANLARI, esik=ESIK):
    """[bool] -- True = satir DONMUS (atilmali).

    Ilk tekrar tutulur (gecis olabilir), ardindan gelenler atilir.
    """
    out = [False] * len(R)
    onceki = None
    seri = 0
    for i, r in enumerate(R):
        im = _imza(r, alanlar)
        if onceki is not None and im == onceki:
            seri += 1
            if seri >= esik - 1:
                out[i] = True
        else:
            seri = 0
        onceki = im
    return out


def temizle(R, alanlar=IMZA_ALANLARI, esik=ESIK):
    """Donmus satirlari atilmis yeni liste."""
    m = donmus_maske(R, alanlar, esik)
    return [r for r, d in zip(R, m) if not d]


def ozet(R, alanlar=IMZA_ALANLARI, esik=ESIK):
    """(donmus_sayisi, oran, en_uzun_seri) -- rapor icin."""
    m = donmus_maske(R, alanlar, esik)
    n = sum(m)
    uzun = seri = 0
    for d in m:
        seri = seri + 1 if d else 0
        uzun = max(uzun, seri)
    return n, (n / len(R) if R else 0.0), uzun
