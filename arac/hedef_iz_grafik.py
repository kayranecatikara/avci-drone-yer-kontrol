# -*- coding: utf-8 -*-
"""
================================================================================
  HEDEF IZ GRAFIK  --  kus bakisi iz + hiz analizi  (Z YOK, tamamen 2B)
================================================================================
hedef_iz_kaydi.py'nin yazdigi CSV'yi okur ve su sorulara OLCUMLE cevap verir:
    1) hedefin hizi kac?  ortalama / max / min
    2) manevrada hiz DUSUYOR mu?      -> donus hizina gore hiz karsilastirmasi
    3) desen KARE mi DAIRE mi?        -> yon degisiminin yay boyunca dagilimi

KARE/DAIRE AYRIMI NASIL YAPILIYOR
--------------------------------------------------------------------------------
Yolun her noktasinda "yon degisim yogunlugu" k = dpsi/ds hesaplaniyor (1/m).
    DAIRE  -> k her yerde ayni (~1/R). Duz kisim YOK.
    KARE   -> kenarlarda k~0, kosede k patliyor. Yani yayin buyuk kismi DUZ.
Olcut: yolun yuzde kaci "duz" (k, tepe degerinin %15'inin altinda).
Sonra her donus blogunun TOPLADIGI yon degisimi bakilir:
    ~90 derece  -> KARE / cokgen kosesi
    ~180 derece + tur basina 2 blok  -> OVAL / YARIS PISTI (stadyum)
    duz kisim hic yok  -> DAIRE

CALISTIR
    python arac/hedef_iz_grafik.py                 (en yeni kaydi alir)
    python arac/hedef_iz_grafik.py <csv yolu>
================================================================================
"""
import os
import sys
import glob

import numpy as np
import matplotlib
matplotlib.use("Agg")                       # sunucuda pencere yok, dosyaya yaz
import matplotlib.pyplot as plt

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def en_yeni_csv():
    a = sorted(glob.glob(os.path.join(KOK, "veri", "hedef_iz", "hedef_iz_*.csv")),
               key=os.path.getmtime)
    return a[-1] if a else None


def yumusat(v, k):
    """Kenarlari kirpmayan hareketli ortalama (yansitmali dolgu)."""
    if k < 3:
        return v
    k = int(k) | 1
    p = k // 2
    g = np.concatenate([v[p:0:-1], v, v[-2:-p - 2:-1]])
    return np.convolve(g, np.ones(k) / k, mode="valid")[:len(v)]


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else en_yeni_csv()
    if not yol or not os.path.exists(yol):
        print("Kayit bulunamadi. Once arayuzu calistir ve simulasyonu ac.")
        print("Beklenen yer: veri/hedef_iz/hedef_iz_*.csv")
        return 1

    d = np.genfromtxt(yol, delimiter=",", names=True)
    if d.size < 20:
        print("Kayit cok kisa (%d ornek). Simulasyonu biraz daha calistir." % d.size)
        return 1

    t = np.asarray(d["t_s"], float)
    x = np.asarray(d["hx_m"], float)
    y = np.asarray(d["hy_m"], float)
    z = np.asarray(d["hz_m"], float)
    v_ham = np.asarray(d["h_hiz_ms"], float)

    # HIZ NEREDEN: oyunun truth paketindeki hedef surati (v[26]) OLCULDU ve
    # 0 geliyor -- konum degisirken bile. Yani o alan doldurulmuyor. Bu yuzden
    # hiz TEMIZ truth KONUMUNDAN turetiliyor (~30 Hz, gurultusuz).
    # Raporlanan alan sifir degilse onu da yazdirip karsilastiriyoruz.
    # Ornekler KONUM DEGISTIKCE yaziliyor -> dt duzgun araliklı DEGIL.
    art = np.concatenate([[True], np.diff(t) > 1e-9])
    t, x, y, z, v_ham = t[art], x[art], y[art], z[art], v_ham[art]

    # HIZI KOMSU IKI ORNEKTEN TURETME -- OLCULDU, ARTEFAKT VERIYOR:
    #   t, oyunun konumu URETTIGI an degil, logger'in DEGISIMI GORDUGU an.
    #   50 Hz yoklama + ~30 Hz oyun guncellemesi -> dt iki tepeli (20/41 ms),
    #   yani gercek araligin uzerinde +-20 ms titreme var. Komsu farkta bu
    #   dogrudan hiza biner: dt-hiz korelasyonu -0.861 olculdu ve "max 32.6,
    #   min 9.1 m/s" gibi sahte bir yayilim uretti.
    # COZUM: PENCERELI hiz. Yay uzunlugu s(t) tam dogru (konum temiz truth);
    #   titreme W boyunca sabit kaldigi icin bagil hata 20ms/W'ye duser.
    #   W=0.4 s -> ~%5, logger 200 Hz'e cikinca ~%1.
    W = 0.4
    sy = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    s3 = np.concatenate([[0.0], np.cumsum(np.sqrt(
        np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2))])
    ta, tb = t - W / 2.0, t + W / 2.0
    np.clip(ta, t[0], t[-1], out=ta)
    np.clip(tb, t[0], t[-1], out=tb)
    genis = np.maximum(tb - ta, 1e-6)
    v_yatay = (np.interp(tb, t, sy) - np.interp(ta, t, sy)) / genis
    v_3b = (np.interp(tb, t, s3) - np.interp(ta, t, s3)) / genis
    ham_var = float(np.abs(v_ham).max()) > 0.05
    v = v_yatay

    # Yolu merkeze al (mutlak dunya koordinati okunakli degil)
    x0, y0 = x.mean(), y.mean()
    xr, yr = x - x0, y - y0

    print("=" * 74)
    print("HEDEF IZ ANALIZI   %s" % os.path.basename(yol))
    print("=" * 74)
    print("  ornek           : %d   (%.1f sn, ort. %.1f Hz)"
          % (len(t), t[-1] - t[0], len(t) / max(t[-1] - t[0], 1e-6)))

    # ------------------------------------------------------------------ HIZ
    print()
    print()
    if ham_var:
        print("  HIZ  (oyunun bildirdigi surat)")
        print("    ortalama      : %6.2f m/s   (%5.1f km/h)"
              % (v_ham.mean(), v_ham.mean() * 3.6))
    else:
        print("  HIZ  (truth KONUMUNDAN turetildi -- oyun hedef suratini 0")
        print("        bildiriyor, o alan doldurulmuyor)")
    # Bas/son W/2 saniyede pencere KIRPILIYOR (tam genislik yok) -> o
    # ornekleri istatistige katma, yoksa sahte dusuk hiz cikar.
    ic = (t >= t[0] + W / 2.0) & (t <= t[-1] - W / 2.0)
    if ic.sum() < 10:
        ic = np.ones_like(t, bool)
    vv = v[ic]
    print("    ortalama      : %6.2f m/s   (%5.1f km/h)" % (vv.mean(), vv.mean() * 3.6))
    print("    max           : %6.2f m/s   (%5.1f km/h)" % (vv.max(), vv.max() * 3.6))
    print("    min           : %6.2f m/s   (%5.1f km/h)" % (vv.min(), vv.min() * 3.6))
    print("    std sapma     : %6.2f m/s" % vv.std())
    print("    degisim orani : %6.1f %%  ((max-min)/ortalama)"
          % (100.0 * (vv.max() - vv.min()) / max(vv.mean(), 1e-6)))
    v3 = v_3b[ic]
    print("    (3B surat ort : %6.2f m/s -- dikey bilesen dahil)" % v3.mean())

    # --- YAYILIM GERCEK MI, GURULTU MU?  Pencereyi buyut ve std'ye bak. -----
    # Gurultuyse std ~1/sqrt(W) ile sifira gider; gercek hiz degisimiyse
    # bir degerde DURUR. Karari okuyucuya birakmiyoruz, kaniti basiyoruz.
    print()
    print("    yayilim testi (pencere buyutuldukce):")
    print("      %-9s%8s%8s%8s" % ("W (s)", "ort", "std", "yayilim"))
    stdler = []
    for Wt in (0.2, 0.5, 1.0, 2.0, 4.0):
        a2 = np.clip(t - Wt / 2.0, t[0], t[-1])
        b2 = np.clip(t + Wt / 2.0, t[0], t[-1])
        vt = (np.interp(b2, t, sy) - np.interp(a2, t, sy)) / np.maximum(b2 - a2, 1e-9)
        m = (t >= t[0] + Wt / 2.0) & (t <= t[-1] - Wt / 2.0)
        if m.sum() < 10:
            continue
        stdler.append(vt[m].std())
        print("      %-9.1f%8.2f%8.3f%8.2f"
              % (Wt, vt[m].mean(), vt[m].std(), vt[m].max() - vt[m].min()))
    if len(stdler) >= 2 and stdler[-1] < 0.35 * stdler[0]:
        print("      ---> std sifira gidiyor: YAYILIM ORNEKLEME GURULTUSU.")
        print("           Hedefin hizi SABIT ~%.2f m/s (max=min)." % vv.mean())
    else:
        print("      ---> std bir degerde duruyor: hiz GERCEKTEN degisiyor.")

    # Tamamen bagimsiz kontrol: tur mesafesi / tur suresi (turevden gecmez)
    _psi = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
    _tur = abs(_psi[-1] - _psi[0]) / (2 * np.pi)
    if _tur > 0.5:
        print("    bagimsiz kontrol (toplam yol / toplam sure): %.2f m/s"
              % (sy[-1] / (t[-1] - t[0])))

    # ------------------------------------------------- GEOMETRI: yon ve yay
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    psi = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))

    # DONUS HIZI da hizla AYNI SEBEPTEN pencereli olmali: anlik gradyan
    # ornekleme titremesini yutuyor ve yaricapi sahte kucuk gosteriyor
    # (anlik yontem "en dar donus 21.5 m" dedi; oysa oval 100 m genis,
    # gercek uc yaricapi ~45 m). Pencereli olcum bunu duzeltir.
    ta2, tb2 = np.clip(t - W / 2.0, t[0], t[-1]), np.clip(t + W / 2.0, t[0], t[-1])
    gen2 = np.maximum(tb2 - ta2, 1e-6)
    omega = (np.interp(tb2, t, psi) - np.interp(ta2, t, psi)) / gen2   # rad/s
    da = np.degrees(np.abs(omega))
    # Egrilik k = omega / v  (1/m) -> yaricap = 1/k
    ka = np.abs(omega) / np.maximum(v, 0.1)

    print()
    print("  YOL")
    print("    toplam mesafe : %8.1f m" % s[-1])
    print("    genislik x/y  : %8.1f m  /  %.1f m"
          % (xr.max() - xr.min(), yr.max() - yr.min()))
    # ------------------------------------------------- KARE mi DAIRE mi
    esik = 0.15 * np.percentile(da, 98)          # tepe donus hizinin %15'i
    duz = da < esik
    duz_oran = 100.0 * duz.sum() / len(da)

    # DONUS SERTLIGI: max DEGIL medyan. max tek bir gurultu tepesine takiliyor
    # ("en dar donus 19 m" dedi), oysa geometri bagimsiz olarak ~40 m veriyor:
    # tur basi 527 m, %52'si duz -> donus yayi ~127 m, 180 derece icin
    # r = 127/pi = 40 m. Medyan bu gercek degeri veriyor, max vermiyor.
    dbol = (~duz) & ic
    if dbol.sum() > 10:
        w_med = np.median(da[dbol])
        r_med = np.median(v[dbol]) / np.radians(max(w_med, 1e-6))
        print("    donus hizi    : %8.1f derece/sn (medyan), %.1f (tepe %%99)"
              % (w_med, np.percentile(da[ic], 99)))
        print("    donus yaricapi: %8.1f m (medyan)" % r_med)
    else:
        print("    donus hizi    :  (belirgin donus yok)")

    # Donus bloklari: "duz degil" bolgelerin ayrik parcalari + her birinin
    # topladigi yon degisimi (kose acisi). Kare -> ~90, oval ucu -> ~180.
    bloklar = []
    bas = None
    for i, b in enumerate(~duz):
        if b and bas is None:
            bas = i
        elif not b and bas is not None:
            bloklar.append((bas, i))
            bas = None
    if bas is not None:
        bloklar.append((bas, len(duz)))
    aci = [abs(np.degrees(psi[j - 1] - psi[i])) for i, j in bloklar
           if j - i > 3]
    tur = abs(psi[-1] - psi[0]) / (2 * np.pi)

    print()
    print("  DESEN")
    print("    duz giden yol  : %5.1f %%" % duz_oran)
    print("    donus blogu    : %d" % len(bloklar))
    if aci:
        print("    blok basina yon degisimi: ort %.0f derece (min %.0f, max %.0f)"
              % (np.mean(aci), min(aci), max(aci)))
    if tur > 0.5:
        print("    tur sayisi     : %5.2f   (tur basi %.0f m, %.1f sn)"
              % (tur, s[-1] / tur, (t[-1] - t[0]) / tur))
    dpt = (len(bloklar) / tur) if tur > 0.5 else 0.0    # tur basina donus

    if aci and tur > 0.8 and 1.5 <= dpt <= 2.8 and np.mean(aci) > 120:
        karar = ("OVAL / YARIS PISTI (stadyum) -- 2 duz kenar + 2 adet ~180 donus, "
                 "tur basina %.1f donus" % dpt)
    elif duz_oran > 55.0 and aci and np.mean(aci) < 120:
        karar = "KARE / COKGEN  (uzun duz kenarlar + ~%.0f derecelik koseler)" % np.mean(aci)
    elif duz_oran < 25.0:
        karar = "DAIRE  (surekli sabit donus, duz kenar yok)"
    else:
        karar = "YUVARLATILMIS COKGEN (duz kenar var ama koseler genis yayli)"
    print("    ---> KARAR     : %s" % karar)

    # --------------------------------- MANEVRADA HIZ DUSUYOR MU
    print()
    print("  MANEVRADA HIZ")
    # Desen analiziyle AYNI 'duz' maskesi kullaniliyor. (Once yuzdelik esik
    # denendi ama keskin kare izinde orneklerin %90'i duz oldugu icin 75.
    # yuzdelik 0'a duser, "donus" maskesi TUM kareleri secer ve karsilastirma
    # nan verir. Grafikte taranan bolge de bu maske -- ikisi artik ayni sey.)
    vd, vs_ = v[~duz], v[duz]
    if vd.size < 10 or vs_.size < 10:
        print("    karsilastirilamaz: duz %d / donus %d ornek "
              "(biri 10'un altinda)." % (vs_.size, vd.size))
    else:
        dus = 100.0 * (vs_.mean() - vd.mean()) / max(vs_.mean(), 1e-6)
        print("    duz giderken   : %6.2f m/s  (%d ornek)" % (vs_.mean(), vs_.size))
        print("    donerken       : %6.2f m/s  (%d ornek)" % (vd.mean(), vd.size))
        print("    fark           : %+6.2f m/s  (%%%.1f)"
              % (vd.mean() - vs_.mean(), -dus))
        if abs(dus) < 2.0:
            print("    ---> HAYIR, manevrada hiz DEGISMIYOR (fark %2'nin altinda)")
        elif dus > 0:
            print("    ---> EVET, manevrada hiz DUSUYOR (%%%.1f)" % dus)
        else:
            print("    ---> manevrada hiz ARTIYOR (%%%.1f)" % (-dus))

    # =================================================================== CIZIM
    fig = plt.figure(figsize=(15, 9))
    fig.suptitle("Hedef arac — kus bakisi iz ve hiz  (%s)" % os.path.basename(yol),
                 fontsize=13)

    # 1) KUS BAKISI, hiza gore renkli
    ax = fig.add_subplot(2, 2, 1)
    sc = ax.scatter(xr, yr, c=v, s=6, cmap="turbo")
    ax.plot(xr[0], yr[0], "ko", ms=9, label="baslangic")
    ax.plot(xr[-1], yr[-1], "kX", ms=10, label="son")
    fig.colorbar(sc, ax=ax, label="hiz (m/s)")
    ax.set_title("Kus bakisi iz (Z yok)")
    ax.set_xlabel("dogu-bati  X (m)")
    ax.set_ylabel("kuzey-guney  Y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=.3)
    ax.legend(loc="best", fontsize=8)

    # 2) KUS BAKISI, donus/duz ayrimi -> desen goz ile de gorulsun
    ax = fig.add_subplot(2, 2, 2)
    ax.plot(xr, yr, "-", color="0.75", lw=1, zorder=1)
    ax.scatter(xr[duz], yr[duz], s=6, c="tab:blue", label="duz (%.0f%%)" % duz_oran,
               zorder=2)
    ax.scatter(xr[~duz], yr[~duz], s=6, c="tab:red",
               label="donus (%d blok)" % len(bloklar), zorder=3)
    ax.set_title("Desen: %s" % karar.split("(")[0].strip())
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=.3)
    ax.legend(loc="best", fontsize=8)

    # 3) HIZ - ZAMAN, donus bolgeleri taranmis
    ax = fig.add_subplot(2, 2, 3)
    ax.plot(t, v, lw=0.7, color="tab:green", alpha=.35,
            label="0.4 s pencere (gurultulu)")
    a4 = np.clip(t - 1.0, t[0], t[-1]); b4 = np.clip(t + 1.0, t[0], t[-1])
    v4 = (np.interp(b4, t, sy) - np.interp(a4, t, sy)) / np.maximum(b4 - a4, 1e-9)
    ax.plot(t, v4, lw=1.8, color="darkgreen", label="2 s pencere (gercek)")
    ax.fill_between(t, v.min(), v.max(), where=~duz, color="tab:red", alpha=.12,
                    step="mid", label="donus")
    ax.axhline(v.mean(), ls="--", c="k", lw=1,
               label="ort %.2f m/s" % v.mean())
    ax.set_title("Hiz — zaman   (max %.2f / min %.2f m/s)" % (vv.max(), vv.min()))
    ax.set_xlabel("t (s)")
    ax.set_ylabel("hiz (m/s)")
    ax.grid(alpha=.3)
    ax.legend(loc="best", fontsize=8)

    # 4) YON - YAY:  kare = merdiven,  daire = duz rampa
    ax = fig.add_subplot(2, 2, 4)
    ax.plot(s, np.degrees(psi - psi[0]), lw=1.4, color="tab:purple")
    ax.set_title("Yon — yol boyu  (merdiven=KARE, duz rampa=DAIRE)")
    ax.set_xlabel("kat edilen yol (m)")
    ax.set_ylabel("kumulatif yon degisimi (derece)")
    ax.grid(alpha=.3)

    fig.tight_layout(rect=(0, 0, 1, .96))
    png = os.path.splitext(yol)[0] + ".png"
    fig.savefig(png, dpi=130)
    print()
    print("=" * 74)
    print("  grafik -> %s" % png)
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
