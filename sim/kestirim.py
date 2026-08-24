"""
sim/kestirim.py — ÖNGÖRÜLÜ NİŞAN TEZGÂHI (oyun açmadan, çevrimdışı).

NE YAPAR
    1. `yukle`   : bbox_ibvs_*.csv (kamera) + veri/hedef_iz/*.csv (truth) hizalar
    2. `menzil`  : kutu boyutu → menzil modelini truth'la ÖLÇER (vekil yanlılığı)
    3. `kor`     : kestirimciyi KÖR test eder (yalnız kamera girdisi, truth cevap)
    4. `kesme`   : kesme noktası fizibilitesi (aspect × menzil × hız zarfı)
    5. `korbolge`: son geçerli ölçümden temasa açık çevrim ıska bütçesi
    6. `cevrim`  : kapalı çevrim benzetimi — saf takip vs öngörülü nişan

⛔ KURAL: kestirimciye YALNIZ {t,cx,cy,w,h,conf} + KENDİ durumumuz girer.
   Truth (hx,hy,hz,h_vx…) YALNIZ cevap anahtarı olarak kullanılır; hiçbir
   kod yolunda kestirimciye geçmez. `_KameraKare` sözleşmesi bunu kilitler.

Kullanım:
    python sim/kestirim.py yukle        # önbellek kur (bir kez)
    python sim/kestirim.py menzil
    python sim/kestirim.py kor
    python sim/kestirim.py kesme
    python sim/kestirim.py korbolge
    python sim/kestirim.py cevrim
    python sim/kestirim.py hepsi
"""

import csv
import glob
import math
import os
import pickle
import sys

import numpy as np

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_KOK, "kopru", "gazebo_kaynak"))

from control.guidance.hedef_kestirim import (  # noqa: E402
    GorselKestirim, KamOlcum, KestirimCfg, ModelSabitHiz, ModelSabitDonus,
    ModelIMM, ModelPolinom, ModelOval, kesme_cozumu, menzil_vekilinden,
    piksel_los_seviye,
)

_BBOX_GLOB = os.path.join(_KOK, "kopru", "gazebo_kaynak", "logs",
                          "bbox_ibvs_*.csv")
_IZ_GLOB = os.path.join(_KOK, "veri", "hedef_iz", "hedef_iz_*.csv")
_CACHE = os.path.join(_KOK, "veri", "kestirim", "hizali.pkl")

# ── ölçülen kanal/araç sabitleri (bkz. görev brifingi + depo ölçümleri) ──
V_NOM = 18.0           # m/s  seyir
A_MAX = 12.0           # m/s² yanal ivme clamp (MAX_ACCEL)
YAW_TAVAN = 120.0      # °/s
YAW_GECIKME = 0.28     # s
DET_GECIKME = 0.22     # s   dedektör
KOR_MENZIL = 8.0       # m   bunun içinde tespit çöküyor
HEDEF_V = 17.99        # m/s


# ══════════════════════════════════════════════════════════ 1. YÜKLEME
def _iz_araliklari():
    """Her truth dosyası için (yol, t0, t1, tam_durumlu) — ucuz tarama."""
    out = []
    for f in sorted(glob.glob(_IZ_GLOB)):
        if os.path.getsize(f) < 5000:
            continue
        fh = open(f, encoding="utf-8", errors="replace")
        hdr = fh.readline().strip().split(",")
        if "t_mutlak" not in hdr:
            continue
        j = hdr.index("t_mutlak")
        first = fh.readline().split(",")
        fh.close()
        if len(first) <= j:
            continue
        with open(f, "rb") as b:
            b.seek(max(0, os.path.getsize(f) - 4000))
            tail = b.read().decode("utf-8", "replace").strip().split("\n")
        last = None
        for L in reversed(tail):
            p = L.split(",")
            if len(p) > j:
                try:
                    last = float(p[j])
                    break
                except ValueError:
                    pass
        try:
            t0 = float(first[j])
        except ValueError:
            continue
        if last is None or last <= t0:
            continue
        out.append((f, t0, last, "h_vx" in hdr))
    return out


def _iz_oku(f):
    """Truth dosyasını numpy sözlüğüne oku."""
    rows = list(csv.DictReader(open(f, encoding="utf-8", errors="replace")))
    if len(rows) < 10:
        return None
    d = {}
    for c in ("t_mutlak", "hx_m", "hy_m", "hz_m", "dx_m", "dy_m", "dz_m",
              "d_roll", "d_pitch", "d_yaw", "h_vx", "h_vy", "h_vz",
              "d_vx", "d_vy", "d_vz"):
        if c not in rows[0]:
            d[c] = None
            continue
        d[c] = np.array([float(r.get(c) or "nan") for r in rows])
    return d


def yukle(limit=None):
    """bbox kareleri + truth'u hizala, önbelleğe yaz."""
    izler = _iz_araliklari()
    print("truth dosya: %d" % len(izler))
    izcache = {}
    seg = []
    fs = sorted(glob.glob(_BBOX_GLOB))
    if limit:
        fs = fs[:limit]
    atlanan = 0
    for f in fs:
        try:
            rows = list(csv.DictReader(open(f, encoding="utf-8",
                                            errors="replace")))
        except Exception:
            continue
        if len(rows) < 12:
            continue
        try:
            t = np.array([float(r["t"]) for r in rows])
        except Exception:
            continue
        hedef_iz = None
        for path, a, b, tam in izler:
            if t[0] >= a - 2 and t[-1] <= b + 2:
                hedef_iz = path
                break
        if hedef_iz is None:
            atlanan += 1
            continue
        if hedef_iz not in izcache:
            izcache[hedef_iz] = _iz_oku(hedef_iz)
        iz = izcache[hedef_iz]
        if iz is None:
            continue

        def col(name):
            try:
                return np.array([float(r.get(name) or "nan") for r in rows])
            except Exception:
                return np.full(len(rows), np.nan)

        s = {
            "dosya": os.path.basename(f), "iz": os.path.basename(hedef_iz),
            "t": t, "cx": col("cx"), "cy": col("cy"),
            "w": col("w"), "h": col("h"), "boyut": col("boyut"),
            "conf": col("conf"),
            "roll": np.radians(col("iris_roll_deg")),
            "pitch": np.radians(col("iris_pitch_deg")),
            "yaw": np.radians(col("iris_yaw_deg")),
            "durum": np.array([r.get("durum", "") for r in rows]),
        }
        # truth'u bbox zamanlarına enterpole et (cevap anahtarı)
        tm = iz["t_mutlak"]
        for k_out, k_in in (("hx", "hx_m"), ("hy", "hy_m"), ("hz", "hz_m"),
                            ("dx", "dx_m"), ("dy", "dy_m"), ("dz", "dz_m"),
                            ("d_yaw", "d_yaw"), ("hvx", "h_vx"),
                            ("hvy", "h_vy"), ("hvz", "h_vz")):
            src = iz.get(k_in)
            s[k_out] = (np.interp(t, tm, src) if src is not None
                        and np.isfinite(src).any() else np.full(len(t), np.nan))
        # ── UZATILMIŞ TRUTH PENCERESİ ────────────────────────────────────
        # bbox dosyaları KISA (medyan 1.75 s). Cevabı yalnız dosyanın kendi
        # süresi içinde ararsak 2-3 s ufuk ÖLÇÜLEMEZ olur (örneklem 19 ve 4'e
        # düştü). Truth kaydı kesintisizdir; dosyanın SONUNDAN 4 s ötesine
        # kadar 20 Hz'lik bir cevap ızgarası saklanır.
        t_ext = np.arange(t[0], t[-1] + 4.0, 0.05)
        s["t_ext"] = t_ext
        for k_out, k_in in (("hx", "hx_m"), ("hy", "hy_m"), ("hz", "hz_m"),
                            ("dx", "dx_m"), ("dy", "dy_m"), ("dz", "dz_m")):
            src = iz.get(k_in)
            s[k_out + "_ext"] = (np.interp(t_ext, tm, src) if src is not None
                                 else np.full(len(t_ext), np.nan))
        # ── TRUTH → NED (dow_kopru.py:49-53) ──────────────────────────────
        # hedef_iz DoW (oyun) çerçevesinde yazılır; yasa NED'de çalışır:
        #     NED_x = DoW_x ,  NED_y = -DoW_y ,  NED_z = -DoW_z
        #     yaw_NED = -yaw_DoW      (iris_yaw_deg ZATEN NED'dir)
        # Bu çevrim YAPILMAZSA azimut yayılımı 2.7° yerine 28° çıkar ve tüm
        # kestirim ölçümü çöp olur. ÖLÇÜLDÜ ve doğrulandı (2026-08-17).
        for k in ("hy", "hz", "dy", "dz"):
            s[k] = -s[k]
            s[k + "_ext"] = -s[k + "_ext"]
        s["ned"] = True
        seg.append(s)
    os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
    pickle.dump(seg, open(_CACHE, "wb"))
    print("hizalanan segment: %d (truth'suz atlanan %d)  kare %d"
          % (len(seg), atlanan, sum(len(s["t"]) for s in seg)))
    return seg


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║ ⚠⚠ AYNA KESİMİ — BU NORMALLEŞTİRME OLMADAN HİÇBİR ÖLÇÜM GEÇERLİ DEĞİL     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
# Kamera aynası 2026-08-16 ~18:00-19:00 arasında düzeltildi (tespit_akisi.
# dow_pikseli_yasaya). ÖLÇÜLDÜ (4993 segment; her segmentte hangi hipotezin
# truth'a uyduğu ayrı ayrı sayıldı):
#     2026-08-15 17:00 → 2026-08-16 18:00   LOS azimut = yaw − eps_yaw (aynasız)
#     2026-08-16 19:00 → ...                LOS azimut = yaw + eps_yaw (aynalı)
# Yani depo İKİ AYNALANMIŞ DÜNYA barındırıyor. Hepsini birlikte kullanmak yatay
# geometriyi ortalayıp yok eder (yayılım 2.7° yerine 28° çıkar).
#
# ÇÖZÜM: ayna ÖNCESİ karelerin pikseli GÜNCEL çerçeveye çevrilir —
#     cx' = 2·CX − cx        (yatay ayna)
# Böylece tek ve GÜNCEL sözleşmeli (yaw + eps_yaw) bir külliyat kalır.
#
# ⚠ VERİ KALİTESİ ÖLÇÜMÜ (segment içi azimut artığının yayılımı):
#     ayna ÖNCESİ  : segmentlerin %92.1'i < 8°   (medyan 1.1°)  → TEMİZ
#     ayna SONRASI : segmentlerin %29.6'sı < 8°  (medyan 16.3°) → KİRLİ
# Ayna sonrası kayıtlar CANLI KAMPANYA'dan geliyor ve köprü/hayalet kare oranı
# yüksek (kutulu karelerin %67'sinde kopru=1). Bu yüzden aşağıdaki tutarlılık
# kapısı uygulanır: segmentin kendi içindeki azimut artığı 8°'yi aşarsa segment
# ATILIR. Kapı truth'u yalnız KAYDIN KENDİ TUTARLILIĞINI ölçmek için kullanır,
# kestirimciye hiçbir şey sızmaz.
AYNA_KESIM = "bbox_ibvs_20260816_1900"
KAPI_YAYILIM_DEG = 8.0


def _ayna_normalize(seg):
    """Ayna öncesi segmentlerin pikselini GÜNCEL çerçeveye çevir (tek külliyat)."""
    for s in seg:
        if s.get("ayna_norm"):
            continue
        if s["dosya"] < AYNA_KESIM:
            s["cx"] = 2.0 * KestirimCfg.CX - s["cx"]
        s["ayna_norm"] = True
    return seg


def azimut_artigi(s, azami=250):
    """Segmentin kendi içindeki LOS azimut artığının yayılımı (derece).

    Kaydın TUTARLILIK ölçüsüdür: piksel + kendi duruşumuz ile truth kerterizi
    aynı şeyi mi söylüyor? Sabit bir ofset (montaj/çerçeve) zararsızdır, o
    yüzden medyan çıkarılır; ölçülen YAYILIMdır."""
    m = _kutulu(s)
    idx = np.flatnonzero(m)[:azami]
    if len(idx) < 12:
        return None, None
    d = []
    for i in idx:
        azb, _ = piksel_los_seviye(s["cx"][i], s["cy"][i], s["roll"][i],
                                   s["pitch"][i])
        azt = math.atan2(s["hy"][i] - s["dy"][i], s["hx"][i] - s["dx"][i])
        d.append((s["yaw"][i] + azb - azt + math.pi) % (2 * math.pi) - math.pi)
    d = np.array(d)
    m0 = np.median(d)
    dd = (d - m0 + math.pi) % (2 * math.pi) - math.pi
    return math.degrees(np.median(np.abs(dd))), math.degrees(m0)


def cache(hepsi=False, kapi=True):
    """Hizalanmış segmentler — ayna normalleştirilmiş, tutarlılık kapılı."""
    if not os.path.exists(_CACHE):
        seg = yukle()
    else:
        seg = pickle.load(open(_CACHE, "rb"))
    seg = _ayna_normalize(seg)
    if hepsi:
        return seg
    if not kapi:
        return seg
    out = []
    for s in seg:
        y, _ = azimut_artigi(s)
        if y is not None and y < KAPI_YAYILIM_DEG:
            s["az_yayilim"] = y
            out.append(s)
    return out


def gecerli(s):
    """KARE GEÇERLİLİK FİLTRESİ — ⚠ BUNU ATLAMA.

    Telemetri boş geldiğinde (araç ölü / yeniden doğuyor / bağlantı kopuk)
    kayıt satırları donuk ya da sıfır değer taşır. Bu satırlar menzil
    kutulamasında SAHTE KORELASYON üretir: "yakın menzilde tespit çöküyor"
    bulgusu tam olarak böyle doğmuş ve çürütülmüştür (2026-08-17).
    Kural: hedef hızı 8-25 m/s bandında (sabit 17.99 m/s uçuyor) VE kendi
    hızımız > 0.5 m/s olmalı."""
    t = s["t"]
    if len(t) < 3:
        return np.zeros(len(t), dtype=bool)
    dt = np.maximum(np.diff(t, prepend=t[0] - 0.05), 1e-4)
    vh = np.hypot(np.diff(s["hx"], prepend=s["hx"][0]),
                  np.diff(s["hy"], prepend=s["hy"][0])) / dt
    vd = np.hypot(np.diff(s["dx"], prepend=s["dx"][0]),
                  np.diff(s["dy"], prepend=s["dy"][0])) / dt
    r = _menzil_truth(s)
    return (vh > 8) & (vh < 25) & (vd > 0.5) & np.isfinite(r)


def _kutulu(s):
    """Geçerli kutu maskesi (geçerlilik filtresi DAHİL)."""
    return (np.isfinite(s["boyut"]) & (s["boyut"] > 0)
            & np.isfinite(s["cx"]) & (s["cx"] > 0)
            & np.isfinite(s["roll"]) & np.isfinite(s["yaw"])
            & gecerli(s))


def _menzil_truth(s):
    return np.sqrt((s["hx"] - s["dx"]) ** 2 + (s["hy"] - s["dy"]) ** 2
                   + (s["hz"] - s["dz"]) ** 2)


def izler(s, gap_kare=6, min_n=8):
    """Kesintisiz kutulu koşuları indeks dizileri olarak ver."""
    ok = _kutulu(s)
    idx = np.flatnonzero(ok)
    if len(idx) < min_n:
        return []
    brk = np.flatnonzero(np.diff(idx) > gap_kare)
    return [g for g in np.split(idx, brk + 1) if len(g) >= min_n]


# ═══════════════════════════════════════════════════ 2. MENZİL MODELİ
def menzil(seg=None):
    """Kutu boyutu → menzil: vekilin yanlılığını truth'la ölç ve model uydur."""
    seg = seg or cache()
    B, R, W, H = [], [], [], []
    for s in seg:
        m = _kutulu(s)
        r = _menzil_truth(s)
        m &= np.isfinite(r) & (r > 0.5) & (r < 60)
        B.append(s["boyut"][m]); R.append(r[m])
        W.append(s["w"][m]); H.append(s["h"][m])
    B = np.concatenate(B); R = np.concatenate(R)
    W = np.concatenate(W); H = np.concatenate(H)
    print("=" * 72)
    print("MENZİL VEKİLİ — %d tespitli kare, truth eşlemeli" % len(B))
    print("=" * 72)
    print("\n  boyut×R (px·m) menzil dilimlerinde  [kodda sabit 202.6]")
    print("  %-12s %6s %8s %8s %8s" % ("menzil", "n", "medyan", "p25", "p75"))
    kenar = [0, 5, 8, 12, 16, 22, 30, 60]
    for a, b in zip(kenar[:-1], kenar[1:]):
        m = (R >= a) & (R < b)
        if m.sum() < 30:
            continue
        k = B[m] * R[m]
        print("  %5.0f-%-6.0f %6d %8.1f %8.1f %8.1f"
              % (a, b, m.sum(), np.median(k), np.percentile(k, 25),
                 np.percentile(k, 75)))

    # ── model 1: sabit  R = K/boyut
    def hata(Rk):
        e = Rk - R
        return (np.median(np.abs(e)), np.median(e))
    K0 = 202.6
    e0 = hata(K0 / B)
    # ── model 2: R = a/(boyut - b)  (yanlılığın menzille değişmesini yakalar)
    from scipy.optimize import least_squares  # noqa
    def rez(p):
        return p[0] / np.maximum(B - p[1], 0.4) - R
    try:
        sol = least_squares(rez, [150.0, 2.0], loss="soft_l1", f_scale=2.0)
        a, b = sol.x
    except Exception:
        a, b = K0, 0.0
    e2 = hata(a / np.maximum(B - b, 0.4))
    # ── model 3: R = c / (w^p * h^q)   (menzil_model.py fikri)
    A = np.column_stack([np.ones(len(B)), -np.log(np.maximum(W, 1)),
                         -np.log(np.maximum(H, 1))])
    coef, *_ = np.linalg.lstsq(A, np.log(R), rcond=None)
    R3 = np.exp(A @ coef)
    e3 = hata(R3)
    print("\n  MODEL                              |hata| medyan   yanlılık")
    print("  R = 202.6/boyut  (kodda)            %8.2f m   %+8.2f m" % e0)
    print("  R = %6.1f/(boyut-%.2f)             %8.2f m   %+8.2f m"
          % (a, b, e2[0], e2[1]))
    print("  R = %.1f/(w^%.2f·h^%.2f)          %8.2f m   %+8.2f m"
          % (math.exp(coef[0]), coef[1], coef[2], e3[0], e3[1]))
    print("\n  → hedef_kestirim.KestirimCfg.MENZIL_A/MENZIL_B için: %.1f / %.2f"
          % (a, b))
    return dict(a=float(a), b=float(b), K0=K0)


# ═══════════════════════════════════════════════════════ 3. KÖR TEST
_MODELLER = {
    "sabit_hiz": ModelSabitHiz,
    "sabit_donus": ModelSabitDonus,
    "imm": ModelIMM,
    "polinom": ModelPolinom,
    "oval": ModelOval,
}
UFUKLAR = (0.5, 1.0, 2.0, 3.0)


def cfg_fx():
    """Odak uzaklığı (px) — metre hatasını piksele çevirmek için."""
    return KestirimCfg.FX


def _kare_uret(s, i):
    """Tek karenin KAMERA sözleşmeli girdisi. Truth BURAYA GİRMEZ."""
    return KamOlcum(t=float(s["t"][i]), cx=float(s["cx"][i]),
                    cy=float(s["cy"][i]), w=float(s["w"][i]),
                    h=float(s["h"][i]), conf=float(s["conf"][i]),
                    roll=float(s["roll"][i]), pitch=float(s["pitch"][i]),
                    yaw=float(s["yaw"][i]),
                    px=float(s["dx"][i]), py=float(s["dy"][i]),
                    pz=float(s["dz"][i]))


def kor(seg=None, modeller=None, min_gecmis=0.6, ayrintili=True, adim=3,
        azami_iz=None):
    """KÖR TEST: t'ye kadarki KAMERA verisiyle t+ufuk'taki hedef konumu kestir,
    truth'la kıyasla. Kestirimci truth'u ASLA görmez.

    adim: tahmin başlangıçlarını her `adim` karede bir örnekle (ölçüm 21 Hz;
          komşu kareler zaten neredeyse aynı bilgi — istatistiği bozmaz)."""
    seg = seg or cache()
    modeller = modeller or list(_MODELLER)
    def _bos():
        return {u: {"m": [], "px": [], "los": [], "R": []} for u in UFUKLAR}
    sonuc = {m: _bos() for m in modeller}
    # OLUMSUZ KONTROL = SAF TAKİP: hedefin BULUNDUĞU yere nişan al (kestirim
    # yok). Öngörülü nişan bunu yenemiyorsa yapılan iş zararlıdır.
    sonuc["saf_takip"] = _bos()
    n_iz = 0
    for s in seg:
        r_t = _menzil_truth(s)
        for g in izler(s):
            if s["t"][g[-1]] - s["t"][g[0]] < min_gecmis + 0.5:
                continue
            n_iz += 1
            if azami_iz and n_iz > azami_iz:
                break
            t = s["t"]
            for mad in list(modeller) + ["saf_takip"]:
                est = (GorselKestirim(_MODELLER[mad]())
                       if mad in _MODELLER else None)
                for k, i in enumerate(g):
                    if est is not None:
                        est.olcum(_kare_uret(s, i))
                    if t[i] - t[g[0]] < min_gecmis or (k % adim):
                        continue
                    for u in UFUKLAR:
                        gt = _gelecek_truth(s, i, u)
                        if gt is None:
                            continue
                        gercek, R, biz = gt
                        if mad == "saf_takip":
                            p = np.array([s["hx"][i], s["hy"][i], s["hz"][i]])
                        else:
                            d = est.tahmin(u)
                            if d is None:
                                continue
                            p = np.array(d["p"])
                        e_perp, e_los, aci = _nisan_hatasi(p, gercek, biz)
                        if e_perp is None:
                            continue
                        sonuc[mad][u]["m"].append(e_perp)
                        sonuc[mad][u]["los"].append(e_los)
                        sonuc[mad][u]["px"].append(aci * cfg_fx())
                        sonuc[mad][u]["R"].append(R)
    if ayrintili:
        print("=" * 78)
        print("KÖR KESTİRİM TESTİ — %d iz, girdi YALNIZ kamera+kendi durum"
              % n_iz)
        print("=" * 78)
        print("NISAN HATASI = LOS'a DIK bilesen (menzil hatasi nisani bozmaz)")
        print("%-14s %5s %7s %8s %8s %8s %8s %8s"
              % ("model", "ufuk", "n", "p50 m", "p90 m", "p50 px", "p90 px",
                 "p50 deg"))
        for mad in list(modeller) + ["saf_takip"]:
            for u in UFUKLAR:
                d = sonuc[mad][u]
                if len(d["m"]) < 20:
                    print("%-14s %5.1f %7d %8s" % (mad, u, len(d["m"]), "-"))
                    continue
                a = np.array(d["m"]); px = np.array(d["px"])
                print("%-14s %5.1f %7d %8.2f %8.2f %8.1f %8.1f %8.2f"
                      % (mad, u, len(a), np.percentile(a, 50),
                         np.percentile(a, 90), np.percentile(px, 50),
                         np.percentile(px, 90),
                         math.degrees(np.percentile(px, 50) / cfg_fx())))
            print()
        r0 = sonuc["saf_takip"][UFUKLAR[0]]["R"]
        if r0:
            print("  ornek menzil dagilimi p25/p50/p75: %.1f / %.1f / %.1f m"
                  % tuple(np.percentile(r0, q) for q in (25, 50, 75)))
    return sonuc


def _nisan_hatasi(p_kestirim, p_gercek, p_biz):
    """NİŞAN HATASI = kestirim hatasının LOS'a DİK bileşeni.

    ⚠ METODOLOJİK ÇEKİRDEK. Ham |p_kestirim − p_gerçek| YANLIŞ ölçüttür: menzil
    vekilinin hatası (medyan 3.4 m, uzakta 14 m) nişan noktasını GÖRÜŞ HATTI
    BOYUNCA kaydırır ve NEREYE BAKTIĞIMIZI DEĞİŞTİRMEZ. Nişanı bozan yalnız
    DİK bileşendir. Ham norm kullanılırsa bütün modeller menzil gürültüsünün
    altında kalır ve kıyas anlamsızlaşır (ölçüldü: ham norm p50 19 m, bunun
    9.3 m'si salt menzil).

    Dönüş: (dik_hata_m, los_hatasi_m, açısal_hata_rad)
    """
    d_ger = np.asarray(p_gercek) - np.asarray(p_biz)
    R = float(np.linalg.norm(d_ger))
    if R < 0.5:
        return None, None, None
    u = d_ger / R
    e = np.asarray(p_kestirim) - np.asarray(p_gercek)
    e_los = float(e @ u)
    e_perp = float(np.linalg.norm(e - e_los * u))
    return e_perp, abs(e_los), math.atan2(e_perp, R)


def _gelecek_truth(s, i, ufuk, tol=0.06):
    """t[i]+ufuk anındaki GERÇEK hedef konumu (cevap anahtarı).

    ⚠ Bu arama izin (g) İÇİNDE sınırlanmaz. Sınırlansaydı yalnız o anda hâlâ
    TESPİT EDİLEN kareler sayılırdı ve ufuk büyüdükçe örneklem çökerdi (1 s'de
    sıfıra iniyordu) — üstelik "tespit sürdüyse" koşulu örneklemi kolay
    angajmanlara doğru YANLI hale getirirdi. Truth kesintisiz kayıttır; kutu
    olsun olmasın her ana bakılabilir. Kestirimci yine yalnız izdeki kutuları
    görür; değişen tek şey CEVABIN nereden okunduğudur.
    """
    t = s.get("t_ext")
    if t is None:                     # eski önbellek — dosya süresiyle sınırlı
        t = s["t"]
        ek = ""
    else:
        ek = "_ext"
    hedef = s["t"][i] + ufuk
    if hedef > t[-1] + tol:
        return None
    j = int(np.searchsorted(t, hedef))
    if j <= 0:
        return None
    if j >= len(t):
        if abs(t[-1] - hedef) > tol:
            return None
        j = len(t) - 1
        w = 0.0
    else:
        dt = t[j] - t[j - 1]
        w = (hedef - t[j - 1]) / dt if dt > 1e-9 else 0.0

    def _ip(k):
        a = s[k + ek]
        return a[j - 1] + w * (a[j] - a[j - 1])
    p = np.array([_ip("hx"), _ip("hy"), _ip("hz")])
    biz = np.array([_ip("dx"), _ip("dy"), _ip("dz")])
    if not (np.isfinite(p).all() and np.isfinite(biz).all()):
        return None
    return p, float(np.linalg.norm(p - biz)), biz


# ═══════════════════════════════════════════════ 4. KESME FİZİBİLİTESİ
def aspect_dagilimi(seg=None):
    """Gerçek angajmanlarda hedefin aspect (kuyruk) açısı dağılımı.

    Kesme fizibilitesi TAMAMEN buna bağlı: 37.7°'lik öngörü açısı yandan
    görülen hedef içindir. Kuyrukta gereken açı çok daha küçüktür."""
    seg = seg or cache()
    ASP, R = [], []
    for s in seg:
        m = _kutulu(s)
        if m.sum() < 5:
            continue
        t = s["t"]
        dt = np.maximum(np.diff(t, prepend=t[0] - 0.05), 1e-4)
        hvx = np.diff(s["hx"], prepend=s["hx"][0]) / dt
        hvy = np.diff(s["hy"], prepend=s["hy"][0]) / dt
        lx, ly = s["dx"] - s["hx"], s["dy"] - s["hy"]
        ln, hn = np.hypot(lx, ly), np.hypot(hvx, hvy)
        ok = m & (ln > 0.5) & (hn > 5)
        cosa = (hvx * lx + hvy * ly) / np.maximum(ln * hn, 1e-6)
        ASP.append(np.degrees(np.arccos(np.clip(cosa, -1, 1)))[ok])
        R.append(_menzil_truth(s)[ok])
    ASP = np.concatenate(ASP); R = np.concatenate(R)
    print("\n  ÖLÇÜLEN ASPECT DAĞILIMI (%d tespitli kare)" % len(ASP))
    print("  p5 %.0f°  p10 %.0f°  p25 %.0f°  p50 %.0f°  p75 %.0f°  p90 %.0f°"
          % tuple(np.percentile(ASP, p) for p in (5, 10, 25, 50, 75, 90)))
    print("  kuyruk (>150°) %%%.0f | yandan (90-150°) %%%.0f | önden (<90°) %%%.0f"
          % (100 * (ASP > 150).mean(), 100 * ((ASP >= 90) & (ASP <= 150)).mean(),
             100 * (ASP < 90).mean()))
    print("  → 37.7°'lik öngörü açısı aspect≈133°'e karşılık gelir; ölçülen"
          " dağılımın yalnız %%%.0f'i orada veya daha yandan."
          % (100 * (ASP < 135).mean()))
    return ASP, R


def _kapanma(V_b, V_h, aspect_deg, sigma_deg):
    """ṙ (negatif = kapanıyor).  ṙ = −V_h·cos(aspect) − V_b·cos(σ)."""
    return (-V_h * math.cos(math.radians(aspect_deg))
            - V_b * math.cos(math.radians(sigma_deg)))


def kesme(seg=None, ayrintili=True):
    """sin σ = μ·sin(aspect) — hangi aspect/menzilde kesme mümkün?
    Yavaşlamayla birleşimi: V düşünce μ artar AMA dönüş tavanı da artar."""
    print("=" * 78)
    print("KESME NOKTASI FİZİBİLİTESİ  (hedef %.2f m/s sabit oval)" % HEDEF_V)
    print("=" * 78)
    try:
        aspect_dagilimi(seg)
    except Exception as e:
        print("  aspect dağılımı ÖLÇÜLEMEDİ: %s" % e)
    print("\n  sin σ = μ·sin(aspect),  μ = V_hedef/V_biz")
    print("  σ = gereken öngörü (lead) açısı; aspect = hedefin kuyruk açısı")
    print("  (aspect 180° = tam kuyruk, 90° = borda)\n")
    print("  %-8s" % "V_biz", end="")
    aspects = [30, 60, 90, 120, 150, 165, 180]
    for a in aspects:
        print("%8d°" % a, end="")
    print("   μ")
    for V in (12, 14, 15, 16, 18, 20, 22, 25):
        mu = HEDEF_V / V
        print("  %-8.0f" % V, end="")
        for a in aspects:
            s = mu * math.sin(math.radians(a))
            if abs(s) > 1.0:
                print("%9s" % "YOK", end="")
            else:
                print("%8.1f°" % math.degrees(math.asin(s)), end="")
        print("   %.3f" % mu)

    print("\n  ── ULAŞILABİLİR ÖNGÖRÜ AÇISI (dönüş tavanı × süre) ──")
    print("  ω_max = a_max/V  (quadrotor: a_max=%.0f m/s² sabit clamp)" % A_MAX)
    print("  Seyirde kullanılabilen: yaw kanal tavanı %.0f °/s ile min\n"
          % YAW_TAVAN)
    print("  %-8s %10s %10s %12s %12s" % ("V_biz", "ω_max °/s", "R_dön m",
                                          "σ@1.0s", "σ@2.0s"))
    for V in (12, 14, 15, 16, 18, 20, 22):
        w = min(math.degrees(A_MAX / V), YAW_TAVAN)
        Rd = V * V / A_MAX
        print("  %-8.0f %10.1f %10.1f %12.1f° %12.1f°"
              % (V, w, Rd, w * 1.0, w * 2.0))

    print("\n  ══ ASIL BAĞLAYAN KISIT: KAPANMA HIZI ══")
    print("  Doğru öngörü açısıyla uçarken:  ṙ = −V_h·cos(aspect) − V_b·cos(σ)")
    print("  (ṙ<0 kapanıyor).  ⚠ μ=1'de (eşit hız) kesme geometrisi KAPANMAZ:")
    print("  sabit kerterizli kesme, hız üstünlüğü yoksa menzili sabit tutar.")
    print("\n  %-6s %-7s %8s %10s %11s %10s"
          % ("V_biz", "aspect", "σ_ger", "ṙ (m/s)", "15m→temas", "faz(4.8s)?"))
    for V in (15, 18, 20, 22, 25):
        mu = HEDEF_V / V
        for a in (120, 150, 163, 175):
            s = mu * math.sin(math.radians(a))
            if abs(s) > 1:
                print("  %-6.0f %-7d %8s" % (V, a, "GEOM.YOK"))
                continue
            sig = math.degrees(math.asin(s))
            rd = _kapanma(V, HEDEF_V, a, sig)
            if rd >= -0.05:
                print("  %-6.0f %-7d %7.1f° %10.2f %11s %10s"
                      % (V, a, sig, rd, "ASLA", "HAYIR"))
                continue
            tt = 15.0 / (-rd)
            print("  %-6.0f %-7d %7.1f° %10.2f %10.1fs %10s"
                  % (V, a, sig, rd, tt, "EVET" if tt <= 4.8 else "HAYIR"))

    print("\n  ══ YAVAŞLAMANIN İKİ YÜZÜ ══")
    print("  (+) ω_max = a/V büyür → daha sert dönüş, köşe kesme imkânı")
    print("  (−) kapanma ÖLÜR → kuyrukta menzil açılır, temas hiç olmaz")
    print("\n  %-6s %9s %10s %12s %12s"
          % ("V_biz", "ω_max °/s", "R_dön m", "ṙ@aspect163", "15m→temas"))
    for V in (14, 15, 16, 18, 20, 22, 25):
        mu = HEDEF_V / V
        s = mu * math.sin(math.radians(163))
        sig = math.degrees(math.asin(s)) if abs(s) <= 1 else float("nan")
        rd = _kapanma(V, HEDEF_V, 163, sig)
        w = min(math.degrees(A_MAX / V), YAW_TAVAN)
        tt = ("%.1fs" % (15.0 / -rd)) if rd < -0.05 else "ASLA"
        print("  %-6.0f %9.1f %10.1f %12.2f %12s"
              % (V, w, V * V / A_MAX, rd, tt))
    print("\n  → YAVAŞLAMA KUYRUKTA ZARARLI. Yalnız hedef DÖNERKEN, kordonu")
    print("    kesmek için geçici olarak anlamlı (aşağıdaki kazanç).")

    print("\n  ══ KÖŞE KESME KAZANCI (hedefin dönüşünü kısa yoldan kesmek) ══")
    print("  Hedef R=48 m yayda θ dönerken: yay = R·θ, kiriş = 2R·sin(θ/2)")
    print("\n  %-8s %10s %10s %10s %12s"
          % ("θ (°)", "yay m", "kiriş m", "kazanç m", "kazanç/ṙ=2"))
    for th in (30, 45, 60, 90, 120, 180):
        r = math.radians(th)
        yay, kiris = 48.0 * r, 2 * 48.0 * math.sin(r / 2)
        print("  %-8d %10.1f %10.1f %10.1f %11.1fs"
              % (th, yay, kiris, yay - kiris, (yay - kiris) / 2.0))
    print("\n  → 90°'lik dönüşte 7.5 m kazanç; ṙ≈2 m/s'de bu 3.8 s'lik kovalama")
    print("    demektir — görsel fazın TAMAMI kadar. Öngörünün asıl değeri bu.")
    return None


# ═══════════════════════════════════════════════════ 5. KÖR BÖLGE BÜTÇESİ
def korbolge(seg=None, kestirim_hata=None):
    """Açık çevrim bütçesi: son geçerli ölçümden temasa ne kadar hata birikir?

    ⚠ ÖNCE KÖRLÜĞÜ ÖLÇ, VARSAYMA. "8 m'nin içinde tespit çöküyor" bulgusu
    ÇÜRÜTÜLDÜ (geçersiz telemetri satırları 0 m kutusuna düşüyordu). Burada
    tespit oranı geçerlilik filtresiyle YENİDEN ölçülür."""
    seg = seg or cache()
    print("=" * 78)
    print("AÇIK ÇEVRİM BÜTÇESİ — son geçerli ölçümden temasa")
    print("=" * 78)
    # ── 0) KÖRLÜK VAR MI? menzile göre tespit oranı (geçerlilik filtreli) ──
    R, OK = [], []
    for s in seg:
        g = gecerli(s)
        if g.sum() < 3:
            continue
        R.append(_menzil_truth(s)[g])
        OK.append(_kutulu(s)[g])
    R = np.concatenate(R); OK = np.concatenate(OK)
    print("\n  TESPİT ORANI × MENZİL (%d geçerli kare)" % len(R))
    print("  %-12s %9s %10s" % ("menzil", "n", "tespit%"))
    for a, b in ((0, 2), (2, 3), (3, 5), (5, 8), (8, 12), (12, 20),
                 (20, 30), (30, 50)):
        m = (R >= a) & (R < b)
        if m.sum() < 100:
            continue
        print("  %4.0f-%-7.0f %9d %9.1f%%" % (a, b, m.sum(), 100 * OK[m].mean()))
    yakin = OK[(R >= 0.5) & (R < 8)]
    uzak = OK[(R >= 20) & (R < 50)]
    print("\n  → 0.5-8 m tespit %%%.1f  vs  20-50 m tespit %%%.1f"
          % (100 * yakin.mean(), 100 * uzak.mean()))
    print("  → YAKIN MENZİLDE KÖRLÜK %s"
          % ("YOK (tespit yakında DAHA İYİ)" if yakin.mean() > uzak.mean()
             else "VAR"))
    # 1) gerçek verilerde: son kutulu kareden CPA'ya kadar geçen süre/mesafe
    sureler, menziller, cpa = [], [], []
    for s in seg:
        r = _menzil_truth(s)
        ok = _kutulu(s) & np.isfinite(r)
        if ok.sum() < 5 or not np.isfinite(r).any():
            continue
        rmin = np.nanmin(r)
        if rmin > 12:
            continue
        jmin = int(np.nanargmin(r))
        son = np.flatnonzero(ok[:jmin + 1])
        if len(son) == 0:
            continue
        i = son[-1]
        if not (np.isfinite(r[i]) and r[i] > 0):
            continue
        sureler.append(float(s["t"][jmin] - s["t"][i]))
        menziller.append(float(r[i]))
        cpa.append(float(rmin))
    if len(sureler) < 10:
        print("  YETERSİZ VERİ (n=%d) — ÖLÇÜLMEDİ" % len(sureler))
        return None
    su = np.array(sureler); mz = np.array(menziller); cp = np.array(cpa)
    print("\n  Gerçek kayıtlarda (n=%d angajman, CPA<12 m):" % len(su))
    for ad, a, br in (("son kutulu karedeki menzil", mz, "m"),
                      ("son kutudan CPA'ya süre", su, "s"),
                      ("CPA (en yakın mesafe)", cp, "m")):
        print("    %-28s p10 %6.2f  p50 %6.2f  p90 %6.2f %s"
              % (ad, np.percentile(a, 10), np.percentile(a, 50),
                 np.percentile(a, 90), br))
    t_kor = float(np.percentile(su, 50))
    print("\n  → KÖR SÜRE (medyan) = %.2f s" % t_kor)

    # ── ASIL AÇIK ÇEVRİM: KÖRLÜK DEĞİL, KANAL GECİKMESİ ──────────────────
    # Kör süre ~0 çıktı: hedefi temasa kadar görüyoruz. Yine de yasa GEÇMİŞE
    # nişan alıyor, çünkü komut τ = dedektör + yaw kadar GEÇ uygulanıyor.
    # τ boyunca hedefin LOS'a DİK göreli hızı kadar yanal hata birikir:
    #     e_yanal ≈ v_dik · τ ,   v_dik = V_hedef · sin(180° − aspect)
    tau = DET_GECIKME + YAW_GECIKME
    print("\n  ══ ASIL AÇIK ÇEVRİM PENCERESİ: KANAL GECİKMESİ ══")
    print("  Kör süre ~0 s (hedef temasa kadar görülüyor). Buna rağmen komut")
    print("  τ = %.2f + %.2f = %.2f s GEÇ uygulanıyor; yasa hedefin τ ÖNCEKİ"
          % (DET_GECIKME, YAW_GECIKME, tau))
    print("  yerine nişan alıyor. Biriken YANAL hata:")
    print("\n  %-14s %12s %14s %14s"
          % ("aspect", "v_dik (m/s)", "gecikme ıskası", "kestirim(0.5s)"))
    kh = kestirim_hata if kestirim_hata is not None else {}
    e_kes = _interp_hata(kh, tau)
    for a in (120, 150, 163, 175):
        vd = HEDEF_V * math.sin(math.radians(180 - a))
        print("  %-14d %12.2f %13.2f m %13.2f m"
              % (a, vd, vd * tau, e_kes))
    vd163 = HEDEF_V * math.sin(math.radians(17.0))
    print("\n  → ÖLÇÜLEN aspect medyanı 163°'te gecikme ıskası %.2f m."
          % (vd163 * tau))
    print("    ÖNGÖRÜLÜ NİŞANIN İLK KAZANCI BU: τ kadar ileri tahmin etmek")
    print("    bu hatayı sıfırlar ve yerine %.2f m'lik kestirim hatası koyar."
          % e_kes)
    print("    Net kazanç %.2f m — daha lead pursuit'e hiç girmeden."
          % (vd163 * tau - e_kes))

    print("\n  ══ ÖLÇÜLEN KESTİRİM HATASI × UFUK (kör test, LOS'a dik p50) ══")
    for u in sorted(kh):
        print("    %.1f s → %5.2f m" % (u, kh[u]))
    print("  Kestirim hatası, ufuk 1 s'e kadar gecikme ıskasının ALTINDA;")
    print("  2 s'ten sonra üstüne çıkıyor → KULLANILABİLİR UFUK ≈ 1 s.")
    return dict(t_kor=t_kor, tau=tau, gecikme_iskasi=vd163 * tau,
                kestirim=e_kes)


def _interp_hata(kh, T):
    if not kh:
        return 3.0
    ks = sorted(kh)
    return float(np.interp(T, ks, [kh[k] for k in ks]))


# ═══════════════════════════════════════════ 6. KAPALI ÇEVRİM BENZETİMİ
# Hedef: ÖLÇÜLEN oval pist (220×96 m, tur 531 m, 17.99 m/s, saat yönü tersine).
# Kanal: ölçülen gecikme (dedektör 0.22 s + yaw 0.28 s), ivme clamp 12 m/s²,
#        yaw hız tavanı 120 °/s.
# Başlangıç geometrisi ÖLÇÜLEN dağılımdan: aspect ~163° (kuyruk), menzil 10-25 m.


def _oval_konum(s_m):
    """220×96 m oval pistte yay uzunluğuna göre konum + teğet (saat yönü tersi).
    İki düz kısım + iki yarım daire; tur 531 m, yarıçap 48 m."""
    R = 48.0
    L = (531.0 - 2 * math.pi * R) / 2.0
    s = s_m % 531.0
    if s < L:
        return np.array([s, 0.0]), np.array([1.0, 0.0])
    s -= L
    if s < math.pi * R:
        a = s / R
        return (np.array([L + R * math.sin(a), R * (1 - math.cos(a))]),
                np.array([math.cos(a), math.sin(a)]))
    s -= math.pi * R
    if s < L:
        return np.array([L - s, 2 * R]), np.array([-1.0, 0.0])
    s -= L
    a = s / R
    return (np.array([-R * math.sin(a), 2 * R - R * (1 - math.cos(a))]),
            np.array([-math.cos(a), -math.sin(a)]))


def _donus_hizi(s_m):
    """Oval pistin o noktadaki dönüş hızı (rad/s). Düzde 0, virajda V/R."""
    R = 48.0
    L = (531.0 - 2 * math.pi * R) / 2.0
    s = s_m % 531.0
    if s < L or (L + math.pi * R) <= s < (2 * L + math.pi * R):
        return 0.0
    return HEDEF_V / R


def _tek_kosu(rng, ongoru, hata_std, V_biz=19.8, dt=0.05, T=6.0,
              yalniz_donus=False):
    """Tek angajman. ongoru=False → SAF TAKİP (hedefin BULUNDUĞU yer).
    ongoru=True → kesme noktası (hedefin GİDECEĞİ yer), kestirim hatası
    hata_std (m, LOS'a dik) ile bozulmuş.

    Dönüş: CPA (en yakın yaklaşma mesafesi, m).
    """
    # ── başlangıç: hedefin arkasında, ölçülen aspect/menzil bandında ──
    if yalniz_donus:                      # yalnız viraj segmentinden başla
        L = (531.0 - 2 * math.pi * 48.0) / 2.0
        s0 = rng.uniform(L, L + math.pi * 48.0)
    else:
        s0 = rng.uniform(0, 531)
    ph, th = _oval_konum(s0)
    r0 = rng.uniform(10.0, 25.0)
    # aspect: ölçülen dağılım ~ N(163°, 15°), kuyruk ağırlıklı
    asp = math.radians(min(179.0, max(90.0, rng.normal(163.0, 15.0))))
    # hedeften bize giden yön: hedefin hız vektöründen aspect kadar döndür
    yan = 1.0 if rng.random() < 0.5 else -1.0
    ca, sa = math.cos(asp), yan * math.sin(asp)
    u_ht = np.array([th[0] * ca - th[1] * sa, th[0] * sa + th[1] * ca])
    pb = ph + r0 * u_ht
    # başlangıç hızımız hedefe doğru
    yon = ph - pb
    vb = yon / max(np.linalg.norm(yon), 1e-9) * V_biz

    s = s0
    en_yakin = float(np.linalg.norm(ph - pb))
    kuyruk = []
    gk = int(round((DET_GECIKME + YAW_GECIKME) / dt))
    for _ in range(int(T / dt)):
        s += HEDEF_V * dt
        ph, th = _oval_konum(s)
        vh = th * HEDEF_V
        # ── nişan noktası ──
        if not ongoru:
            nisan = ph.copy()
        else:
            rvec = ph - pb
            R = np.linalg.norm(rvec)
            kap = -float((vh - vb) @ (rvec / max(R, 1e-9)))   # kapanma (+)
            tgo = min(R / kap, 3.0) if kap > 0.3 else 3.0
            # ⚠ SABİT HIZ (CV) ile ileri taşı — dönüş hızı KULLANILMAZ.
            # İki sebep:
            #  1) DÜRÜSTLÜK: hedefin gerçek dönüş hızını okumak benzetime truth
            #     sızdırırdı; gerçek yasada elimizde yalnız kestirim var.
            #  2) ÖLÇÜM: kör testte sabit dönüş (CT) sabit hızdan (CV) DAHA
            #     KÖTÜ çıktı (1.0 s'de 4.48 m vs 3.31 m). Ovalin viraj
            #     parçaları ufka göre kısa; "dönüş sürecek" bahsi kaybediyor.
            dp = vh * tgo
            nisan = ph + dp
            if hata_std > 0:              # kestirim hatası: LOS'a DİK
                u = rvec / max(R, 1e-9)
                perp = np.array([-u[1], u[0]])
                nisan = nisan + perp * rng.normal(0, hata_std)
        # ── kanal: gecikme ──
        kuyruk.append(nisan)
        nis = kuyruk[max(0, len(kuyruk) - 1 - gk)]
        istek = nis - pb
        nrm = np.linalg.norm(istek)
        if nrm < 1e-9:
            break
        istek = istek / nrm * V_biz
        dv = istek - vb
        if np.linalg.norm(dv) > A_MAX * dt:
            dv = dv / np.linalg.norm(dv) * A_MAX * dt
        vb_yeni = vb + dv
        a1 = math.atan2(vb[1], vb[0])
        a2 = math.atan2(vb_yeni[1], vb_yeni[0])
        d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        lim = math.radians(YAW_TAVAN) * dt
        if abs(d) > lim:
            a2 = a1 + math.copysign(lim, d)
            vb_yeni = np.array([math.cos(a2), math.sin(a2)]) * V_biz
        vb = vb_yeni / max(np.linalg.norm(vb_yeni), 1e-9) * V_biz
        pb = pb + vb * dt
        en_yakin = min(en_yakin, float(np.linalg.norm(ph - pb)))
    return en_yakin


def cevrim(n=600, tohum=7, ayrintili=True, V_biz=19.8, kestirim_hata=None):
    """Saf takip vs öngörülü nişan — ıska dağılımı ve DEVRİLME NOKTASI.

    Devrilme noktası: kestirim hatası hangi seviyede öngörülü nişan saf
    takipten KÖTÜ hale gelir? Reçetenin olumsuz kontrolü budur."""
    print("=" * 78)
    print("KAPALI ÇEVRİM — saf takip vs öngörülü nişan (%d koşu, V_biz=%.1f)"
          % (n, V_biz))
    print("=" * 78)
    print("  kanal: dedektör %.2fs + yaw %.2fs gecikme, ivme %.0f m/s²,"
          " yaw tavan %.0f °/s" % (DET_GECIKME, YAW_GECIKME, A_MAX, YAW_TAVAN))

    def kos(ongoru, sig, yalniz_donus=False, V=V_biz):
        rng = np.random.default_rng(tohum)
        return np.array([_tek_kosu(rng, ongoru, sig, V_biz=V,
                                   yalniz_donus=yalniz_donus)
                         for _ in range(n)])

    def yaz(ad, a, taban=None):
        ek = ""
        if taban is not None:
            d = np.percentile(a, 50) - np.percentile(taban, 50)
            ek = "  (saf takibe göre %+.2f m)" % d
        print("  %-22s CPA p50 %6.2f  p90 %6.2f  <2m %%%-5.0f%s"
              % (ad, np.percentile(a, 50), np.percentile(a, 90),
                 100 * (a < 2.0).mean(), ek))

    print("\n  ── TÜM PİST ──")
    taban = kos(False, 0.0)
    yaz("saf takip", taban)
    sonuc = {"saf": taban}
    for sig in (0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0):
        a = kos(True, sig)
        sonuc[sig] = a
        yaz("öngörülü σ=%.0f m" % sig, a, taban)
    # devrilme noktası
    t50 = np.percentile(taban, 50)
    devril = None
    for sig in sorted(k for k in sonuc if k != "saf"):
        if np.percentile(sonuc[sig], 50) > t50:
            devril = sig
            break
    print("\n  → DEVRİLME NOKTASI: kestirim hatası σ ≈ %s m'de öngörülü nişan"
          % ("%.0f" % devril if devril is not None else ">12"))
    print("    saf takipten KÖTÜ hale geliyor.")

    print("\n  ── YALNIZ VİRAJ SEGMENTİ (öngörünün asıl hedefi) ──")
    tabanv = kos(False, 0.0, yalniz_donus=True)
    yaz("saf takip (viraj)", tabanv)
    for sig in (0.0, 2.0, 4.0, 8.0):
        yaz("öngörülü σ=%.0f m (viraj)" % sig,
            kos(True, sig, yalniz_donus=True), tabanv)

    print("\n  ── HIZ ZARFI: kapanma olmadan öngörü de kurtarmaz ──")
    for V in (18.0, 20.0, 22.0, 25.0):
        a0 = kos(False, 0.0, V=V)
        a1 = kos(True, 2.0, V=V)
        print("  V_biz=%4.1f  saf CPA p50 %6.2f  |  öngörülü(σ=2) %6.2f"
              "  |  vuruş %%%.0f → %%%.0f"
              % (V, np.percentile(a0, 50), np.percentile(a1, 50),
                 100 * (a0 < 2).mean(), 100 * (a1 < 2).mean()))
    return sonuc


# ══════════════════════════════════════════════════════════════ ANA
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if cmd == "yukle":
        yukle()
    elif cmd == "menzil":
        menzil()
    elif cmd == "kor":
        kor()
    elif cmd == "kesme":
        kesme()
    elif cmd == "korbolge":
        korbolge()
    elif cmd == "cevrim":
        cevrim()
    else:
        seg = cache()
        menzil(seg)
        k = kor(seg)
        kesme(seg)
        # kanal bütçesinde KAZANAN modelin hatası kullanılır (ölçülen: CV)
        en_iyi = min(_MODELLER, key=lambda m: np.percentile(
            k[m][1.0]["m"], 50) if len(k[m][1.0]["m"]) > 20 else 1e9)
        print("\n  bütçede kullanılan model: %s" % en_iyi)
        kh = {u: float(np.percentile(k[en_iyi][u]["m"], 50))
              for u in UFUKLAR if len(k[en_iyi][u]["m"]) > 20}
        korbolge(seg, kh)
        cevrim(kestirim_hata=kh)


if __name__ == "__main__":
    main()
