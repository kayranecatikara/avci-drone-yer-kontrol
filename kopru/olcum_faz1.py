# -*- coding: utf-8 -*-
"""
kopru/olcum_faz1.py — FAZ 1 oyun-ici olcumleri (dikey + yaw + hiz-kaynagi).

Kullanim (repo kokunden, oyun ACIK ve PLAY modunda, arac YERDE/spawn'da):
    python -m kopru.olcum_faz1 --mod hepsi     (veya dikey / hizkaynak / yaw)

Ne olcer (hepsi SAYIYLA raporlanir, CSV veri/kopru_olcum_*.csv):
  dikey    : vz=0'da irtifa tutma, +-2 m/s tirman/alcal adimlarinda ulasilan hiz,
             hover denge gazi (THR_TRIM dogrulamasi).
  hizkaynak: sabit pitch 0.3 ile 15 sn ileri ucus; SDK velocity vektoru ile
             konum sonlu-farki (ana_kontrol:744-771 EMA'si) KIYASI — capraz
             korelasyon gecikmesi (ms), gurultu std, kalici sapma. Ayrica ileri
             ucusta dikey trim kaymasi (ana_kontrol "ort thr=-0.45" referansi).
  yaw      : acik-dongu stick->donus hizi (0.3 ve 0.6'da deg/s, dogrusallik) +
             kapali-dongu +-90 deg adim (oturma, asim, toplam donus = kacak kaniti).

EMNIYET KATMANLARI (2026-08-06 kazasindan; kaza: dunya-z 48.4 spawn ZEMINI
"30 m irtifa" sanildi -> alcalma yere kondu -> ileri segment yerde suruklendi
-> patlama + respawn -> kalan olcumler olu araca kostu):
  * ZEMIN REFERANSI: baslangicta arac YERDE varsayilir, o anki dunya-z zemin
    kaydedilir; tum irtifa hedefleri/kosullari AGL = z - zemin ile.
  * Her mod KENDI kalkisini yapar (dikey/yaw 40 m AGL, hizkaynak 60 m AGL —
    ileri ucusta onde arazi yukselebilir, pay birakilir).
  * AGL KORUMASI: herhangi bir segmentte AGL < 15 m -> setpoint zorla tirmanisa
    cevrilir (satir guard=1 isaretlenir); yere yaklasma yapisal olarak kesilir.
  * RESPAWN/ISINLANMA DEDEKTORU: tik arasi 3B konum farki > 30 m -> olcum
    GECERSIZ, kalan modlar iptal (olu araca olcum kosulmaz), kullanici bilgilenir.
  * ARM KENARI: baslangicta arm False->True cevrimi (respawn sonrasi takilma
    ihtimaline karsi temiz arm gecisi).

GUVENLIK: Ctrl+C her modda yakalanir -> TRIM hover + sticks sifir.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time

import numpy as np

from sdk import drone_sdk as drone
from kopru.dow_kopru import CM, Cfg, DowKopru, sarmala_pi

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERI = os.path.join(_REPO, "veri")

GUARD_AGL_M = 15.0          # bu AGL altinda setpoint zorla tirmanis olur
GUARD_VZ_NED = -2.5         # korumanin tirmanis komutu (NED: negatif = yukari)
TELEPORT_M = 30.0           # tik arasi bu kadar konum sicramasi = respawn

KOLONLAR = [
    "t", "t_wall", "seg", "dt", "bayat", "guard",
    "x_m", "y_m", "alt_m", "agl_m", "yaw_dow_deg",
    "sp_vz", "vz_up_sp", "vz_up_sdk", "vz_up_fd", "e_vz", "i_vz",
    "vx_sdk", "vy_sdk", "vx_fd", "vy_fd",
    "sp_yaw_ned_deg", "yaw_hata_deg",
    "thr", "pitch", "roll", "yaw", "thr_ham", "thr_doydu",
]


class RespawnHatasi(RuntimeError):
    """Arac isinlandi/patladi — bu olcum gecersiz, kalan modlar iptal."""


class YatayFD:
    """Yatay hiz: konum sonlu-farki + EMA(0.7/0.3) — ana_kontrol:744-755 deseni."""

    def __init__(self):
        self.p = None
        self.t = None
        self.v = (0.0, 0.0)

    def guncelle(self, x, y, t):
        if self.p is None or self.t is None:
            self.p, self.t = (x, y), t
            return self.v
        dt = t - self.t
        if 1e-3 < dt < 0.5:
            ham = ((x - self.p[0]) / dt, (y - self.p[1]) / dt)
            self.v = (0.7 * self.v[0] + 0.3 * ham[0], 0.7 * self.v[1] + 0.3 * ham[1])
            self.p, self.t = (x, y), t
        elif dt >= 0.5:
            self.p, self.t = (x, y), t
        return self.v


class Kayitci:
    def __init__(self, mod, kolonlar=None):
        self.kolonlar = list(kolonlar or KOLONLAR)
        os.makedirs(_VERI, exist_ok=True)
        self.yol = os.path.join(
            _VERI, time.strftime(f"kopru_olcum_{mod}_%Y%m%d_%H%M%S.csv"))
        self.f = open(self.yol, "w", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=self.kolonlar,
                                extrasaction="ignore")
        self.w.writeheader()
        self.satirlar = []

    def yaz(self, d):
        self.satirlar.append(d)
        self.w.writerow({k: (round(v, 5) if isinstance(v, float) else v)
                         for k, v in d.items() if k in self.kolonlar})

    def kapat(self):
        self.f.close()


def kos_segment(kopru, kayitci, fd, zemin, ad, sure_s, vz_ned, yaw_sp_ned):
    """sure_s boyunca 50 Hz: taze setpoint + kopru.adim + log.
    AGL korumasi + respawn dedektoru burada (tum modlar ayni korumadan gecer)."""
    period = 1.0 / kopru.cfg.LOOP_HZ
    agl = kopru.sdk.get_drone_altitude() / CM - zemin
    print(f"[OLCUM]   segment {ad}: {sure_s:.0f} s, vz_ned {vz_ned:+.1f}, "
          f"baslangic AGL {agl:.1f} m")
    onceki_poz = None
    guard_ilan = False
    t_bit = time.monotonic() + sure_s
    while time.monotonic() < t_bit:
        t0 = time.monotonic()
        vz_kullan = vz_ned
        guard = 0
        if agl < GUARD_AGL_M:
            vz_kullan = GUARD_VZ_NED               # zorla tirman (yere yaklasma)
            guard = 1
            if not guard_ilan:
                print(f"[OLCUM]   !! AGL {agl:.1f} m < {GUARD_AGL_M:.0f} -> "
                      f"koruma tirmanisi (segment {ad})")
                guard_ilan = True
        kopru.set_hiz_ned(0.0, 0.0, vz_kullan, yaw_sp_ned)
        tani = dict(kopru.adim())
        agl = tani["alt_m"] - zemin
        poz = (tani["x_m"], tani["y_m"], tani["alt_m"])
        if onceki_poz is not None:
            sicrama = math.dist(poz, onceki_poz)
            if sicrama > TELEPORT_M:
                print(f"[OLCUM]   !! RESPAWN/ISINLANMA: tik arasi {sicrama:.0f} m "
                      f"(segment {ad}) — olcum gecersiz.")
                raise RespawnHatasi(ad)
        onceki_poz = poz
        vxf, vyf = fd.guncelle(tani["x_m"], tani["y_m"], tani["t"])
        tani.update(seg=ad, t_wall=time.time(), sp_vz=vz_kullan, agl_m=agl,
                    guard=guard, vx_fd=vxf, vy_fd=vyf)
        kayitci.yaz(tani)
        gecen = time.monotonic() - t0
        if gecen < period:
            time.sleep(period - gecen)


def _seg(kayit, ad):
    return [r for r in kayit.satirlar if r["seg"] == ad]


def _son_sn(satirlar, sn):
    if not satirlar:
        return []
    t1 = satirlar[-1]["t"]
    return [r for r in satirlar if r["t"] >= t1 - sn]


def _ort(satirlar, k):
    return float(np.mean([r[k] for r in satirlar])) if satirlar else float("nan")


# ── Analiz yardimcilari ─────────────────────────────────────────────────────

def xcorr_gecikme(a, b, hz, maks_s=0.5):
    """b'nin a'ya gore gecikmesi (ms; pozitif = b GEC). Normalize tepe korelasyonla."""
    a = np.asarray(a, float) - float(np.mean(a))
    b = np.asarray(b, float) - float(np.mean(b))
    n = len(a)
    maks = int(maks_s * hz)
    en_k, en_c = 0, -2.0
    for k in range(-maks, maks + 1):
        if k >= 0:
            aa, bb = a[:n - k] if k else a, b[k:]
        else:
            aa, bb = a[-k:], b[:n + k]
        if len(aa) < 20:
            continue
        payda = float(np.linalg.norm(aa) * np.linalg.norm(bb)) + 1e-12
        c = float(np.dot(aa, bb)) / payda
        if c > en_c:
            en_c, en_k = c, k
    return en_k * 1000.0 / hz, en_c


def puruz_std(x, hz, tau_s=0.3):
    """EMA(tau) duzlestirilmise gore artiklarin std'si (olcum gurultusu)."""
    a = 1.0 / (tau_s * hz)
    f = float(x[0])
    art = []
    for v in x:
        f += a * (float(v) - f)
        art.append(float(v) - f)
    return float(np.std(art))


def egim(ts, ys):
    """dogrusal fit egimi (birim/s)."""
    t = np.asarray(ts, float)
    y = np.asarray(ys, float)
    t = t - t[0]
    A = np.vstack([t, np.ones_like(t)]).T
    m, _b = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(m)


# ── Baglanti / hazirlik ─────────────────────────────────────────────────────

def baglan_ve_dogrula():
    if not drone.connect():
        print("[OLCUM] BAGLANTI YOK (127.0.0.1:12345). Oyun acik ve PLAY modunda mi?")
        sys.exit(2)
    time.sleep(1.0)
    p0 = drone.get_drone_location()
    time.sleep(0.7)
    p1 = drone.get_drone_location()
    if p0 == (0.0, 0.0, 0.0) and p1 == (0.0, 0.0, 0.0):
        print("[OLCUM] Telemetri hep (0,0,0) — oyun PLAY modunda gorunmuyor. Cikiliyor.")
        sys.exit(2)
    print(f"[OLCUM] Baglandi. Konum cm: {p1}  irtifa cm: {drone.get_drone_altitude():.0f}")


def hazirla():
    """Arm kenari + ZEMIN referansi (arac yerde varsayilir). Kalkis MODLARDA."""
    drone.set_arm(False)                # temiz arm kenari (respawn takilmasina karsi)
    time.sleep(0.3)
    kopru = DowKopru(drone, cfg=type("CfgOlcum", (Cfg,), {}))
    zemin = drone.get_drone_altitude() / CM
    print(f"[OLCUM] Zemin referansi (dunya-z): {zemin:.1f} m — tum hedefler AGL.")
    return kopru, zemin


def kalkis_yap(kopru, zemin, hedef_agl):
    agl = kopru.sdk.get_drone_altitude() / CM - zemin
    print(f"[OLCUM] Kalkis: AGL {agl:.1f} -> {hedef_agl:.0f} m ...")
    ok = kopru.kalkis(hedef_agl, zemin_m=zemin)
    agl = kopru.sdk.get_drone_altitude() / CM - zemin
    print(f"[OLCUM] Kalkis {'TAMAM' if ok else 'ZAMAN ASIMI'} — AGL {agl:.1f} m")
    if not ok:
        print("[OLCUM] Arac tirmanmiyor — oyunda gorevi/araci yeniden baslatmak "
              "gerekebilir. Cikiliyor.")
        sys.exit(3)


# ── MOD: dikey ──────────────────────────────────────────────────────────────

def mod_dikey(kopru, zemin, base_agl):
    kalkis_yap(kopru, zemin, base_agl)
    kayit = Kayitci("dikey")
    fd = YatayFD()
    yaw0 = kopru.get_iris()["yaw"]                 # mevcut burun yonu tutulur
    print("[OLCUM] dikey: hover0 15s / tirman 8s / hover1 5s / alcal 8s / hover2 5s")
    try:
        kos_segment(kopru, kayit, fd, zemin, "hover0", 15.0, 0.0, yaw0)
        kos_segment(kopru, kayit, fd, zemin, "tirman", 8.0, -2.0, yaw0)
        kos_segment(kopru, kayit, fd, zemin, "hover1", 5.0, 0.0, yaw0)
        kos_segment(kopru, kayit, fd, zemin, "alcal", 8.0, +2.0, yaw0)
        kos_segment(kopru, kayit, fd, zemin, "hover2", 5.0, 0.0, yaw0)
    finally:
        kayit.kapat()

    print("\n===== DIKEY RAPOR =====")
    h0 = _seg(kayit, "hover0")
    drift = h0[-1]["alt_m"] - h0[0]["alt_m"]
    print(f"hover0 (vz_sp=0, 15 s): irtifa drift {drift:+.2f} m, "
          f"ort thr {_ort(h0, 'thr'):+.3f}, son i_vz {h0[-1]['i_vz']:+.3f}, "
          f"alt-egimi {egim([r['t'] for r in h0], [r['alt_m'] for r in h0]):+.2f} m/s")
    for ad, sp in (("tirman", +2.0), ("alcal", -2.0)):
        s = _son_sn(_seg(kayit, ad), 5.0)
        print(f"{ad} (hedef {sp:+.1f} m/s yukari, son 5 s): "
              f"GERCEK alt-egimi {egim([r['t'] for r in s], [r['alt_m'] for r in s]):+.2f} m/s, "
              f"vz_fd {_ort(s, 'vz_up_fd'):+.2f}, vz_sdk {_ort(s, 'vz_up_sdk'):+.2f} m/s, "
              f"ort thr {_ort(s, 'thr'):+.3f}, son i_vz {s[-1]['i_vz']:+.3f}, "
              f"guard {sum(r['guard'] for r in s)} tik")
    for ad in ("hover1", "hover2"):
        s = _seg(kayit, ad)
        print(f"{ad}: drift {s[-1]['alt_m'] - s[0]['alt_m']:+.2f} m, "
              f"ort thr {_ort(s, 'thr'):+.3f}, son AGL {s[-1]['agl_m']:.1f} m")
    print(f"CSV: {kayit.yol}")


# ── MOD: hizkaynak ──────────────────────────────────────────────────────────

def mod_hizkaynak(kopru, zemin, base_agl):
    kalkis_yap(kopru, zemin, base_agl)
    kayit = Kayitci("hizkaynak")
    fd = YatayFD()
    yaw0 = kopru.get_iris()["yaw"]
    print("[OLCUM] hizkaynak: hover 3s / pitch 0.3 ileri 15s / birak 4s")
    try:
        kos_segment(kopru, kayit, fd, zemin, "hover", 3.0, 0.0, yaw0)
        kopru.cfg.PITCH_SABIT = 0.30
        kos_segment(kopru, kayit, fd, zemin, "ileri", 15.0, 0.0, yaw0)
        kopru.cfg.PITCH_SABIT = 0.0
        kos_segment(kopru, kayit, fd, zemin, "birak", 4.0, 0.0, yaw0)
    finally:
        kopru.cfg.PITCH_SABIT = 0.0
        kayit.kapat()

    print("\n===== HIZ KAYNAGI RAPORU (SDK velocity vs konum sonlu-farki) =====")
    hz = kopru.cfg.LOOP_HZ
    s = _seg(kayit, "ileri")
    s = [r for r in s if r["t"] >= s[0]["t"] + 2.0]        # ilk 2 s gecis atilir
    # emniyet suzgeci: tik arasi konum sicramasi buyuk satirlar analiz disi
    temiz = [s[0]]
    for i in range(1, len(s)):
        d3 = math.dist((s[i]["x_m"], s[i]["y_m"], s[i]["alt_m"]),
                       (s[i-1]["x_m"], s[i-1]["y_m"], s[i-1]["alt_m"]))
        if d3 < 5.0:
            temiz.append(s[i])
    s = temiz
    spd_sdk = [math.hypot(r["vx_sdk"], r["vy_sdk"]) for r in s]
    spd_fd = [math.hypot(r["vx_fd"], r["vy_fd"]) for r in s]
    print(f"ileri ucus ({len(s)/hz:.0f} s temiz pencere): ort hiz sdk "
          f"{np.mean(spd_sdk):.2f} m/s, fd {np.mean(spd_fd):.2f} m/s")
    for ad, a, b in (("vx", [r["vx_sdk"] for r in s], [r["vx_fd"] for r in s]),
                     ("vy", [r["vy_sdk"] for r in s], [r["vy_fd"] for r in s]),
                     ("hiz", spd_sdk, spd_fd)):
        gec, c = xcorr_gecikme(a, b, hz)
        print(f"  {ad}: fd'nin sdk'ya gore gecikmesi {gec:+.0f} ms (tepe korelasyon "
              f"{c:.3f}); gurultu std sdk {puruz_std(a, hz):.3f} / fd "
              f"{puruz_std(b, hz):.3f} m/s; kalici sapma (sdk-fd) "
              f"{np.mean(np.asarray(a) - np.asarray(b)):+.3f} m/s")
    print(f"ileri ucusta DIKEY: ort thr {_ort(s, 'thr'):+.3f}, "
          f"son i_vz {s[-1]['i_vz']:+.3f}, "
          f"alt-egimi {egim([r['t'] for r in s], [r['alt_m'] for r in s]):+.2f} m/s, "
          f"AGL {s[0]['agl_m']:.0f} -> {s[-1]['agl_m']:.0f} m "
          f"(ana_kontrol referansi: ileri ucusta trim -0.45'e kayar)")
    print(f"CSV: {kayit.yol}")


# ── MOD: yaw ────────────────────────────────────────────────────────────────

def _yaw_unwrap_topla(satirlar):
    top = 0.0
    onceki = None
    for r in satirlar:
        y = math.radians(r["yaw_dow_deg"])
        if onceki is not None:
            top += sarmala_pi(y - onceki)
        onceki = y
    return math.degrees(top)


def mod_yaw(kopru, zemin, base_agl):
    kalkis_yap(kopru, zemin, base_agl)
    kayit = Kayitci("yaw")
    fd = YatayFD()
    yaw0 = kopru.get_iris()["yaw"]
    print("[OLCUM] yaw: acik-dongu 0.3 ve 0.6 stick (4'er s) + kapali-dongu +-90 deg adim")
    try:
        kos_segment(kopru, kayit, fd, zemin, "hover", 3.0, 0.0, yaw0)
        for stick in (0.30, 0.60):
            kopru.cfg.YAW_SABIT = stick
            kos_segment(kopru, kayit, fd, zemin, f"acik_{stick:.2f}", 4.0, 0.0, yaw0)
            kopru.cfg.YAW_SABIT = None
            kos_segment(kopru, kayit, fd, zemin, f"dur_{stick:.2f}", 2.0, 0.0,
                        kopru.get_iris()["yaw"])
        for yon, ad in ((+90.0, "adim_p90"), (-90.0, "adim_n90")):
            y_bas = kopru.get_iris()["yaw"]
            hedef = sarmala_pi(y_bas + math.radians(yon))
            kos_segment(kopru, kayit, fd, zemin, ad, 10.0, 0.0, hedef)
    finally:
        kopru.cfg.YAW_SABIT = None
        kayit.kapat()

    print("\n===== YAW RAPORU =====")
    for stick in (0.30, 0.60):
        s = _son_sn(_seg(kayit, f"acik_{stick:.2f}"), 3.0)
        hiz = egim([r["t"] for r in s],
                   np.degrees(np.unwrap(np.radians([r["yaw_dow_deg"] for r in s]))))
        print(f"acik dongu stick {stick:+.2f}: donus hizi {hiz:+.1f} deg/s "
              f"(oran {abs(hiz) / stick:.1f} deg/s per birim stick)")
    for ad, yon in (("adim_p90", +90.0), ("adim_n90", -90.0)):
        s = _seg(kayit, ad)
        hatalar = [abs(r["yaw_hata_deg"]) for r in s]
        otur_t = None
        for r in s:
            if abs(r["yaw_hata_deg"]) < 5.0:
                otur_t = r["t"] - s[0]["t"]
                break
        toplam = _yaw_unwrap_topla(s)
        kuyruk = _son_sn(s, 2.0)
        print(f"{ad}: hedefe {yon:+.0f} deg adim -> oturma "
              f"{('%.2f s' % otur_t) if otur_t is not None else 'OLMADI'}, "
              f"toplam donus {toplam:+.1f} deg (kacak kontrolu: ~{yon:+.0f} olmali), "
              f"kalan hata son 2 s ort {_ort(kuyruk, 'yaw_hata_deg'):+.1f} deg, "
              f"max |hata| {max(hatalar):.1f} deg")
    print(f"CSV: {kayit.yol}")


# ── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="FAZ 1 kopru olcumleri (oyun gerekli)")
    ap.add_argument("--mod", choices=["dikey", "hizkaynak", "yaw", "hepsi"],
                    default="hepsi")
    ap.add_argument("--irtifa", type=float, default=40.0,
                    help="taban AGL (m); hizkaynak +20 kullanir")
    a = ap.parse_args()

    baglan_ve_dogrula()
    kopru, zemin = hazirla()
    try:
        if a.mod in ("dikey", "hepsi"):
            mod_dikey(kopru, zemin, a.irtifa)
        if a.mod in ("hizkaynak", "hepsi"):
            mod_hizkaynak(kopru, zemin, a.irtifa + 20.0)
        if a.mod in ("yaw", "hepsi"):
            mod_yaw(kopru, zemin, a.irtifa)
    except RespawnHatasi as e:
        print(f"\n[OLCUM] IPTAL: respawn/isinlanma ({e}). Kalan modlar KOSULMADI — "
              "oyunda gorevi yeniden baslatip scripti tekrar calistir.")
    except KeyboardInterrupt:
        print("\n[OLCUM] Kesildi — TRIM hover'a geciliyor.")
    finally:
        kopru.cfg.PITCH_SABIT = 0.0
        kopru.cfg.YAW_SABIT = None
        for _ in range(30):                        # sticks TRIM hover'a insin (slew)
            kopru.hover()
            time.sleep(0.02)
        print("[OLCUM] Bitti; arac hover'da birakildi.")


if __name__ == "__main__":
    main()
