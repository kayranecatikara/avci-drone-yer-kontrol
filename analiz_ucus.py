# -*- coding: utf-8 -*-
"""
UCUS DAVRANIS ANALIZI - ucus_log_*.csv'yi okuyup uc belirtiyi teshis eder:
  (a) GERI-CEKILME  : temasta kapanisin durmasi (v_close/vclose_true ~0, bounce)
  (b) SALINIM       : komut isaret-degisim frekansi, LOS acisal hizi, rate-limit/yaw doygunlugu
  (c) GORSEL TEMAS KAYBI : burun (nose_off_true) FOV konisi disina cikma araliklari

Her belirti icin: tespit (E/H) + nicel kanit + kok-neden + hangi Cfg parametresini
hangi yonde ayarla onerisi. Ayrica turlar-arasi kiyas icin bir metrik satirini
ucus_metrikler.csv'ye ekler (append).

KULLANIM:
  python analiz_ucus.py                # en yeni ucus_log_*.csv
  python analiz_ucus.py <dosya.csv>    # belirli dosya
Bagimlilik: numpy (pandas YOK).
"""
import csv
import glob
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Kontrolcu sabitleri (ana_kontrol.py Cfg ile ayni; teshis esikleri) ---
FOV_HALF_DEG = 65.77        # KAMERA_FOV_YARIM (131.54/2)
KAMERA_MENZIL_CM = 5000.0   # 50 m
STRIKE_RANGE_CM = 6000.0
MAX_DELTA = 0.05
YAW_MAX = 0.30
V_CLOSE = 1200.0
KP_CLOSE = 0.6
# Teshis esikleri
NEAR_CM = 2000.0            # "yakin" pencere (20 m) - terminal salinim/geri-cekilme
CONTACT_CM = 500.0          # "temas" esigi (5 m)
BOUNCE_CM = 300.0           # menzil bu kadar geri acilirsa "bounce"
EPS = 1e-9


def en_yeni_log():
    fs = sorted(glob.glob(os.path.join(HERE, "ucus_log_*.csv")))
    return fs[-1] if fs else None


def yukle(path):
    """CSV -> {kolon: np.array(float, nan)} + phase (str list). Bos -> nan."""
    with open(path, newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    header = r[0]
    rows = r[1:]
    idx = {name: i for i, name in enumerate(header)}
    n = len(rows)
    cols = {}
    for name, i in idx.items():
        if name == "phase" or name == "kaynak" or name == "durum":
            cols[name] = [(row[i] if i < len(row) else "") for row in rows]
        else:
            a = np.full(n, np.nan)
            for k, row in enumerate(rows):
                if i < len(row) and row[i] != "":
                    try:
                        a[k] = float(row[i])
                    except ValueError:
                        pass
            cols[name] = a
    return cols, idx, n


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def smooth(x, w=5):
    if len(x) < w:
        return x
    k = np.ones(w) / w
    return np.convolve(x, k, mode="same")


def signflip_hz(sig, tt):
    """Isaret-degisim frekansi (Hz): |sig| sifir-gecislerinin sayisi / sure."""
    s = sig[~np.isnan(sig)]
    if len(s) < 3:
        return 0.0
    sd = np.sign(s)
    sd[sd == 0] = 1
    flips = int(np.sum(sd[1:] != sd[:-1]))
    sure = tt[-1] - tt[0] if len(tt) > 1 else 1.0
    return flips / max(sure, 1e-3)


def sat_frac(cmd, max_delta):
    """Ardisik komut degisiminin rate-limit tavanina dayanma kesri."""
    c = cmd[~np.isnan(cmd)]
    if len(c) < 2:
        return 0.0
    d = np.abs(np.diff(c))
    return float(np.mean(d >= max_delta - 1e-3))


def araliklar(mask):
    """Boolean maskede ardisik True bloklarinin (baslangic, bitis) indeks ciftleri."""
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def analiz(path):
    cols, idx, n = yukle(path)
    print("=" * 78)
    print("UCUS ANALIZI :", os.path.basename(path), " (%d satir)" % n)
    print("=" * 78)

    phase = np.array(cols["phase"])
    for ph in ("TAKEOFF", "WARMUP", "DROPOUT", "APPROACH", "STRIKE"):
        c = int(np.sum(phase == ph))
        if c:
            print("  phase %-9s: %5d tik (~%.1f s)" % (ph, c, c * 0.02))
    active = (phase == "APPROACH") | (phase == "STRIKE")
    if np.sum(active) < 10:
        print("\n[!] Yeterli aktif (APPROACH/STRIKE) tik yok - ucus cok kisa ya da hep loiter.")
        return None

    t = cols["t_perf"]
    # aktif alt-dizi
    A = np.where(active)[0]
    t_a = t[A]

    # --- truth var mi? ---
    gm = cols["gercek_mesafe"]
    truth_var = np.sum(~np.isnan(gm[A])) > 0.5 * len(A)
    if truth_var:
        menzil = gm.copy()
        menzil_kaynak = "GERCEK (truth)"
    else:
        menzil = np.sqrt(np.nan_to_num(cols["ex"])**2 + np.nan_to_num(cols["ey"])**2
                         + np.nan_to_num(cols["ez"])**2)
        menzil_kaynak = "FILTRELI kestirim (truth yok!)"
        print("\n[!] TRUTH YOK - FOV/geri-cekilme metrikleri FILTRELI kestirime dayali "
              "(bias olabilir). Temiz teshis icin oyunda debug truth acik / gercek modda uc.")
    print("  Menzil kaynagi :", menzil_kaynak, " | Mod: terminal istatistik APPROACH+STRIKE")

    menzil_a = menzil[A]
    dt = np.diff(t_a)
    gecerli = (dt > 1e-3) & (dt < 0.5)

    # LOS acisi + acisal hiz (deg/s)
    if truth_var:
        tx, ty = cols["true_tx"][A], cols["true_ty"][A]
    else:
        tx = cols["est_x"][A]; ty = cols["est_y"][A]
    dx, dy = cols["drone_x"][A], cols["drone_y"][A]
    los = np.degrees(np.arctan2(ty - dy, tx - dx))
    los_rate = np.full(len(A), np.nan)
    dlos = wrap_deg(np.diff(los))
    los_rate[1:] = np.where(gecerli, dlos / np.where(dt == 0, np.nan, dt), np.nan)
    max_los_rate = float(np.nanmax(np.abs(los_rate))) if np.any(~np.isnan(los_rate)) else 0.0

    # gercek kapanis hizi (cm/s, + = kapaniyor)
    vclose_true = np.full(len(A), np.nan)
    vclose_true[1:] = np.where(gecerli, -np.diff(menzil_a) / np.where(dt == 0, np.nan, dt), np.nan)
    vclose_true = smooth(np.nan_to_num(vclose_true), 5)

    min_menzil = float(np.nanmin(menzil_a))
    i_min = int(np.nanargmin(menzil_a))

    rapor = {}

    # ================= (a) GERI-CEKILME =================
    print("\n" + "-" * 78)
    print("(a) GERI-CEKILME (temasta kapanmanin durmasi / geri gitme)")
    print("-" * 78)
    yakinda = menzil_a < NEAR_CM
    bounce = 0
    for i in range(1, len(menzil_a) - 1):
        if yakinda[i] and vclose_true[i - 1] > 5 and vclose_true[i] < -5:
            # kapaniyordu -> uzaklasmaya dondu; sonrasinda anlamli geri-acilma?
            ileri = menzil_a[i:min(i + 25, len(menzil_a))]
            if len(ileri) and (np.nanmax(ileri) - menzil_a[i]) > BOUNCE_CM:
                bounce += 1
    vclose_cmd = cols["v_close"][A]
    vclose_cmd_min = float(np.nanmin(vclose_cmd[yakinda])) if np.any(yakinda & ~np.isnan(vclose_cmd)) else float("nan")
    # en yakin yaklasimda komutlu v_close ve gercek kapanis
    vc_at_min = cols["v_close"][A][i_min]
    vct_at_min = vclose_true[i_min]
    tespit_a = (min_menzil > CONTACT_CM and vct_at_min < 20) or bounce > 0
    print("  min menzil        : %.1f m   (temas esigi %.1f m)" % (min_menzil / 100, CONTACT_CM / 100))
    print("  bounce (geri-acilma) sayisi : %d" % bounce)
    print("  en yakin anda: komut v_close=%s cm/s, gercek kapanis=%.0f cm/s"
          % (("%.0f" % vc_at_min if not np.isnan(vc_at_min) else "NA"), vct_at_min))
    print("  TESPIT: %s" % ("EVET - kapanis temastan ONCE duruyor/geri donuyor" if tespit_a
                            else "belirgin degil"))
    if tespit_a:
        print("  KOK-NEDEN: v_close = clamp(KP_CLOSE*d_s, 0, V_CLOSE) temasta ~0'a iner (ana_kontrol:528);")
        print("            son_hiz (hedef hizi) kalan butceyi asinca temas ivmesi kalmiyor -> geri-cekilme.")
        print("  ONERI  : KP_CLOSE 0.6->0.9 (dik kapanis) | V_CLOSE 1200->1500 | V_CLOSE tabani ekle "
              "(v_close=max(KP_CLOSE*d_s, ~300)) | STRIKE_RANGE'i biraz KUCULT.")
    rapor.update(min_menzil_m=min_menzil / 100, bounce_sayisi=bounce)

    # ================= (b) SALINIM =================
    print("\n" + "-" * 78)
    print("(b) SALINIM (saga-sola / komut titremesi)")
    print("-" * 78)
    yakin_mask = menzil_a < NEAR_CM
    tt_near = t_a[yakin_mask]
    roll_hz = signflip_hz(cols["roll_cmd"][A][yakin_mask], tt_near) if np.sum(yakin_mask) > 3 else 0.0
    yaw_hz = signflip_hz(cols["yaw_cmd"][A][yakin_mask], tt_near) if np.sum(yakin_mask) > 3 else 0.0
    pitch_hz = signflip_hz(cols["pitch_cmd"][A][yakin_mask], tt_near) if np.sum(yakin_mask) > 3 else 0.0
    roll_sat = sat_frac(cols["roll_cmd"][A], MAX_DELTA)
    pitch_sat = sat_frac(cols["pitch_cmd"][A], MAX_DELTA)
    yaw_sat_rl = sat_frac(cols["yaw_cmd"][A], MAX_DELTA)
    yaw_clip = float(np.mean(np.abs(cols["yaw_raw"][A][~np.isnan(cols["yaw_raw"][A])]) >= YAW_MAX - 1e-3)) \
        if np.any(~np.isnan(cols["yaw_raw"][A])) else 0.0
    tespit_b = roll_hz > 1.0 or pitch_hz > 1.0 or roll_sat > 0.4
    print("  yakin (menzil<%.0fm) komut isaret-degisim: roll=%.1f Hz  pitch=%.1f Hz  yaw=%.1f Hz"
          % (NEAR_CM / 100, roll_hz, pitch_hz, yaw_hz))
    print("  rate-limit doygunlugu: roll=%.0f%%  pitch=%.0f%%  yaw=%.0f%%"
          % (roll_sat * 100, pitch_sat * 100, yaw_sat_rl * 100))
    print("  yaw komutu YAW_MAX'a dayanma: %.0f%%   |  max LOS acisal hizi: %.0f deg/s"
          % (yaw_clip * 100, max_los_rate))
    print("  TESPIT: %s" % ("EVET - yakin mesafede belirgin komut salinimi" if tespit_b else "belirgin degil"))
    if tespit_b:
        print("  KOK-NEDEN olasilar (kanita gore siralı):")
        if max_los_rate > 120:
            print("   - Terminal geometri: menzil->0'da LOS acisal hizi ıraksıyor (%.0f deg/s); "
                  "carpisma-rotasi asiri-duzeltiyor." % max_los_rate)
        if roll_sat > 0.4 or pitch_sat > 0.4:
            print("   - Rate-limit doygun (%d%% roll): ham komut cok sarsintili / MAX_DELTA kucuk -> gecikme."
                  % int(roll_sat * 100))
        print("  ONERI  : KV_STRIKE 2.5->1.5 ve/veya STRIKE_TILT 0.8->0.5 (yumusat) | "
              "MAX_DELTA 0.05->0.08 (hizli tepki) | yaw salinimi varsa KP_YAW 1.0->0.6 / YAW_DEADBAND 3->5.")
    rapor.update(roll_signflip_hz=roll_hz, roll_sat_frac=roll_sat, yaw_sat_frac=yaw_clip,
                 max_los_rate_dps=max_los_rate)

    # ================= (c) GORSEL TEMAS KAYBI =================
    print("\n" + "-" * 78)
    print("(c) GORSEL TEMAS KAYBI (burun FOV konisi disinda)")
    print("-" * 78)
    nose = cols["nose_off_true"][A]
    if np.all(np.isnan(nose)):
        # truth yok -> yaw_err'e dus (filtreye gore; uyari)
        nose = np.degrees(np.abs(cols["yaw_err"][A]))
        print("  [!] nose_off_true yok (truth yok) -> |yaw_err| (FILTREYE gore) kullaniliyor.")
        nose_abs = nose
    else:
        nose_abs = np.abs(nose)
    kayip = (nose_abs > FOV_HALF_DEG) & (menzil_a < KAMERA_MENZIL_CM)
    olaylar = araliklar(np.nan_to_num(kayip.astype(float), nan=0).astype(bool))
    toplam_s = sum((t_a[b] - t_a[a]) for a, b in olaylar)
    tespit_c = len(olaylar) > 0
    print("  FOV yarim aci=%.1f deg, kamera menzili=%.0f m" % (FOV_HALF_DEG, KAMERA_MENZIL_CM / 100))
    print("  ort |nose_off|=%.1f deg, max=%.1f deg" % (np.nanmean(nose_abs), np.nanmax(nose_abs)))
    print("  GORSEL KAYIP olayi: %d adet, toplam %.1f s" % (len(olaylar), toplam_s))
    print("  TESPIT: %s" % ("EVET - hedef FOV disina cikiyor" if tespit_c else "HAYIR - hedef hep FOV icinde"))
    if tespit_c:
        # mekanizma ayirt: yaw-slew mi geometri mi?
        yaw_slew = 0; geo = 0
        for a, b in olaylar:
            seg = slice(a, b + 1)
            yaw_dayanma = np.mean(np.abs(cols["yaw_raw"][A][seg]) >= YAW_MAX - 1e-3) if b > a else 0
            los_seg = np.nanmax(np.abs(los_rate[seg])) if b > a else 0
            if yaw_dayanma > 0.5:
                yaw_slew += 1
            elif los_seg > 120:
                geo += 1
        print("  Mekanizma: yaw-slew-sinirli %d olay | geometri/overshoot %d olay" % (yaw_slew, geo))
        if yaw_slew >= geo:
            print("  ONERI  : YAW_MAX 0.30->0.45 ve/veya KP_YAW 1.0->1.5 (burun daha hizli hedefe donsun).")
        else:
            print("  ONERI  : STRIKE_RANGE'i KUCULT (erken devret) ve/veya V_CLOSE dusur "
                  "(temasta LOS acisal hizi sinirli kalsin).")
        # lead-nisan sapmasi kontrolu
        yaw_err_deg = np.degrees(np.abs(cols["yaw_err"][A]))
        if np.nanmean(yaw_err_deg[kayip]) < 10 and np.nanmean(nose_abs[kayip]) > FOV_HALF_DEG:
            print("  NOT: yaw_err (filtreye) kucuk ama nose_off_true buyuk -> LEAD-NISAN sapmasi "
                  "(filtre/lead gercek hedeften saptiriyor); gain degil, lead suresi/filtre konusu.")
    rapor.update(fov_kayip_s=toplam_s, fov_kayip_olay=len(olaylar),
                 max_nose_off=float(np.nanmax(nose_abs)))

    # ================= METRIK SATIRI =================
    mfile = os.path.join(HERE, "ucus_metrikler.csv")
    yeni = not os.path.exists(mfile)
    with open(mfile, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(["dosya", "min_menzil_m", "bounce_sayisi", "roll_signflip_hz",
                        "roll_sat_frac", "yaw_sat_frac", "fov_kayip_s", "fov_kayip_olay",
                        "max_los_rate_dps"])
        w.writerow([os.path.basename(path),
                    round(rapor["min_menzil_m"], 2), rapor["bounce_sayisi"],
                    round(rapor["roll_signflip_hz"], 2), round(rapor["roll_sat_frac"], 3),
                    round(rapor["yaw_sat_frac"], 3), round(rapor["fov_kayip_s"], 2),
                    rapor["fov_kayip_olay"], round(rapor["max_los_rate_dps"], 1)])
    print("\n" + "=" * 78)
    print("METRIK satiri eklendi -> ucus_metrikler.csv (turlar-arasi kiyas icin).")
    print("Ozet: min_menzil=%.1f m | bounce=%d | roll_salinim=%.1f Hz | roll_sat=%.0f%% | "
          "FOV_kayip=%.1f s (%d olay) | max_LOS=%.0f deg/s"
          % (rapor["min_menzil_m"], rapor["bounce_sayisi"], rapor["roll_signflip_hz"],
             rapor["roll_sat_frac"] * 100, rapor["fov_kayip_s"], rapor["fov_kayip_olay"],
             rapor["max_los_rate_dps"]))
    print("=" * 78)
    return rapor


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else en_yeni_log()
    if not path or not os.path.exists(path):
        print("ucus_log_*.csv bulunamadi. Once Cfg.LOG_ENABLE=True ile bir ucus yap.")
        sys.exit(1)
    analiz(path)
