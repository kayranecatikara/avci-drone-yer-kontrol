# -*- coding: utf-8 -*-
"""
================================================================================
 arac/kopru_denetim.py — KOPRU DENETIMI (analiz + cubuk seviyeli tezgah)
================================================================================
⚠ SALT OKUR. kopru/dow_kopru.py, kopru/entegre.py ve kopru/gazebo_kaynak/
  DEGISTIRILMEDI. Alternatif cevirici arac/kopru_alt.py'dedir.

NE YAPAR
    olcum   : kopru_tani_*.csv canli loglarindan yedi adayi tek tek olcer
    tesis   : CUBUK seviyeli arac modeli (sim/tesis.py hiz SETPOINT'i alir,
              koprunun cikisini sinayamaz — bu yuzden ayri tezgah gerekti)
    ab      : gercek DowKopru ile arac/kopru_alt.KopruAlt'i ayni tesiste kiyaslar

TESIS NEREDEN GELDI (uydurma yok — ACIK DONGU olcumu)
    veri/kopru_olcum_f2trim_pitch_20260806_170842.csv  (sabit cubuk basamaklari)
    veri/kopru_olcum_f2trim_roll_20260806_170939.csv
        v_ss = K*stick,  K = 91.0 (m/s)/stick   [0.15 -> 91.8, 0.20 -> 91.5,
                                                 0.30 -> 90.6, roll 0.20 -> 91.3]
        tau_v = 2.28 s   [2.27, 2.30, 2.27, 2.27, 2.30 — bes basamakta ayni]
    ic gecikme: olu zaman 0.046 s + ivme tau 0.211 s (sim/tesis.Olcum, basamak
        testinden). Basamagin ilk 0.6 s'indeki ivmenin saf birinci-mertebe
        modelin ~0.63'u cikmasi bu ic gecikmeyle birebir tutarli.
    yaw: yaw_rate = 181.4 * stick (2026-08-16 canli log regresyonu, r=0.855),
        zarf 214 deg/s.
    dikey: thr -0.60 = hover, +1.0 = +33.3 m/s, -1.0 = -5.6 m/s (ASIMETRIK).

KULLANIM
    python arac/kopru_denetim.py olcum     # canli loglardan yedi aday
    python arac/kopru_denetim.py dogrula   # tesisi acik dongu olcumune karsi sina
    python arac/kopru_denetim.py ab        # kopru vs kopru_alt
    python arac/kopru_denetim.py hepsi
"""

from __future__ import annotations

import glob
import math
import os
import sys

import numpy as np

os.environ.setdefault("AVCI_KOPRU_LOG", "0")     # tezgahta tani logu YAZMA

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

LOG_DZ = os.path.join(KOK, "kopru", "gazebo_kaynak", "logs")
VERI_DZ = os.path.join(KOK, "veri")


# ══════════════════════════════════════════════════════════════════════════
#  TESIS — CUBUK girisli arac modeli (olculmus)
# ══════════════════════════════════════════════════════════════════════════
class TesisOlcum:
    K_YATAY = 91.0          # (m/s)/stick — acik dongu basamak fiti
    TAU_V = 2.28            # s — hizin zaman sabiti (acik dongu)
    TAU_IC = 0.211          # s — cubuk -> ivme ic gecikmesi
    OLU_ZAMAN = 0.046       # s
    ZARF_IVME = 39.22       # m/s^2
    ZARF_HIZ = 34.6         # m/s
    YAW_STICK = 181.4       # deg/s per stick
    ZARF_YAW = 214.0        # deg/s
    THR_HOVER = -0.60       # denge gazi
    VZ_UP_STICK = 20.8      # m/s per stick, TIRMANMA tarafi (33.3/1.60)
    VZ_DN_STICK = 14.0      # m/s per stick, ALCALMA tarafi ( 5.6/0.40)
    ZARF_TIRMANMA = 33.7
    ZARF_ALCALMA = -5.6
    TAU_VZ = 1.20           # s (dikey; denetimin odagi degil)


class Tesis:
    """DoW aracinin CUBUK -> hareket modeli. Cerceve: DoW dunya, z YUKARI,
    yaw CCW (+x burun). Birimler SI (m, m/s, rad) — SDK adaptoru cm'ye cevirir."""

    def __init__(self, x=0.0, y=0.0, z=90.0, yaw=0.0, o=TesisOlcum):
        self.o = o
        self.x, self.y, self.z = x, y, z
        self.vx = self.vy = self.vz = 0.0        # DoW dunya, vz YUKARI +
        self.yaw = yaw
        self.roll = self.pitch = 0.0
        self._kuyruk = []                        # olu zaman kuyrugu
        self._u = (o.THR_HOVER, 0.0, 0.0, 0.0)   # ic gecikmeden GECMIS cubuk
        self.t = 0.0

    # ── kopru buraya yazar ──
    def cubuk(self, thr, pitch, roll, yaw):
        self._kuyruk.append((self.t + self.o.OLU_ZAMAN, thr, pitch, roll, yaw))

    def adim(self, dt):
        o = self.o
        self.t += dt
        ham = None
        while self._kuyruk and self._kuyruk[0][0] <= self.t:
            ham = self._kuyruk.pop(0)
        if ham is not None:
            self._ham = ham[1:]
        hedef = getattr(self, "_ham", self._u)
        # ic gecikme: cubuk -> etkin cubuk, birinci mertebe (tau 0.211)
        a = min(dt / o.TAU_IC, 1.0)
        self._u = tuple(u + (h - u) * a for u, h in zip(self._u, hedef))
        thr, pit, rol, yaw_u = self._u

        # ── YAW ──
        yr = math.radians(max(-o.ZARF_YAW, min(o.ZARF_YAW, o.YAW_STICK * yaw_u)))
        self.yaw = (self.yaw + yr * dt + math.pi) % (2 * math.pi) - math.pi

        # ── YATAY: govde cercevesinde birinci mertebe, dunyada entegre ──
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        v_f = self.vx * c + self.vy * s
        v_r = self.vx * s - self.vy * c
        a_f = (o.K_YATAY * pit - v_f) / o.TAU_V
        a_r = (o.K_YATAY * rol - v_r) / o.TAU_V
        am = math.hypot(a_f, a_r)
        if am > o.ZARF_IVME:                      # ivme zarfi
            k = o.ZARF_IVME / am
            a_f, a_r = a_f * k, a_r * k
        # govde ivmesini DUNYAYA cevir (govde donuyor; dunyada entegre etmek
        # merkezkac terimini KENDILIGINDEN dogru yapar)
        ax = a_f * c + a_r * s
        ay = a_f * s - a_r * c
        self.vx += ax * dt
        self.vy += ay * dt
        vm = math.hypot(self.vx, self.vy)
        if vm > o.ZARF_HIZ:
            k = o.ZARF_HIZ / vm
            self.vx, self.vy = self.vx * k, self.vy * k
        self.roll = math.atan2(a_r, 9.81)
        self.pitch = -math.atan2(a_f, 9.81) * 0.5

        # ── DIKEY (asimetrik) ──
        d = thr - o.THR_HOVER
        vz_ss = (o.VZ_UP_STICK * d) if d >= 0 else (o.VZ_DN_STICK * d)
        vz_ss = max(o.ZARF_ALCALMA, min(o.ZARF_TIRMANMA, vz_ss))
        self.vz += (vz_ss - self.vz) / o.TAU_VZ * dt

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt


class SahteSDK:
    """DowKopru'nun get_telemetry/set_control_surfaces sozlesmesi (DoW birimleri)."""

    def __init__(self, tesis):
        self.tesis = tesis
        self.son = (0.0, 0.0, 0.0, 0.0)

    def get_telemetry(self):
        t = self.tesis
        return {"drone": {"position": (t.x * 100, t.y * 100, t.z * 100),
                          "velocity": (t.vx * 100, t.vy * 100, t.vz * 100),
                          "rotation": (math.degrees(t.roll), math.degrees(t.pitch),
                                       math.degrees(t.yaw))}}

    def set_control_surfaces(self, thr, pitch, roll, yaw, arm):
        self.son = (thr, pitch, roll, yaw)
        self.tesis.cubuk(thr, pitch, roll, yaw)

    def set_arm(self, v):
        pass

    def get_drone_altitude(self):
        return self.tesis.z * 100


# ══════════════════════════════════════════════════════════════════════════
#  1) CANLI LOG OLCUMLERI
# ══════════════════════════════════════════════════════════════════════════
def _tani_yukle(desen="kopru_tani_20260816_*.csv", seyir=True):
    import pandas as pd
    D = []
    for f in sorted(glob.glob(os.path.join(LOG_DZ, desen))):
        c = pd.read_csv(f)
        c = c[c["bayat"] == 0].reset_index(drop=True)
        if len(c) < 500:
            continue
        # ⚠ 't' kolonu "%.6g" ile yazildigi icin 1 s'ye yuvarlanmis; zaman
        #   'dt'den yeniden kurulur (bkz. dow_kopru._tani_bosalt).
        c["tt"] = np.cumsum(c["dt"].values)
        yd = np.radians(c["yaw_dow_deg"].values)
        c["yawrate"] = np.gradient(np.unwrap(yd), c["tt"].values) * 180 / math.pi
        cs, sn = np.cos(yd), np.sin(yd)
        w = 6
        ax = np.full(len(c), np.nan); ay = np.full(len(c), np.nan)
        tt = c["tt"].values
        ax[w:-w] = (c.vx_sdk.values[2 * w:] - c.vx_sdk.values[:-2 * w]) / (tt[2 * w:] - tt[:-2 * w])
        ay[w:-w] = (c.vy_sdk.values[2 * w:] - c.vy_sdk.values[:-2 * w]) / (tt[2 * w:] - tt[:-2 * w])
        c["a_fwd"] = ax * cs + ay * sn
        c["a_right"] = ax * sn - ay * cs
        c["a_yatay"] = np.hypot(ax, ay)
        D.append(c)
    d = pd.concat(D, ignore_index=True)
    if seyir:
        d = d[(d["alt_m"] > 55) & (d["vh_sdk"] > 5)].reset_index(drop=True)
    return d


def olcum():
    import pandas as pd
    print("=" * 78)
    print(" KOPRU DENETIMI — canli log olcumleri (kopru_tani_*.csv)")
    print("=" * 78)

    # --- bayat (aday 3): TUM tikler, seyir filtresi YOK ---
    tot = bay = 0
    for f in sorted(glob.glob(os.path.join(LOG_DZ, "kopru_tani_20260816_*.csv"))):
        c = pd.read_csv(f, usecols=["dt", "bayat"])
        tot += len(c); bay += int(c["bayat"].sum())
    print("\n[3] BAYAT: %d / %d tik = %.4f%%  (koddaki %%27.8 notu 2026-08-10'a ait,"
          " BAYAT_S_GORSEL 1.0 -> 2.5 duzeltmesinden ONCE)" % (bay, tot, 100 * bay / tot))

    d = _tani_yukle()
    n = len(d)
    print("\nseyir tigi (alt>55 m, vh>5 m/s): n = %d" % n)

    # --- 1) MAX_DELTA ---
    print("\n[1] MAX_DELTA = 0.05 — hiz siniri kac tikte BAGLIYOR")
    for k in ["thr", "pitch", "roll", "yaw"]:
        dv = np.abs(np.diff(d[k].values))
        print("    %-6s %6.2f%%" % (k, 100 * np.mean(dv >= 0.05 - 1e-6)))
    print("    -> pitch/roll'da SEYREK cunku kazanc zaten cubugu hizli surmuyor;")
    print("       thr'de sik cunku HIZ_KAYNAK='sonlu_fark' gurultulu (asagi bak).")

    # --- 2) tavanlar ---
    print("\n[2] CUBUK TAVANI DOYMA (istenen komut, kirpma oncesi)")
    print("    |pitch_cmd|>=0.75 : %.3f%%" % (100 * np.mean(np.abs(d.pitch_cmd) >= 0.75 - 1e-6)))
    print("    |roll_cmd| >=0.75 : %.3f%%" % (100 * np.mean(np.abs(d.roll_cmd) >= 0.75 - 1e-6)))
    yd_ = np.clip(1.3 * np.radians(d.yaw_hata_deg.values), -0.85, 0.85)
    print("    |yaw_cmd|  >=0.85 : %.3f%%" % (100 * np.mean(np.abs(yd_) >= 0.85 - 1e-6)))
    print("    thr_ham <= -1.00  : %.3f%%   thr_ham >= 0.70 : %.3f%%"
          % (100 * np.mean(d.thr_ham <= -1.0), 100 * np.mean(d.thr_ham >= 0.70)))
    st = np.hypot(d.pitch, d.roll)
    print("    |yatis stick| p50=%.3f p90=%.3f p99=%.3f max=%.3f (tek eksen tavani 0.75)"
          % tuple(np.percentile(st, [50, 90, 99]).tolist() + [st.max()]))

    # --- 4) yatay PI ---
    print("\n[4] YATAY PI")
    for k, mx in [("i_fwd", 0.15), ("i_right", 0.15), ("i_vz", 0.60)]:
        v = np.abs(d[k].values)
        print("    %-8s p50=%.4f p95=%.4f max=%.4f  DOYUM=%.2f%% (tavan %.2f)"
              % (k, np.median(v), np.percentile(v, 95), v.max(),
                 100 * np.mean(v >= mx - 1e-6), mx))
    print("    |e_fwd|  p50=%.2f p90=%.2f m/s | band(2.5) disi %%%.1f (integral DONUK)"
          % (np.median(np.abs(d.e_fwd)), np.percentile(np.abs(d.e_fwd), 90),
             100 * np.mean(np.abs(d.e_fwd) > 2.5)))
    print("    |e_right|p50=%.2f p90=%.2f m/s | band(2.5) disi %%%.1f"
          % (np.median(np.abs(d.e_right)), np.percentile(np.abs(d.e_right), 90),
             100 * np.mean(np.abs(d.e_right) > 2.5)))

    # --- ASIL BULGU: kazanc mi tavan mi bagliyor ---
    print("\n[1+2+4 BIRLESIK] yaw hizina gore hata / uretilen roll")
    d2 = d.copy(); d2["yb"] = pd.cut(d2["yawrate"].abs(), [0, 8, 25, 60, 120, 400])
    for k, x in d2.groupby("yb", observed=True):
        print("    |yawrate| %-11s n=%6d  |e_right|p50=%5.2f m/s -> |roll|p50=%.3f"
              "  (KP_VH*e = %.3f)  roll_doyum=%.2f%%"
              % (str(k), len(x), np.median(np.abs(x.e_right)), np.median(np.abs(x.roll)),
                 0.024 * np.median(np.abs(x.e_right)),
                 100 * np.mean(np.abs(x.roll_cmd) >= 0.75 - 1e-6)))

    # --- 5) eksen ciftlenmesi ---
    print("\n[5] EKSEN CIFTLENMESI: |yaw stick| kovanlarinda yanal ivme kazanci")
    d3 = d.copy(); d3["yb"] = pd.cut(d3["yaw"].abs(), [0, 0.05, 0.2, 0.4, 0.6, 0.86])
    for k, x in d3.groupby("yb", observed=True):
        m = (np.abs(x.roll) > 0.02) & np.isfinite(x.a_right)
        if m.sum() < 500:
            continue
        s = np.polyfit(x.roll[m], x.a_right[m], 1)
        print("    |yaw| %-12s n=%6d  a_right/roll = %5.1f m/s^2/stick  (r=%.3f)"
              % (str(k), len(x), s[0], np.corrcoef(x.roll[m], x.a_right[m])[0, 1]))
    a = d["a_yatay"].values; a = a[np.isfinite(a)]
    print("    gerceklesen |a_yatay| p50=%.1f p99=%.1f p99.9=%.1f (zarf 39.22)"
          % (np.percentile(a, 50), np.percentile(a, 99), np.percentile(a, 99.9)))

    # --- 6) cerceve ---
    print("\n[6] CERCEVE CEVRIMI")
    m = d["vh_sp"] > 5
    spx = d.sp_vx.values[m]; spy = -d.sp_vy.values[m]     # ned_to_dow
    vx = d.vx_sdk.values[m]; vy = d.vy_sdk.values[m]
    ang = np.degrees(np.arctan2(spx * vy - spy * vx, spx * vx + spy * vy))
    ang2 = np.degrees(np.arctan2(spx * vy + spy * vx, spx * vx - spy * vy))
    print("    komut->gerceklesen |aci| p50 = %.2f deg   (y-isareti TERS olsaydi: %.2f)"
          % (np.median(np.abs(ang)), np.median(np.abs(ang2))))
    yw = np.abs(d.yawrate.values[m])
    print("      |yawrate|<8  alt kumesi: %.2f deg  (n=%d, ucusun %%%.0f'i)"
          % (np.median(np.abs(ang[yw < 8])), (yw < 8).sum(), 100 * np.mean(yw < 8)))
    print("      |yawrate|>60 alt kumesi: %.2f deg  (n=%d)"
          % (np.median(np.abs(ang[yw > 60])), (yw > 60).sum()))
    s = np.polyfit(d.yawrate.values[m], ang, 1)
    print("    isaretli hata = %+.4f*yawrate %+.2f -> ortulu gecikme %.0f ms"
          % (s[0], s[1], -s[0] * 1000))
    r = np.gradient(np.unwrap(np.radians(d.yaw_dow_deg.values)), d.tt.values) * 180 / math.pi
    mm = np.abs(d["yaw"].values) > 0.2
    print("    yaw isareti: corr(stick, d(yaw)/dt) = %+.3f  (>0 = DOGRU)"
          % np.corrcoef(d["yaw"].values[mm], r[mm])[0, 1])

    # --- 7) dikey ---
    print("\n[7] DIKEY KANAL — komut vs gerceklesen (irtifa egimi hakem)")
    dd = _tani_yukle(seyir=False)
    z = dd["alt_m"].values; tt = dd["tt"].values; w = 20
    vzr = np.full(len(z), np.nan)
    vzr[w:-w] = (z[2 * w:] - z[:-2 * w]) / (tt[2 * w:] - tt[:-2 * w])
    dd = dd[(dd["alt_m"] > 55) & np.isfinite(vzr)].copy()
    dd["vz_ref"] = vzr[np.isfinite(vzr) & (z > 55)]
    dd["b"] = pd.cut(dd["vz_up_sp"], [-30, -4, -2, -0.5, 0.5, 2, 4, 30])
    for k, x in dd.groupby("b", observed=True):
        print("    vz_sp %-13s n=%6d  istenen p50=%+6.2f  gerceklesen p50=%+6.2f"
              "  ACIK=%+5.2f m/s  thrDN_doyum=%5.1f%%"
              % (str(k), len(x), np.median(x.vz_up_sp), np.median(x.vz_ref),
                 np.median(x.vz_ref) - np.median(x.vz_up_sp),
                 100 * np.mean(x.thr_ham <= -1.0)))
    print("    FF_VZ = 1/33.33 = 0.0300 stick/(m/s) — TIRMANMA egimi.")
    print("    ALCALMA egimi olculdu: 5.6 m/s / 0.40 stick -> 0.0714 stick/(m/s).")
    print("    Yani alcalma tarafinda ileri-besleme 2.4x KUCUK; farki integrator")
    print("    kapatmak zorunda (KI_VZ=0.15 ile ~yavas) -> yukaridaki ACIK.")
    sc = dd[dd["vh_sdk"] > 5]
    print("    dikey gurultu: thr_ham |diff| p50=%.4f p90=%.4f (MAX_DELTA=0.05)"
          % (np.median(np.abs(np.diff(sc.thr_ham.values))),
             np.percentile(np.abs(np.diff(sc.thr_ham.values)), 90)))


# ══════════════════════════════════════════════════════════════════════════
#  2) TESIS DOGRULAMA — acik dongu olcumune karsi
# ══════════════════════════════════════════════════════════════════════════
def dogrula():
    print("=" * 78)
    print(" TESIS DOGRULAMA — acik dongu basamaklarina karsi (kopru KAPALI)")
    print("=" * 78)
    print(" olculen (veri/kopru_olcum_f2trim_pitch): 0.10->8.70  0.15->13.17")
    print("                                          0.20->17.56 0.30->26.15 0.45->32.86 m/s")
    print("\n  stick   tesis_v(8 s)   olculen   fark")
    olc = {0.10: 8.70, 0.15: 13.17, 0.20: 17.56, 0.30: 26.15, 0.45: 32.86}
    hata = []
    for u, gercek in olc.items():
        t = Tesis(); dt = 1 / 50.0
        for _ in range(int(8.0 / dt)):
            t.cubuk(TesisOlcum.THR_HOVER, u, 0.0, 0.0)
            t.adim(dt)
        v = math.hypot(t.vx, t.vy)
        hata.append(v - gercek)
        print("  %.2f    %7.2f      %7.2f   %+6.2f" % (u, v, gercek, v - gercek))
    print("\n  RMS fark = %.2f m/s  (olcum surelerinin kendisi 6-9 s, tam oturmamis)"
          % math.sqrt(np.mean(np.array(hata) ** 2)))
    # yaw
    t = Tesis(); dt = 1 / 50.0
    for _ in range(int(2.0 / dt)):
        t.cubuk(TesisOlcum.THR_HOVER, 0, 0, 0.85); t.adim(dt)
    y0 = t.yaw
    for _ in range(int(1.0 / dt)):
        t.cubuk(TesisOlcum.THR_HOVER, 0, 0, 0.85); t.adim(dt)
    print("  yaw 0.85 stick -> %.0f deg/s (canli log regresyonu: 154)"
          % math.degrees((t.yaw - y0 + math.pi) % (2 * math.pi) - math.pi))


# ══════════════════════════════════════════════════════════════════════════
#  3) A/B — gercek kopru vs alternatif, ayni tesiste
# ══════════════════════════════════════════════════════════════════════════
def _kos(kopru_sinif, cfg, senaryo, sure=12.0, hz=50.0, gudum_hz=20.0):
    """Kopruyu tesise bagla, senaryodan setpoint besle, izlemeyi kaydet."""
    tesis = Tesis()
    sdk = SahteSDK(tesis)
    k = kopru_sinif(sdk, cfg=cfg)
    dt = 1.0 / hz
    n = int(sure / hz ** 0) if False else int(sure * hz)
    gudum_ara = max(1, int(round(hz / gudum_hz)))
    kayit = {"t": [], "vx": [], "vy": [], "spx": [], "spy": [],
             "pitch": [], "roll": [], "yaw_stick": [], "yaw": []}
    for i in range(n):
        t = i * dt
        if i % gudum_ara == 0:
            vx_n, vy_n, vz_n, yaw_n = senaryo(t)
            k.set_hiz_ned(vx_n, vy_n, vz_n, yaw_n)
        k.adim(dt=dt)
        tesis.adim(dt)
        vx_n, vy_n, _, _ = senaryo(t)
        kayit["t"].append(t)
        kayit["vx"].append(tesis.vx); kayit["vy"].append(tesis.vy)
        # setpoint NED -> DoW dunya
        kayit["spx"].append(vx_n); kayit["spy"].append(-vy_n)
        kayit["pitch"].append(sdk.son[1]); kayit["roll"].append(sdk.son[2])
        kayit["yaw_stick"].append(sdk.son[3]); kayit["yaw"].append(tesis.yaw)
    return {a: np.array(b) for a, b in kayit.items()}


def _metrik(r, t0):
    """Yukselme suresi / asma / kalici hata — hiz VEKTORU buyuklugu ve yonu."""
    m = r["t"] >= t0
    sp = np.hypot(r["spx"], r["spy"])
    v = np.hypot(r["vx"], r["vy"])
    hedef = sp[m][-1]
    # yon hatasi
    ang = np.degrees(np.arctan2(r["spx"] * r["vy"] - r["spy"] * r["vx"],
                                r["spx"] * r["vx"] + r["spy"] * r["vy"]))
    # yukselme: basamak sonrasi hedefin %90'ina ilk varis
    idx = np.where(m)[0]
    v0 = v[idx[0]]
    hedef90 = v0 + 0.9 * (hedef - v0)
    tr = np.nan
    for i in idx:
        if (hedef > v0 and v[i] >= hedef90) or (hedef < v0 and v[i] <= hedef90):
            tr = r["t"][i] - t0
            break
    asma = 100 * (v[idx].max() - hedef) / max(abs(hedef), 1e-6) if hedef > v0 else np.nan
    son = idx[-int(len(idx) * 0.25):]
    return {"t_yuks": tr, "asma%": asma, "kalici": np.mean(v[son]) - hedef,
            "yon_p50": np.median(np.abs(ang[son])),
            "yon_rms": math.sqrt(np.mean(ang[son] ** 2)),
            "hiz_rms": math.sqrt(np.mean((v[idx] - sp[idx]) ** 2)),
            "roll_max": np.abs(r["roll"][idx]).max(),
            "pitch_max": np.abs(r["pitch"][idx]).max()}


def ab():
    from kopru.dow_kopru import Cfg as KCfg, DowKopru
    from arac.kopru_alt import CfgAlt, KopruAlt

    class CfgBaz(KCfg):
        YATAY_AKTIF = True
    class CfgAlt2(CfgAlt):
        YATAY_AKTIF = True

    print("=" * 78)
    print(" A/B — kopru/dow_kopru (MEVCUT) vs arac/kopru_alt (ALTERNATIF)")
    print("=" * 78)
    print(" tesis: K=91 (m/s)/stick, tau_v=2.28 s, ic gecikme 0.046+0.211 s,")
    print("        ivme zarfi 39.22, hiz zarfi 34.6 — hepsi OLCULDU")
    print(" fark : KP_VH 0.024->0.070 ; MAX_DELTA(pitch/roll) 0.05->0.15")

    # ⚠ Yasa burnu HER ZAMAN komut edilen hiz yonune cevirir (canli olcum:
    #   yaw hizi ~0 iken komut-gerceklesen aci 1.6 deg). Senaryolarda yaw
    #   setpoint'i bu yuzden NED hiz yonunden TURETILIR — elle verilirse
    #   burun ile hiz komutu ters yone donebiliyor (ilk surumde oldu).
    def _yaw_ned(vx, vy):
        return math.atan2(vy, vx)

    # ── S1: yanal basamak (en zorlayici — yanal kanalda trim ileri-beslemesi yok)
    def s_yanal(t):
        v = (20.0, 0.0) if t < 3.0 else (20.0, -12.0)
        return (v[0], v[1], 0.0, _yaw_ned(*v))

    # ── S2..S4: donen hiz VEKTORU (gercek angajman geometrisi)
    def s_donus(w):
        def f(t):
            a = math.radians(w) * max(0.0, t - 3.0)
            v = (20.0 * math.cos(a), 20.0 * math.sin(a))
            return (v[0], v[1], 0.0, _yaw_ned(*v))
        return f

    senaryolar = [("S1 yanal basamak 0->12 m/s", s_yanal, 3.0, 12.0),
                  ("S2 hiz vektoru donuyor  45 d/s", s_donus(45), 3.0, 14.0),
                  ("S3 hiz vektoru donuyor  90 d/s", s_donus(90), 3.0, 14.0),
                  ("S4 hiz vektoru donuyor 135 d/s", s_donus(135), 3.0, 14.0)]

    for ad, sen, t0, sure in senaryolar:
        print("\n--- %s ---" % ad)
        print("  %-12s %8s %8s %8s %9s %9s %9s %8s"
              % ("kopru", "t_yuks", "asma%", "kalici", "yon_p50", "yon_rms", "hiz_rms", "roll_max"))
        for nm, cls, cfg in [("MEVCUT", DowKopru, CfgBaz), ("ALT", KopruAlt, CfgAlt2)]:
            r = _kos(cls, cfg, sen, sure=sure)
            m = _metrik(r, t0)
            print("  %-12s %8.3f %8.1f %8.2f %9.2f %9.2f %9.2f %8.3f"
                  % (nm, m["t_yuks"], m["asma%"], m["kalici"], m["yon_p50"],
                     m["yon_rms"], m["hiz_rms"], m["roll_max"]))
    print("\n  t_yuks  : hiz buyuklugunun %90'ina varis (s)   asma%: yuzde asim")
    print("  yon_p50 : oturmus bolgede komut-gerceklesen ACI (deg) — asil olcut")
    print("  hiz_rms : basamak sonrasi hiz vektor buyuklugu hatasi (m/s)")


def main():
    k = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if k in ("olcum", "hepsi"):
        olcum()
    if k in ("dogrula", "hepsi"):
        print(); dogrula()
    if k in ("ab", "hepsi"):
        print(); ab()


if __name__ == "__main__":
    main()
