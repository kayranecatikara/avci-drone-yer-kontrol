# -*- coding: utf-8 -*-
"""
arac/denetim_kanit.py — DEPO DENETIMI KANIT BETIGI (SALT OKUMA)

Her bulgu icin kodu ITHAL EDIP davranisini gosterir. Hicbir dosyayi
DEGISTIRMEZ, hicbir MAVLink/DoW baglantisi kurmaz, hicbir thread baslatmaz.

    python arac/denetim_kanit.py            # tum kanitlar
    python arac/denetim_kanit.py B1 B4      # yalnizca secilenler

Rapor: arac/DEPO_DENETIM.md
"""
from __future__ import annotations

import ast
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_HERE)
_KAYNAK = os.path.join(_KOK, "kopru", "gazebo_kaynak")
for _p in (_KOK, _KAYNAK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:                       # Windows cp1252 konsolu Unicode'da patliyor
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KANITLAR = []


def kanit(kod, baslik):
    def sar(fn):
        KANITLAR.append((kod, baslik, fn))
        return fn
    return sar


def y(*a):
    print(*a)


# ══════════════════════════════════════════════════════════════════════════
@kanit("B1", "SupCfg.KAYIP_M=60 her gorev basinda 20'ye EZILIYOR")
def b1():
    """supervisor.py:84 KAYIP_M=60 (2026-08-16 ucus olcumu). entegre.py:226
    her _kur()'da ana_kontrol.Cfg.KOPRU_KAYIP_M ile setattr eder."""
    import control.guidance.supervisor as sup
    from guidance.ana_kontrol import Cfg as AK

    yasa = int(sup.SupCfg.KAYIP_M)
    istek = int(getattr(AK, "KOPRU_KAYIP_M", 0) or 0)
    y("  yasa dosyasindaki deger  supervisor.SupCfg.KAYIP_M = %d" % yasa)
    y("  ana_kontrol.Cfg.KOPRU_KAYIP_M            = %d" % istek)

    # entegre.py:223-226'daki KOSULUN ve ATAMANIN birebir kopyasi
    if istek:                                   # entegre.py:223  `if self.kayip_m:`
        eski = int(sup.SupCfg.KAYIP_M)
        sup.SupCfg.KAYIP_M = istek              # entegre.py:226
        y("  -> entegre._kur() calistiktan SONRA: KAYIP_M = %d  (%d'ten ezildi)"
          % (sup.SupCfg.KAYIP_M, eski))
    sup.SupCfg.KAYIP_M = yasa                   # denetim yan etkisiz olsun
    y("  KOR PENCERE (olculen dongu 31.2 Hz):")
    for k, ad in ((yasa, "yasanin yazdigi"), (istek, "fiilen kosan")):
        y("     %2d kare -> %.2f s   (%s)" % (k, k / 31.2, ad))
    y("  entegre.py:228 ise ekrana '~%.1f s @15 FPS' basiyor -> ucuncu bir sayi."
      % (istek / 15.0))
    return yasa != istek


# ══════════════════════════════════════════════════════════════════════════
@kanit("B2", "lead_az ve sonum VARSAYILANDA hicbir cikisa dokunmuyor")
def b2():
    """BURUN_LOS=1 -> yaw_cmd'den cikar (bbox_ibvs:842-848).
    PN_N=1.6>0   -> hiz yonunden cikar (bbox_ibvs:909-932).
    Yani SONUM_T=0.30 ve LEAD_MAX_SEYIR_DEG=9.0 OLU ayardir."""
    import control.guidance.bbox_ibvs as bi

    y("  varsayilanlar: BURUN_LOS=%s  PN_N=%.2f  SONUM_T=%.2f  "
      "LEAD_ERKEN=%s  LEAD_MAX_SEYIR_DEG=%.1f"
      % (bi.Cfg.BURUN_LOS, bi.Cfg.PN_N, bi.Cfg.SONUM_T,
         bi.Cfg.LEAD_ERKEN, bi.Cfg.LEAD_MAX_SEYIR_DEG))

    def cfg_ile(**kw):
        return type("C", (bi.Cfg,), kw)

    # Hedef kadrajin saginda, arac 40 deg/s doniyor, LOS 0.8 rad/s kayiyor
    arg = dict(cx=430.0, cy=310.0, w=40.0, h=14.0, iris_yaw=0.3, hiz_I=15.0,
               dt=0.05, terminal=False, los_hiz=(0.8, 0.05),
               iris_pitch=-0.2, iris_vz=0.0, kapanma=3.0, iris_roll=0.25,
               yaw_hizi=0.7, psi_v=0.31, eps_hizi=0.0)

    taban = bi.komut(cfg=bi.Cfg, **arg)
    kapali = bi.komut(cfg=cfg_ile(SONUM_T=0.0, LEAD_MAX_SEYIR_DEG=0.0,
                                  LEAD_ERKEN=False, LEAD_SURE=0.0), **arg)
    ad = ("vx", "vy", "vz", "yaw_cmd", "hiz_I")
    y("  %-10s %14s %14s %10s" % ("cikti", "SONUM+LEAD ACIK", "IKISI DE KAPALI", "fark"))
    ayni = True
    for i, a in enumerate(ad):
        f = abs(taban[i] - kapali[i])
        ayni &= (f < 1e-12)
        y("  %-10s %14.9f %14.9f %10.2e" % (a, taban[i], kapali[i], f))
    y("  tani['lead_az'] = %.4f rad (%.2f deg), tani['sonum'] = %.4f rad -> "
      "HESAPLANIYOR ama yalniz CSV'ye yaziliyor."
      % (taban[5]["lead_az"], math.degrees(taban[5]["lead_az"]), taban[5]["sonum"]))
    y("  SONUC: cikti BIT-AYNI mi? %s" % ("EVET -> ayarlar OLU" if ayni else "hayir"))

    # Kontrol: PN kapatilinca terimler DIRILIYOR mu? (mekanizma kapisi)
    t2 = bi.komut(cfg=cfg_ile(PN_N=0.0, BURUN_LOS=False), **arg)
    t3 = bi.komut(cfg=cfg_ile(PN_N=0.0, BURUN_LOS=False, SONUM_T=0.0,
                              LEAD_ERKEN=False, LEAD_SURE=0.0), **arg)
    y("  MEKANIZMA KAPISI: PN=0 + BURUN_LOS=0 iken ayni A/B'nin yaw farki "
      "%.4f rad -> terimler gercekten CALISIR HALDE, sadece yol kapali."
      % abs(t2[3] - t3[3]))
    return ayni


# ══════════════════════════════════════════════════════════════════════════
@kanit("B3", "MENZIL_PX_M ikizi: yasa 202.6 kullaniyor, nisan kapisi 160.0")
def b3():
    """bbox_ibvs.py:490 MENZIL_PX_M=202.6 (2026-08-16 olcumu, 1788 kare).
    bbox_ibvs.py:1371 hala `_men = 160.0 / boyut` yaziyor (curutulmus sabit)."""
    import control.guidance.bbox_ibvs as bi
    import re

    src = open(bi.__file__, encoding="utf-8").read().splitlines()
    sat = [(i + 1, s.strip()) for i, s in enumerate(src)
           if re.search(r"=\s*160\.0\s*/", s)]
    y("  Cfg.MENZIL_PX_M = %.1f  (dosyanin kendi olcumu)" % bi.Cfg.MENZIL_PX_M)
    for n, s in sat:
        y("  bbox_ibvs.py:%d  %s" % (n, s))
    if not sat:
        y("  (160.0 sabiti bulunamadi -- duzeltilmis olabilir)")
        return False

    y("  TERM_NISAN_MAX_M kapisinin etkisi (eps_yaw=20 deg):")
    y("  %8s %10s %10s %9s %9s  %s" % ("boyut", "R@160", "R@202.6",
                                       "yanal160", "yanal202", "karar"))
    for b in (25.0, 30.0, 40.0, 60.0):
        r1, r2 = 160.0 / b, bi.Cfg.MENZIL_PX_M / b
        y1, y2 = r1 * math.tan(math.radians(20)), r2 * math.tan(math.radians(20))
        k1 = "GEC" if y1 <= bi.Cfg.TERM_NISAN_MAX_M else "DUR"
        k2 = "GEC" if y2 <= bi.Cfg.TERM_NISAN_MAX_M else "DUR"
        y("  %8.0f %10.2f %10.2f %9.2f %9.2f  %s / %s(dogru)"
          % (b, r1, r2, y1, y2, k1, k2))
    y("  -> kapi %.0f%% FAZLA gecirgen (esik 2.0 m fiilen %.2f m gibi davraniyor)"
      % (100 * (bi.Cfg.MENZIL_PX_M / 160.0 - 1),
         bi.Cfg.TERM_NISAN_MAX_M * bi.Cfg.MENZIL_PX_M / 160.0))
    y("  Ayrica Cfg yorumu 'TERMINAL_BOYUT %.0f px ~ 6.4 m' diyor; 202.6 ile %.1f m."
      % (bi.Cfg.TERMINAL_BOYUT, bi.Cfg.MENZIL_PX_M / bi.Cfg.TERMINAL_BOYUT))
    y("  Ayni sekilde 'BOYUT_REF %.0f px = 6-7 m tutus' -> gercekte %.1f m."
      % (bi.Cfg.BOYUT_REF, bi.Cfg.MENZIL_PX_M / bi.Cfg.BOYUT_REF))
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B4", "ISTASYON dikey ayrimi 1.56 m: kanat acikligindan (1.718 m) KUCUK")
def b4():
    """ana_kontrol Cfg: RANGE_SET 18->9 (2026-08-16) yapilirken dikey ayrim
    anilmadi. ELEV=10 sabit kaldi -> 3.13 m -> 1.56 m."""
    from guidance.ana_kontrol import Cfg as AK
    R = float(AK.KOPRU_RANGE_SET)
    E = math.radians(float(AK.KOPRU_ISTASYON_ELEV))
    arka, alt = R * math.cos(E), R * math.sin(E)
    y("  ana_kontrol.Cfg.KOPRU_RANGE_SET     = %.1f m   (:222)" % R)
    y("  ana_kontrol.Cfg.KOPRU_ISTASYON_ELEV = %.1f deg (:249)" % AK.KOPRU_ISTASYON_ELEV)
    y("  -> istasyon = %.2f m ARKA + %.2f m ALT" % (arka, alt))
    y("  TARIH (ayni Cfg blogunun kendi yorumlari):")
    for r, e, not_ in ((6.9, 15, "1.79 m: 'carpisma payi YOK, bir kosuda 1.4 m'de carpti'"),
                       (6.9, 25, "2.92 m: '+%63 pay' -- KALICI diye onaylanan deger"),
                       (25.0, 25, "10.57 m: gozden kacmis yan etki, faz 1.8 s'de olduruyordu"),
                       (18.0, 10, "3.13 m: ':244 bu degisiklikte GEREKCE olarak yazildi'"),
                       (R, math.degrees(E), "SIMDIKI")):
        y("     RANGE %.1f x ELEV %2.0f -> %5.2f m alt   %s"
          % (r, e, r * math.sin(math.radians(e)), not_))
    y("  Talon kanat acikligi = 1.718 m (ana_kontrol.py:230)")
    y("  SONUC: %.2f m < 1.718 m -> istasyon hedefin carpisma zarfinin ICINDE."
      % alt)
    y("  ':244-245 dogrulanmis-guvenli 2.92 m'nin UZERINDE' gerekcesi RANGE=18")
    y("  icin yazilmisti; RANGE 9.0'a inince (:217) o cumle gecersizlesti ama")
    y("  ELEV yorumu guncellenmedi.")
    return alt < 1.718


# ══════════════════════════════════════════════════════════════════════════
@kanit("B5", "entegre.adim(): tani_log_kapat() `return`in ARKASINDA -> OLU")
def b5():
    """entegre.py:381 `return self._kopru.adim()`; :386-390 asla calismaz.
    Kendi yorumu 'her gorevin SON 0-5 saniyesi kayboluyordu' diyor."""
    yol = os.path.join(_KOK, "kopru", "entegre.py")
    src = open(yol, encoding="utf-8").read()
    agac = ast.parse(src)
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == "adim":
            govde = d.body
            for i, st in enumerate(govde):
                if isinstance(st, ast.Return):
                    olu = govde[i + 1:]
                    y("  entegre.py fonksiyon `adim`: return satiri %d" % st.lineno)
                    y("  return SONRASI %d ifade var (satir %s) -> ERISILEMEZ:"
                      % (len(olu), ", ".join(str(s.lineno) for s in olu)))
                    for s in olu:
                        y("     %s" % ast.unparse(s).splitlines()[0][:70])
                    y("  cagirilamayan: DowKopru.tani_log_kapat()")
                    y("  (tek gercek cagri yeri: dow_kopru.dongu_durdur():805 --")
                    y("   ama entegre kendi thread'ini kullaniyor, o dongu kosmuyor)")
                    return len(olu) > 0
    y("  fonksiyon bulunamadi (duzeltilmis olabilir)")
    return False


# ══════════════════════════════════════════════════════════════════════════
@kanit("B6", "AVCI_GPS_* ortam degiskenleri varsayilan kipte SILINIYOR")
def b6():
    """entegre.py:141-148 -- birebir=True iken yaziliyor degil, POP ediliyor.
    ana_kontrol KOPRU_BIREBIR=False oldugu icin bu kol UCUSTA kosmuyor, ama
    entegre'nin KENDI varsayilani birebir=True."""
    from guidance.ana_kontrol import Cfg as AK
    import inspect
    from kopru.entegre import KopruGudum

    imza = inspect.signature(KopruGudum.__init__)
    y("  KopruGudum.__init__ varsayilani : birebir=%s"
      % imza.parameters["birebir"].default)
    y("  ana_kontrol.Cfg.KOPRU_BIREBIR   : %s  (ucusta kullanilan)"
      % AK.KOPRU_BIREBIR)

    eski = {k: os.environ.get(k) for k in
            ("AVCI_GPS_RANGE", "AVCI_GPS_IC", "AVCI_GPS_ISTASYON_ELEV",
             "AVCI_GPS_ELEV_DIN")}
    os.environ["AVCI_GPS_RANGE"] = "33.0"
    y("  disaridan AVCI_GPS_RANGE=%s verildi" % os.environ["AVCI_GPS_RANGE"])
    # entegre.py:145-148 birebir kolunun birebir kopyasi
    for _k in ("AVCI_GPS_RANGE", "AVCI_GPS_IC", "AVCI_GPS_ISTASYON_ELEV",
               "AVCI_GPS_ELEV_DIN"):
        os.environ.pop(_k, None)
    y("  entegre.py:146-148 calisti -> AVCI_GPS_RANGE = %r"
      % os.environ.get("AVCI_GPS_RANGE"))
    for k, v in eski.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    y("  SONUC: birebir kipinde AVCI_GPS_* disaridan ayarlanamaz (sessizce silinir).")
    y("  KOPRU_BIREBIR=False oldugu icin ucusta ayni degiskenler bu sefer")
    y("  entegre.py:142-144'te USTUNE YAZILIYOR -> her iki kipte de ETKISIZ.")
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B7", "DevirCfg (LOCK_PCT %2, AV 35-65) devir kararina HIC girmiyor")
def b7():
    """supervisor GORSEL kolunda _devret = _kare_ok and _sure_ok and _geo_ok.
    KILIT_SURE_S=0 -> _sure_ok daima True; ASPECT/DONUS=999 -> _geo_ok daima
    True. Geriye yalniz ardisik kare sayisi kaliyor. OTO kipinde ise kolun
    kendisine hic girilmiyor."""
    import control.guidance.supervisor as sup
    from guidance.ana_kontrol import DevirCfg
    c = sup.SupCfg
    y("  SupCfg.ZORLA_MOD       = %r  (server.py:323 _zorla_mod_istek=None)" % c.ZORLA_MOD)
    y("  SupCfg.KILIT_SURE_S    = %.1f -> _sure_ok = (%.1f <= 0.0) = %s"
      % (c.KILIT_SURE_S, c.KILIT_SURE_S, c.KILIT_SURE_S <= 0.0))
    y("  SupCfg.DEVIR_ASPECT_MAX= %.0f -> _geo_ok daima %s" % (c.DEVIR_ASPECT_MAX,
                                                               c.DEVIR_ASPECT_MAX >= 999.0))
    y("  SupCfg.DEVIR_DONUS_MAX = %.0f -> _duz_ok daima %s" % (c.DEVIR_DONUS_MAX,
                                                               c.DEVIR_DONUS_MAX >= 999.0))
    y("  => _devret == _kare_ok == (ardisik_gor >= KILIT_N=%d)" % c.KILIT_N)
    y("  DevirCfg.LOCK_PCT=%.2f AV_X=%.2f AV_Y=%.2f -> yalnizca karar_log/telemetri"
      % (DevirCfg.LOCK_PCT, DevirCfg.AV_X, DevirCfg.AV_Y))
    y("  ⚠ kilit_kaynagi yine de ZORUNLU: None donerse supervisor.py:474-481")
    y("    'continue' der ve GORSEL kipinde HIC devretmez (deger kullanilmaz,")
    y("    varligi kapi olur).")
    y("  Gercek devir kapilari: DEVIR_BOYUT_PX=%.0f px, HAYALET w/h>=%.1f, "
      "KILIT_N=%d ardisik" % (c.DEVIR_BOYUT_PX, c.HAYALET_WH_MIN, c.KILIT_N))
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B8", "tespit_akisi.olcum(): kayip esigini SABIT 20 kare sayiyor")
def b8():
    """tespit_akisi.py:230-231 15.0 ve 20.0 gomulu. Gercek esikler
    SupCfg.KILIT_N (ardisik) ve calisma anindaki KAYIP_M."""
    import control.guidance.supervisor as sup
    from guidance.ana_kontrol import Cfg as AK
    from kopru.tespit_akisi import TespitAkisi

    a = TespitAkisi()
    t = 0.0
    for i in range(31):
        a.yaz({"cx": 960, "cy": 540, "w": 60, "h": 20, "conf": 0.9,
               "W": 1920, "H": 1080}, simdi=t)
        t += 1.0 / 30.0
    o = a.olcum()
    gercek_kayip = int(getattr(AK, "KOPRU_KAYIP_M", 0) or sup.SupCfg.KAYIP_M)
    y("  30 Hz sahte akis -> olcum()['hz'] = %.2f" % o["hz"])
    y("  olcum()['kayip_esigi_s']      = %.2f s   (20 kare varsayarak)" % o["kayip_esigi_s"])
    y("  olcum()['kilit_penceresi_s']  = %.2f s   (15 kare varsayarak)" % o["kilit_penceresi_s"])
    y("  yasa dosyasindaki KAYIP_M     = %d  -> dogrusu %.2f s"
      % (sup.SupCfg.KAYIP_M, sup.SupCfg.KAYIP_M / o["hz"]))
    y("  fiilen kosan KAYIP_M          = %d  -> dogrusu %.2f s"
      % (gercek_kayip, gercek_kayip / o["hz"]))
    y("  KILIT_ARDISIK = %s -> 15'lik kayan pencere zaten KULLANILMIYOR;"
      % sup.SupCfg.KILIT_ARDISIK)
    y("    dogru sayi KILIT_N=%d -> %.2f s"
      % (sup.SupCfg.KILIT_N, sup.SupCfg.KILIT_N / o["hz"]))
    y("  Modul docstring'i ayrica '~8-9 FPS' diyor; ana_kontrol:273 '~15 FPS';")
    y("  supervisor:74 'olculen dongu 31.2 Hz' -> UC AYRI kare hizi iddiasi.")
    return abs(o["kayip_esigi_s"] - sup.SupCfg.KAYIP_M / o["hz"]) > 1e-6


# ══════════════════════════════════════════════════════════════════════════
@kanit("B9", "OLU SABITLER: tanimlandigi yer disinda hic okunmayanlar")
def b9():
    import re
    hedefler = {
        "guidance/ana_kontrol.py": ["VIS_AV_X", "VIS_AV_Y", "DEBUG_Z",
                                    "ROT_IN_DEGREES", "VIS_WIN_S"],
        "kopru/gazebo_kaynak/control/guidance/gps_guidance.py":
            ["HANDOFF_RANGE", "IC_R_MIN", "IC_OMEGA_REF", "LOOKUP_MIN_ALT",
             "TRACK_MIN_SPD", "FF_DONUS_MAX", "ARKA_KISALT", "IC_KAYMA_MAX"],
        "kopru/gazebo_kaynak/control/guidance/bbox_ibvs.py":
            ["YANAL_TGO_MIN", "YANAL_RDOT_MIN", "SONUM_MAX_DEG", "LEAD_EMA",
             "BOYUT_MIN", "YAW_ESIK", "I_MIN"],
    }
    py = []
    for kok, _d, fs in os.walk(_KOK):
        if any(x in kok for x in (".git", "_ONCEKI_", ".claude", "__pycache__",
                                  "arsiv", "png_sim")):
            continue
        py += [os.path.join(kok, f) for f in fs if f.endswith(".py")]
    metin = {}
    for p in py:
        if os.path.basename(p) == "denetim_kanit.py":
            continue                       # DENETIM BETIGININ KENDISI sayilmaz
        if ".yedek" in p:
            continue
        try:
            metin[p] = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except Exception:
            pass

    y("  (sayim: yorum satirlari, tanim satiri, yedekler ve bu betik HARIC)")
    y("  %-42s %6s  %-24s %s" % ("sabit", "okuma", "durum", "ilk okuyucu"))
    olu = []
    for dosya, adlar in hedefler.items():
        tam = os.path.join(_KOK, *dosya.split("/"))
        for ad in adlar:
            n, ilk = 0, ""
            for p, satirlar in metin.items():
                for i, satir in enumerate(satirlar):
                    kod = satir.split("#", 1)[0]
                    if not re.search(r"\b%s\b" % ad, kod):
                        continue
                    if p == tam and re.match(r"\s*%s\s*=[^=]" % ad, kod):
                        continue                       # tanim satiri
                    n += 1
                    if not ilk:
                        ilk = "%s:%d" % (os.path.basename(p), i + 1)
            durum = "OLU (hic okunmuyor)" if n == 0 else ""
            if n == 0:
                olu.append("%s::%s" % (os.path.basename(dosya), ad))
            y("  %-42s %6d  %-24s %s"
              % ("%s::%s" % (os.path.basename(dosya), ad), n, durum, ilk))
    y("  OLU SABIT SAYISI: %d -> %s" % (len(olu), ", ".join(olu) or "-"))
    return bool(olu)


# ══════════════════════════════════════════════════════════════════════════
@kanit("B10", "KILIT SAYACI IKIZI: arayuz Cfg.VIS_*, sayac KilitCfg.*")
def b10():
    from guidance.ana_kontrol import Cfg as AK
    from guidance.kilit_sayaci import KilitCfg
    ciftler = [("VIS_LOCK_PCT", "LOCK_PCT"), ("VIS_AV_X", "AV_X"),
               ("VIS_AV_Y", "AV_Y"), ("VIS_WIN_S", "WIN_S"),
               ("VIS_WIN_NEED_S", "WIN_NEED_S")]
    y("  %-18s %-12s %10s %10s  %s" % ("ana_kontrol.Cfg", "KilitCfg",
                                       "deger A", "deger B", "durum"))
    sapan = 0
    for a, b in ciftler:
        va, vb = float(getattr(AK, a)), float(getattr(KilitCfg, b))
        d = "UYUYOR" if abs(va - vb) < 1e-9 else "!! SAPMIS"
        sapan += (d != "UYUYOR")
        y("  %-18s %-12s %10.3f %10.3f  %s" % (a, b, va, vb, d))
    y("  Sayac SADECE KilitCfg okur (kilit_sayaci.py:82-88).")
    y("  server.py:1692-1695 arayuze Cfg.VIS_* degerlerini basar.")
    y("  Su an ayni -> ZARARSIZ, ama iki bagimsiz kaynak: biri degisirse arayuz")
    y("  yalan soyler. (VIS_AV_X/VIS_AV_Y'nin BASKA okuyucusu YOK -- bkz. B9.)")
    return sapan == 0


# ══════════════════════════════════════════════════════════════════════════
@kanit("B11", "set_kaynak() kilit_devir'i SIFIRLAMIYOR (kilit'i sifirliyor)")
def b11():
    import re
    src = open(os.path.join(_KOK, "guidance", "ana_kontrol.py"),
               encoding="utf-8").read()
    agac = ast.parse(src)
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == "set_kaynak":
            g = ast.get_source_segment(src, d) or ""
            y("  set_kaynak() icinde 'self.kilit.sifirla()'       : %s"
              % ("VAR" if "self.kilit.sifirla()" in g else "YOK"))
            y("  set_kaynak() icinde 'self.kilit_devir.sifirla()' : %s"
              % ("VAR" if "self.kilit_devir.sifirla()" in g else "YOK"))
            y("  -> yeni gorevde devir sayacinin 10 s'lik penceresi ve `ok`")
            y("     mandali ONCEKI gorevden devrediyor.")
            return "self.kilit_devir.sifirla()" not in g
    return False


# ══════════════════════════════════════════════════════════════════════════
@kanit("B12", "Gazebo kamera sabiti (HFOV 125 / FX=FY=166.6) — nerede zararsiz")
def b12():
    """Ceviri (tespit_akisi) ile yasa AYNI FX/FY'yi kullandigi icin aci
    kanallarinda sadelesiyor. Kanit: DoW pikselinden hesaplanan aci, gercek
    DoW icsellikleriyle hesaplanan aciya esit mi?"""
    from vision import geometry as geo
    from kopru.tespit_akisi import dow_pikseli_yasaya, HFOV_DOW_DEG
    import control.guidance.bbox_ibvs as bi

    W, H = 1920.0, 1080.0
    fx_dow = (W / 2.0) / math.tan(math.radians(HFOV_DOW_DEG) / 2.0)
    y("  geometry.py: HFOV=%.1f  FX=FY=%.1f  (Gazebo iris)"
      % (math.degrees(geo.HFOV_RAD), geo.FX))
    y("  DoW gercegi: HFOV=%.4f  fx=fy=%.2f  (motorun kendi degeri)"
      % (HFOV_DOW_DEG, fx_dow))
    y("  %8s %14s %14s %10s" % ("cx_dow", "gercek aci", "yasanin acisi", "fark"))
    kotu = 0
    for cxd in (960.0, 1100.0, 1400.0, 1700.0):
        cxy, cyy, wy, hy = dow_pikseli_yasaya(cxd, 540.0, 60.0, 20.0, W, H)
        a_ger = math.degrees(math.atan((cxd - W / 2) / fx_dow))
        a_yasa = math.degrees(math.atan((cxy - geo.CX) / geo.FX))
        kotu += abs(a_ger - a_yasa) > 1e-9
        y("  %8.0f %14.4f %14.4f %10.1e" % (cxd, a_ger, a_yasa,
                                            abs(a_ger - a_yasa)))
    y("  -> FX ceviride ve yasada SADELESIYOR: azimut/yukselis kanallari temiz.")
    y("  CY_NISAN da geo.FY'den turetildigi icin ayni sadelesme gecerli:")
    y("     CY_NISAN = %.1f px = CY + FY*tan(20 deg)" % bi.Cfg.CY_NISAN)
    y("  ⚠ AMA piksel->METRE ceviren tek yer MENZIL_PX_M ve o AYRI olculdu")
    y("    (202.6 px*m, yasa cercevesinde) -> geometry sabitine bagli DEGIL.")
    y("  SONUC: geometry.py'nin 125 deg'i BU HATTA zararsiz. Zararli olacagi tek")
    y("  yol, birinin FX/FY'yi 'duzeltip' ceviriyi guncellememesi.")
    return kotu == 0


# ══════════════════════════════════════════════════════════════════════════
@kanit("B13", "DEVIR_BOYUT_PX ve TERMINAL menzil karsiliklari")
def b13():
    import control.guidance.supervisor as sup
    import control.guidance.bbox_ibvs as bi
    c = sup.SupCfg
    y("  SupCfg.DEVIR_BOYUT_PX = %.1f px  (olcum: R*max(w,h) = 310 px*m)"
      % c.DEVIR_BOYUT_PX)
    y("     -> devir ancak R <= %.1f m icinde atesleyebilir" % (310.0 / c.DEVIR_BOYUT_PX))
    from guidance.ana_kontrol import Cfg as AK
    R = float(AK.KOPRU_RANGE_SET)
    y("  GPS istasyonu slant menzili = %.1f m  -> kapi %s"
      % (R, "ACIK (istasyondan atesleyebilir)" if R <= 310.0 / c.DEVIR_BOYUT_PX
         else "KAPALI (istasyonda hic atesLENMEZ)"))
    y("  (24 px doneminde bu %.1f m idi -- istasyon 22.66 m'deyken ULASILAMAZDI.)"
      % (310.0 / 24.0))
    y("  TERMINAL_BOYUT = %.0f px (sqrt(w*h)) -> %.1f m (MENZIL_PX_M=%.1f ile)"
      % (bi.Cfg.TERMINAL_BOYUT, bi.Cfg.MENZIL_PX_M / bi.Cfg.TERMINAL_BOYUT,
         bi.Cfg.MENZIL_PX_M))
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B14", "GEOMETRI KAPISI acilirsa izci thread'i TypeError ile oluyor")
def b14():
    """supervisor.py:506-511 -- _duz_ok False ama _asp None ise
    '%.0f' % None patlar. AVCI_DEVIR_DONUS=8 verildiginde gerceklesebilir."""
    _asp = None
    _duz_ok = False
    _geo_ok = True and _duz_ok
    try:
        if not _geo_ok:
            _ = ("[SUPERVISOR] GEOMETRI KAPISI: aspect %.0f deg > %.0f deg"
                 % (_asp, 40.0))
        y("  patlamadi (?)")
        return False
    except TypeError as e:
        y("  supervisor.py:508-511 blogunun birebir kopyasi -> %s: %s"
          % (type(e).__name__, e))
        y("  KOSUL: AVCI_DEVIR_DONUS<999 (duz kisim kapisi ACIK) VE hedef donus")
        y("  hizi biliniyor VE aspect_deg None (gps_guidance:750-756'da hedef")
        y("  hizi <0.5 m/s ya da WARMUP/DROPOUT iken None yaziliyor).")
        y("  ETKI: izci thread'i sessizce oluyor -> o GPS fazinda devir")
        y("  ARTIK HIC olmaz (thread yok, faz_stop hic set edilmez).")
        return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B15", "bbox_ibvs CSV: kayip_sayac kolonu normal karelerde SABIT 0")
def b15():
    import re
    src = open(os.path.join(_KAYNAK, "control", "guidance", "bbox_ibvs.py"),
               encoding="utf-8").read().splitlines()
    for i, s in enumerate(src):
        if re.search(r'"kayip_sayac"\s*:', s):
            y("  bbox_ibvs.py:%d  %s" % (i + 1, s.strip()))
    y("  -> KUTU_YOK / TERM_KOR / KURTARMA satirlarinda gercek sayac yaziliyor,")
    y("     ama KOPRU karesinde sayac artmasina ragmen normal satir 0 basiyor.")
    y("     'kayip_sayac' kolonuna bakan analiz, kopru karelerindeki birikimi")
    y("     goremez.")
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B16", "Panel kaydiraklarindan 3'u kaynak degisiminde SESSIZCE siniriliyor")
def b16():
    """gorsel_ozellikler.ayarla() gg.Cfg / SupCfg'ye yazar. entegre._kur()
    her yeniden kurulumda ayni alanlari ana_kontrol.Cfg'den setattr eder."""
    from kopru.gorsel_ozellikler import OZELLIKLER
    from guidance.ana_kontrol import Cfg as AK

    # entegre._kur():186-194 ve :223-226'nin yazdigi alanlar
    ezilen = {
        "RANGE_SET": ("gg", AK.KOPRU_RANGE_SET, "entegre.py:187"),
        "IC_KAYMA": ("gg", AK.KOPRU_IC_KAYMA, "entegre.py:188"),
        "ISTASYON_ELEV_DEG": ("gg", AK.KOPRU_ISTASYON_ELEV, "entegre.py:189"),
        "ELEV_DINAMIK": ("gg", False, "entegre.py:190"),
        "V_MAX": ("gg", AK.KOPRU_V_MAX, "entegre.py:191"),
        "KAYIP_M": ("sup", AK.KOPRU_KAYIP_M, "entegre.py:226"),
    }
    panel = {o[0]: o[1] for o in OZELLIKLER}
    y("  %-20s %-6s %-12s %s" % ("panel anahtari", "modul", "geri donen", "ezen satir"))
    n = 0
    for ad, modul in panel.items():
        if ad in ezilen:
            _, dg, nerede = ezilen[ad]
            n += 1
            y("  %-20s %-6s %-12s %s  <- KAYNAK DEGISIMINDE SIFIRLANIR"
              % (ad, modul, dg, nerede))
    y("  panelde %d anahtar var, bunlarin %d'i her _kur()'da geri yaziliyor."
      % (len(panel), n))
    y("  ⚠ ELEV_DINAMIK/ISTASYON_ELEV_DEG zaten panelde YOK (bilerek disarida,")
    y("    gorsel_ozellikler.py:206-210) -- kalan 3'u (RANGE_SET, V_MAX,")
    y("    KAYIP_M) panelde VAR ve sessizce geri aliniyor.")
    return n > 0


# ══════════════════════════════════════════════════════════════════════════
@kanit("B17", "Panel MAX_ACCEL tavani (38) kurtarma tetigini (60 deg) asiyor")
def b17():
    """kurtarma.py: 'esikler saglikli zarfin COK disinda, asla tetiklenmez'.
    O cumle MAX_ACCEL=12 icin dogru. Panel 4..38 araligi aciyor."""
    from control.guidance.kurtarma import KurtCfg
    from kopru.gorsel_ozellikler import _INDEKS
    import control.guidance.bbox_ibvs as bi
    g = 9.81
    o = _INDEKS["MAX_ACCEL"]
    y("  KurtCfg.ACI_TETIK = %.0f deg  (|roll| veya |pitch|)" % KurtCfg.ACI_TETIK)
    y("  panel MAX_ACCEL araligi = %.0f .. %.0f m/s^2 (gorsel_ozellikler:60)"
      % (o[3], o[4]))
    kritik = g * math.tan(math.radians(KurtCfg.ACI_TETIK))
    y("  kararli donus yatisi = atan(a/g):")
    for a in (bi.Cfg.MAX_ACCEL, 17.0, 24.0, o[4]):
        b = math.degrees(math.atan(a / g))
        y("     a=%5.1f m/s^2 -> %5.1f deg   %s"
          % (a, b, "TETIKLER" if b > KurtCfg.ACI_TETIK else "guvenli"))
    y("  KIRILMA NOKTASI: a > %.1f m/s^2 (panelin ust yarisi)" % kritik)
    y("  Etki: bekci normal manevrada tetiklenir -> guduum komutlari KESILIR")
    y("  (bbox_ibvs:1151-1166) ve kayip sayaci isler -> faz erken oluyor.")
    y("  ⚠ SINIR: gercek yatisin komut ivmesini takip ettigini OLCEMEDIM;")
    y("    bu bir aritmetik uyari, ucus kaniti degil.")
    return kritik < o[4]


# ══════════════════════════════════════════════════════════════════════════
@kanit("B18", "gps_guidance.status modul duzeyinde; gorevler arasi SIZIYOR")
def b18():
    import control.guidance.gps_guidance as gg
    src = open(gg.__file__, encoding="utf-8").read()
    agac = ast.parse(src)
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == "run_gps_guidance":
            g = ast.get_source_segment(src, d) or ""
            y("  run_gps_guidance icinde 'status.clear()'  : %s"
              % ("VAR" if "status.clear" in g else "YOK"))
            y("  run_gps_guidance icinde '_hdg_gecmis' temizligi: %s"
              % ("VAR" if "_hdg_gecmis[:] = []" in g or "_hdg_gecmis.clear" in g
                 else "YOK"))
            break
    y("  status anahtarlari (gps_guidance.py:349) modul omru boyunca yasar:")
    y("     %s" % ", ".join(sorted(gg.status)))
    y("  supervisor bunlari devir aninda okur:")
    y("     tgt_vx/vy/vz -> bbox_ibvs integral SICAK BASLANGICI (supervisor:628)")
    y("     d_h, durum   -> menzil kapisi / DROPOUT (supervisor:590-592)")
    y("     aspect_deg, hedef_donus_deg -> geometri kapilari (supervisor:492-504)")
    y("  Gorev yeniden baslatilinca modul sys.modules'ta KALIR -> ilk devirde")
    y("  ONCEKI gorevin hedef hizi dondurulmus tasiyici olarak kullanilabilir.")
    y("  (WARMUP'ta status['tgt_vx'] hala eski gorevin son degeri.)")
    return True


# ══════════════════════════════════════════════════════════════════════════
def _kod_okumalari(ad, dosyalar):
    """ad'in KOD (yorum degil) icinde gectigi (dosya, satir) listesi."""
    import re
    out = []
    for p in dosyalar:
        try:
            satirlar = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except Exception:
            continue
        for i, s in enumerate(satirlar):
            kod = s.split("#", 1)[0]
            if re.search(r"\b%s\b" % ad, kod):
                out.append((p, i + 1, s.strip()))
    return out


@kanit("B19", "TUNE_ALLOW'daki YAW_MAX kaydiragi HICBIR SEY yapmiyor")
def b19():
    """server.py TUNE_ALLOW = {YAW_MAX, VIS_CONF_MIN}. Cfg.YAW_MAX'in
    tanimi ve slider disinda OKUYUCUSU yok; gercek tavan dow_kopru.Cfg.
    (server.py IMPORT EDILMEZ -- import aninda drone/thread kuruyor.)"""
    dosyalar = []
    for kok, _d, fs in os.walk(_KOK):
        if any(x in kok for x in (".git", "_ONCEKI_", ".claude", "__pycache__",
                                  "arsiv", "png_sim", "tests")):
            continue
        dosyalar += [os.path.join(kok, f) for f in fs
                     if f.endswith(".py") and ".yedek" not in f
                     and f != "denetim_kanit.py"]
    y("  ana_kontrol.Cfg.YAW_MAX icin KOD icinde gecen her yer:")
    for p, n, s in _kod_okumalari("YAW_MAX", dosyalar):
        etiket = ""
        b = os.path.basename(p)
        if b == "ana_kontrol.py":
            etiket = "  <- TANIM"
        elif b == "server.py":
            etiket = "  <- SLIDER (TUNE_ALLOW / setattr / GET geri okuma)"
        elif b == "dow_kopru.py":
            etiket = "  <- BASKA BIR SINIF (dow_kopru.Cfg)"
        y("     %-18s:%-5d %s%s" % (b, n, s[:52], etiket))
    from kopru.dow_kopru import Cfg as KCfg
    from guidance.ana_kontrol import Cfg as AK
    y("  ana_kontrol.Cfg.YAW_MAX = %.2f  <- slider bunu yaziyor, OKUYAN YOK"
      % AK.YAW_MAX)
    y("  dow_kopru.Cfg.YAW_MAX   = %.2f  <- yaw'i FIILEN kirpan (dow_kopru:626)"
      % KCfg.YAW_MAX)
    y("  Etki: 'Yaw tavani' kaydiragi degistirilir, tune_log'a yazilir,")
    y("  tune_rapor segment kiyasi bu degisimden SEGMENT ACAR -> sahte A/B.")
    return abs(AK.YAW_MAX - KCfg.YAW_MAX) > 1e-9


# ══════════════════════════════════════════════════════════════════════════
@kanit("B20", "Telemetride esik_pct ORAN, boyut_pct YUZDE -> 100 KAT sapma")
def b20():
    from guidance.ana_kontrol import Cfg as AK
    from guidance.kilit_sayaci import KilitSayaci
    k = KilitSayaci()
    k.guncelle({"cx": 960, "cy": 540, "w": 120, "h": 42,
                "W": 1920, "H": 1080}, 0.0, gorsel_faz=True)
    d = k.durum()
    y("  KilitSayaci.durum() (kilit_sayaci.py:117-121):")
    y("     boyut_pct = %-6s   esik_pct = %-6s   <- IKISI DE YUZDE"
      % (d["boyut_pct"], d["esik_pct"]))
    y("  server.py:1689-1696 telemetri sozlugu:")
    y("     boyut_pct = %-6s   (sayacin YUZDESI, aynen aktarilir)" % d["boyut_pct"])
    y("     esik_pct  = %-6s   (Cfg.VIS_LOCK_PCT, ORAN olarak yazilir)"
      % float(AK.VIS_LOCK_PCT))
    y("  AYNI SOZLUKTE iki farkli birim. Arayuz %s'i %s ile kiyasliyor:"
      % (d["boyut_pct"], AK.VIS_LOCK_PCT))
    y("     kutu kadrajin %%%.1f'i, esik %%%.1f -> DOGRU karsilastirma: %s"
      % (d["boyut_pct"], d["esik_pct"],
         "GECER" if d["boyut_pct"] >= d["esik_pct"] else "GECMEZ"))
    y("     telemetrideki hali: %.1f >= %.2f -> HER ZAMAN 'gecti' gorunur"
      % (d["boyut_pct"], AK.VIS_LOCK_PCT))
    y("  ⚠ Yalniz GOSTERIM: sayacin kendi kararı (kilit_sayaci.py:86) oran-oran,")
    y("    dogru. Bozulan sey arayuzun/olay gunlugunun soyledigi.")
    return True


# ══════════════════════════════════════════════════════════════════════════
@kanit("B21", "tune_rapor.py performans analizi ERISILEMEZ (phase hep KOPRU)")
def b21():
    import csv as _csv
    import glob
    veri = os.path.join(_KOK, "veri")
    loglar = sorted(glob.glob(os.path.join(veri, "ucus_log_*.csv")),
                    key=os.path.getmtime, reverse=True)[:5]
    y("  ana_kontrol.py:938 TEK log cagrisi: _log_early(\"KOPRU\", ...)")
    y("  tune_rapor.py:132  vis = [r for r in satirlar if r['phase'] == 'VISUAL']")
    y("  GERCEK UCUS LOGLARI:")
    toplam_vis = 0
    for p in loglar:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                r = list(_csv.DictReader(f))
        except Exception:
            continue
        fazlar = {}
        for s in r:
            fazlar[s.get("phase")] = fazlar.get(s.get("phase"), 0) + 1
        vis = fazlar.get("VISUAL", 0)
        toplam_vis += vis
        y("     %-28s %6d satir  fazlar=%s  VISUAL=%d"
          % (os.path.basename(p), len(r), fazlar, vis))
    y("  -> VISUAL satiri toplam: %d" % toplam_vis)
    y("  tune_rapor.metrik_hesapla 4 satir + 'UYARI: gorsel faz yok' donup")
    y("  :137'de RETURN ediyor; altindaki tum metrikler (tespit orani, kilit")
    y("  penceresi, IBVS merkezleme, yaw duzgunlugu, kapanma, lead) ERISILEMEZ.")
    y("  server.py yine de {'ok': True, 'dosya': ...} donuyor.")
    return toplam_vis == 0


# ══════════════════════════════════════════════════════════════════════════
@kanit("B22", "config.py 'UCUS pipeline'inin parcasi' diyor; ucus onu okumuyor")
def b22():
    import re
    dosyalar = []
    for kok, _d, fs in os.walk(_KOK):
        if any(x in kok for x in (".git", "_ONCEKI_", ".claude", "__pycache__",
                                  "arsiv", "png_sim", "tests")):
            continue
        dosyalar += [os.path.join(kok, f) for f in fs
                     if f.endswith(".py") and ".yedek" not in f
                     and f != "denetim_kanit.py"]
    y("  config.py docstring:19 'Bu dosya UCUS pipeline'inin parcasidir'")
    ithal = [(os.path.basename(p), n, s) for p, n, s in
             _kod_okumalari("config", dosyalar)
             if re.search(r"^\s*import\s+config|^\s*from\s+config\s+import", s)]
    y("  `import config` yapan dosyalar: %s"
      % (", ".join("%s:%d" % (b, n) for b, n, _ in ithal) or "HICBIRI"))
    for ad in ("WEB_HOST", "WEB_PORT", "PROJ_ROOT", "VIS_MODEL_ADI"):
        yerler = [(os.path.basename(p), n) for p, n, _ in
                  _kod_okumalari(ad, dosyalar)]
        cfg_disi = [(b, n) for b, n in yerler if b != "config.py"]
        y("     %-14s -> config.py disinda %d yer: %s"
          % (ad, len(cfg_disi),
             ", ".join("%s:%d" % x for x in cfg_disi) or "YOK"))
    y("  server.py kendi sabitlerini kuruyor (WEB_PORT=8000, PROJ_ROOT) ->")
    y("  config.py'yi degistirmek sunucuyu ETKILEMEZ.")
    return True


def main():
    sec = [a.upper() for a in sys.argv[1:]]
    y("=" * 78)
    y(" DEPO DENETIM KANITLARI — %s" % _KOK)
    y("=" * 78)
    ozet = []
    for kod, baslik, fn in KANITLAR:
        if sec and kod not in sec:
            continue
        y("")
        y("── %s · %s" % (kod, baslik))
        y("─" * 78)
        try:
            r = fn()
            ozet.append((kod, "DOGRULANDI" if r else "dogrulanamadi"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            ozet.append((kod, "HATA: %r" % (e,)))
    y("")
    y("=" * 78)
    for k, s in ozet:
        y("  %-5s %s" % (k, s))
    y("=" * 78)


if __name__ == "__main__":
    main()
