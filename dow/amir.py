# -*- coding: utf-8 -*-
"""
================================================================================
AMIR - yeni gudum YASALARINI canli sisteme baglayan DONGULER
================================================================================
`dow/gps.py` ve `dow/ibvs.py` SAF YASALARDIR: durumu alir, hiz komutu doner.
Ne araca komut gonderirler ne de bir dongu isletirler. Bu dosya o eksik
katmandir -- eski `run_gps_guidance` / `run_bbox_ibvs` ile AYNI sozlesmeyi
sunar ki supervisor'da tek satir disinda hicbir sey degismesin.

  gps_fazi(conn, get_plane, get_iris, stop_event)         <- run_gps_guidance
  gorsel_fazi(conn, get_iris, wait_pose, stop_event, ...) <- run_bbox_ibvs

UC CERCEVE DONUSUMU - hepsi burada, yasalarin ICINDE DEGIL
 (1) DIKEY EKSEN. Canli sistem NED verir (z ASAGI pozitif). `dow/gps.py` ise
     Z-YUKARI cerceve varsayar: istasyonu `z = hedef_z - alt` ile kurar, yani
     "alt" demek icin z'yi KUCULTUR. NED'de bu YUKARI demektir -> istasyon
     hedefin USTUNDE kurulur, kamera (25 der YUKARI bakiyor) hedefi kaybeder.
     Bu yuzden konumlar yasaya -z ile verilir; donen vz zaten NED'dir.
 (2) PIKSEL OLCEGI. Canli tespit akisi (kopru/tespit_akisi.py:189) pikselleri
     YASA cercevesine cevirir: 640x480, FX=166.58, CX=320, CY=240.
     `dow/ibvs.py` ise HAM DoW cercevesini varsayar: 1920x1080, CX=960, CY=540
     (CY_REF_UZAK=470 / CY_REF_YAKIN=540 bu cercevenin sayilaridir).
     Olcek verilmezse e_cy = cy - cy_ref surekli ~-290 px cikar ve dikey kanal
     bitmeyen TIRMAN komutu uretir. Donusum: _yasa_pikselden_ham().
 (3) AYNA - DOKUNULMAZ. kopru/dow_kopru.py dunyayi yatay aynalar
     (NED_y = -DoW_y, yaw_NED = -yaw_DoW) ve tespit akisi pikseli de aynalar.
     Gelen piksel ile iris yaw'i AYNI (aynali) cercevede oldugu icin
     `yaw_hedef = yaw + K_YAW*azimut` DOGRUDUR. Ayna YATAYDIR, cy'yi etkilemez.
     Olcek cevirisi merkez etrafinda yapildigi icin aynayi BOZMAZ.
     Bu depoda ayna hatasi UC KEZ tekrarladi; buraya dokunmadan once
     memory/gorsel-yasa-ayna-hatasi.md okunmali.

YAW BIRIMI: send_velocity(conn, vx, vy, vz, yaw) -> yaw MUTLAK NED, RADYAN
  (gps_guidance.py:932 `send_velocity(conn,0,0,0, iyaw)` ile ayni birim).
  gps.komut() yaw HIZI dondurur -> mutlaga cevrilir (kerteriz = yaw + yaw_hata).
  ibvs.komut() zaten MUTLAK derece dondurur -> yalniz radyana cevrilir.
================================================================================
"""
import math
import os
import time

from dow.ayarlar import Ayar
from dow import gps as YGPS
from dow import ibvs as YIBVS
from dow.gorus import kamera as KAM

# entegre.py bunu dow_kopru.send_velocity'ye baglar (eski yasalarla ayni yol).
send_velocity = None

DONGU_HZ = float(os.environ.get("DOW_DONGU_HZ", Ayar.LOOP_HZ))

# ── OLCEK CEVIRISI: canli akis -> kamera.py'nin bekledigi HAM DoW pikseli ──
# Canli akis kopru/tespit_akisi.dow_pikseli_yasaya ile ceviriliyor; o fonksiyon
# ACIYI KORUYARAK su donusumu yapiyor:
#     cx_yasa = CX_yasa + (cx_dow - 960) * (FX_yasa / FX_AKIS)
# Tersini almak icin AYNI FX_AKIS gerekir.
#
# ⚠ FX_AKIS, kamera.py'nin F_PX'i DEGILDIR ve olmamalidir:
#     FX_AKIS = 531.36  <- tespit_akisi'nin HFOV_DOW=122.0709 varsayimi
#     KAM.F_PX = 540.4  <- kamera.py'nin KENDI ucus kalibrasyonu
#   Ceviriyi F_PX ile yapmak, akisin YAPMADIGI bir donusumu geri almak olur
#   ve pikseli %1.7 kaydirir. Ters donusum ILERI donusumun eslenigi olmak
#   ZORUNDA; ham pikseli hangi f ile YORUMLAYACAGIMIZ ayri karardir ve orada
#   kamera.py'nin olcumu (540.4) esastir.
YASA_CX, YASA_CY = 320.0, 240.0
YASA_FX = (640.0 / 2.0) / math.tan(2.18166 / 2.0)          # 166.5786
HFOV_AKIS_DEG = float(os.environ.get("DOW_HFOV_AKIS", 122.0709))
FX_AKIS = (1920.0 / 2.0) / math.tan(math.radians(HFOV_AKIS_DEG) / 2.0)   # 531.36
OLCEK = FX_AKIS / YASA_FX                                  # 3.18979
# "yasa" = akis 640x480'e cevrilmis (canli sistemin varsayilani)
# "ham"  = akis 1920x1080 ham piksel veriyor (cevirme yapilmaz)
PIKSEL_UZAYI = os.environ.get("DOW_PIKSEL_UZAYI", "yasa").strip().lower()

status = {"faz": "-", "d_h": None, "durum": "-",
          "tgt_vx": 0.0, "tgt_vy": 0.0, "tgt_vz": 0.0}


def _yasa_pikselden_ham(cx, cy, w, h):
    """YASA cercevesi (640x480) -> HAM DoW cercevesi (1920x1080).
    Merkez etrafinda olceklenir; ayna KORUNUR (bkz. modul basligi (3))."""
    if PIKSEL_UZAYI == "ham":
        return cx, cy, w, h
    return (KAM.CX + (cx - YASA_CX) * OLCEK,
            KAM.CY + (cy - YASA_CY) * OLCEK,
            w * OLCEK, h * OLCEK)


def _kutu(pose):
    """pose kaydindan (cx,cy,w,h,conf) cikar -- HAM cercevede. Yoksa None."""
    if pose is None:
        return None
    conf = float(pose.get("conf", 0.0) or 0.0)
    bbox = pose.get("bbox")
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        w, h = (x2 - x1), (y2 - y1)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    elif pose.get("cx") is not None:
        cx, cy = float(pose["cx"]), float(pose["cy"])
        w = float(pose.get("w", 0.0) or 0.0)
        h = float(pose.get("h", 0.0) or 0.0)
    else:
        return None
    if w <= 0 or h <= 0:
        return None
    cx, cy, w, h = _yasa_pikselden_ham(cx, cy, w, h)
    return cx, cy, w, h, conf


def _uyu(t0, period):
    kalan = period - (time.monotonic() - t0)
    if kalan > 0:
        time.sleep(kalan)


# ══════════════════════════════════════════════════════════════════════════
#  GPS FAZI
# ══════════════════════════════════════════════════════════════════════════

def gps_fazi(conn, get_plane, get_iris, stop_event, cfg=Ayar):
    """Eski run_gps_guidance ile AYNI sozlesme. Yasa: dow/gps.py"""
    period = 1.0 / DONGU_HZ
    izleyici = YGPS.HedefIzleyici()
    status["faz"] = "GPS"
    alt = (cfg.ISTASYON_MENZIL_M * cfg.ISTASYON_ALT_ORAN
           if cfg.ISTASYON_ALT_ORAN > 0 else cfg.ISTASYON_ALT_M)
    print("[DOW-GPS] istasyon tutma basladi - kuyrukta %.2f m, altta %.2f m, "
          "ileri besleme=%s, Kp=%.2f/%.2f, V_MAX=%.1f m/s"
          % (cfg.ISTASYON_MENZIL_M, alt,
             "ACIK" if cfg.ISTASYON_ILERI else "KAPALI",
             cfg.ISTASYON_KP, cfg.ISTASYON_KP_Z, cfg.V_MAX))
    n = 0
    while not stop_event.is_set():
        t0 = time.monotonic()
        try:
            plane = get_plane()
            iris = get_iris()
        except Exception as e:
            print("[DOW-GPS] durum okunamadi: %r" % (e,))
            _uyu(t0, period)
            continue
        if not plane or not iris:
            _uyu(t0, period)
            continue

        # (1) NED -> Z-YUKARI  (bkz. modul basligi)
        hedef_p = (float(plane["x"]), float(plane["y"]), -float(plane["z"]))
        drone_p = (float(iris["x"]), float(iris["y"]), -float(iris["z"]))
        yaw_deg = math.degrees(float(iris.get("yaw", 0.0)))

        hedef_v = izleyici.guncelle(hedef_p, t0)
        v_xy, vz_ned, _yaw_rate, tani = YGPS.komut(
            drone_p, yaw_deg, hedef_p, hedef_v, izleyici.yon_deg, cfg)

        # yaw HIZI -> MUTLAK kerteriz (yasanin niyeti: burun DAIMA hedefe)
        cmd_yaw = math.radians(yaw_deg + tani["yaw_hata"])
        if send_velocity is None:
            raise RuntimeError("[DOW-GPS] send_velocity BAGLI DEGIL - "
                               "entegre.py amir'i baglamali (sessiz ucus riski)")
        send_velocity(conn, v_xy[0], v_xy[1], vz_ned, cmd_yaw)

        status.update(d_h=round(tani["hedef_menzil_m"], 1), durum="ISTASYON",
                      tgt_vx=hedef_v[0], tgt_vy=hedef_v[1], tgt_vz=hedef_v[2])
        n += 1
        if n % 40 == 0:
            print("[DOW-GPS] menzil=%.1fm ist_hata=%.1fm (yatay %.1f / dikey %+.1f) "
                  "hedef_hiz=%.1f yaw_hata=%+.0f v=%.1f"
                  % (tani["hedef_menzil_m"], tani["ist_hata_m"],
                     tani["ist_hata_yatay"], tani["ist_hata_dikey"],
                     tani["hedef_hiz"], tani["yaw_hata"], tani["v_istek"]))
        _uyu(t0, period)
    return "durduruldu"


# ══════════════════════════════════════════════════════════════════════════
#  GORSEL FAZ
# ══════════════════════════════════════════════════════════════════════════

def gorsel_fazi(conn, get_iris, wait_pose, stop_event, cfg=YIBVS.IbvsCfg,
                kayip_kare_esik=20, get_temas=None, **_yoksay):
    """Eski run_bbox_ibvs ile AYNI sozlesme. Yasa: dow/ibvs.py

    Donus: 'vuruldu' | 'kayip' | 'durduruldu'

    Eski cagrinin ff_hiz / kilit_t0 parametreleri KABUL EDILIR ama
    KULLANILMAZ: yeni yasa hedefin GPS'ini imzasinda hic tasimaz
    (yarisma kurali - ihlal yapisal olarak imkansiz).
    """
    hiz_I = 0.0
    kayip = 0
    son_seq = -1
    onceki_t = time.monotonic()
    n = 0
    status["faz"] = "GORSEL"
    print("[DOW-IBVS] gorsel gudum basladi - V_HUCUM=%.1f m/s, K_FWD=%.2f, "
          "K_I=%.3f, K_CY=%.4f, cy_ref %.0f->%.0f px, kayip esigi=%d ardisik "
          "kare | piksel uzayi=%s (olcek %.4f)"
          % (cfg.V_HUCUM, cfg.K_FWD, cfg.K_I, cfg.K_CY,
             cfg.CY_REF_UZAK, cfg.CY_REF_YAKIN, kayip_kare_esik,
             PIKSEL_UZAYI, 1.0 if PIKSEL_UZAYI == "ham" else OLCEK))

    while not stop_event.is_set():
        if get_temas is not None:
            try:
                if get_temas():
                    print("[DOW-IBVS] TEMAS - hedef vuruldu")
                    return "vuruldu"
            except Exception:
                pass

        kayit = wait_pose(son_seq, timeout=0.5)
        if kayit is None:
            kayip += 1
            if kayip >= kayip_kare_esik:
                print("[DOW-IBVS] kare akisi kesildi (%d ardisik) -> kayip" % kayip)
                return "kayip"
            continue
        son_seq = kayit.get("seq", son_seq)

        simdi = time.monotonic()
        dt = min(max(simdi - onceki_t, 0.001), 0.5)
        onceki_t = simdi

        k = _kutu(kayit.get("pose"))
        gecerli = False
        if k is not None:
            cx, cy, w, h, conf = k
            gecerli, _sebep = YIBVS.gecerli(cx, cy, w, h, conf, cfg)

        if not gecerli:
            kayip += 1
            if kayip >= kayip_kare_esik:
                print("[DOW-IBVS] %d ardisik gecersiz/kutusuz kare -> kayip" % kayip)
                return "kayip"
            continue
        kayip = 0

        try:
            iris = get_iris()
        except Exception:
            continue
        v_xy, vz_ned, yaw_hedef_deg, hiz_I, tani = YIBVS.komut(
            cx, cy, w, h,
            math.degrees(float(iris.get("yaw", 0.0))),
            math.degrees(float(iris.get("pitch", 0.0))),
            math.degrees(float(iris.get("roll", 0.0))),
            hiz_I, dt, cfg,
            own_vz=-float(iris.get("vz", 0.0)))     # NED asagi+ -> yukari+

        if send_velocity is None:
            raise RuntimeError("[DOW-IBVS] send_velocity BAGLI DEGIL")
        send_velocity(conn, v_xy[0], v_xy[1], vz_ned,
                      math.radians(yaw_hedef_deg))

        status.update(d_h=round(tani["ibvs_menzil_m"], 1), durum="GORSEL")
        n += 1
        if n % 30 == 0:
            print("[DOW-IBVS] kutu=%.0fpx menzil=%.1fm az=%+.1f e_cy=%+.0fpx "
                  "(ref %.0f) v=%.1f vz=%+.1f"
                  % (tani["ibvs_boyut_px"], tani["ibvs_menzil_m"],
                     tani["ibvs_azimut"], tani["ibvs_e_cy"], tani["ibvs_cy_ref"],
                     tani["ibvs_v"], tani["ibvs_vz_yukari"]))
    return "durduruldu"
