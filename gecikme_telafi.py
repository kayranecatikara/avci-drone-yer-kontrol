# ============================================================
# GECIKME TELAFISI — bozuk GNSS'te 1 sn gecikmeyi zaman ekseninde geri al
# ============================================================
# HESAP YOK, FILTRE YOK. Olcum degerlerine DOKUNULMAZ (gurultu, sicrama
# aynen kalir). Tek is: her olcumun ZAMAN etiketini gecikme_sn geri almak.
#
# NEDEN: t aninda gelen olcum, hedefin t - gecikme_sn'deki konumudur
# (sim FLAG_DELAY: "delay_s sn onceki konum"). Logda olculdu ~1.0 sn.
# Dogru zamana yerlestirmek = olcumu oldugu gibi birakip zamanini geri
# kaydirmak. Spike kendisiyle beraber kayar, BUYUMEZ / IKIZLENMEZ.
#
# KULLANIM (offline analiz / gorsellestirme):
#   t_duzeltilmis = [ti - GECIKME_SN for ti in t]
#   z_temiz = z_spike_temizle(bozuk_z)
#   sonra (t_duzeltilmis, z_temiz) ciftini ciz.
# ============================================================


def zaman_kaydir(zamanlar, gecikme_sn=1.0):
    """Olcum zaman etiketlerini gecikme_sn geri al.

    zamanlar : olcum zaman damgalari (sn)
    Donus    : ayni uzunlukta, her biri gecikme_sn azaltilmis liste.
    Olcum DEGERLERINE dokunmaz.
    """
    return [float(z) - gecikme_sn for z in zamanlar]


def z_spike_temizle(z_dizi, zamanlar=None, esik=3.0, max_hold=8, vz_ema=0.3):
    """z eksenindeki sicramalari (spike) ele: SON HIZLA devam et.

    Gercek irtifa yavas salinir (logda max ~1.25 m/s); spike'lar 30-40 m
    sicrar. Ardisik degisim 'esik'i asarsa o olcum spike'tir. Spike'ta
    olcumu ATIP yerine "son gecerli konum + son hiz * dt" tahminini koyariz.

    NEDEN 'tut' degil 'surdur': eski surum spike boyunca son degeri
    DONDURUYORDU -> grafikte duz plato + plato sonunda dik sicrama, cunku
    spike 5-6 ornek (5 Hz'de ~1 sn) surdugu icin salinim o sure kaciyordu.
    Son hizla (egim) devam edince plato olmaz, salinim takip edilir; logda
    plato 50->0 ornek, ort hata 0.94->0.92 m (hem plato gitti hem iyilesme).

    vz : gecerli olcumler arasi EMA-yumusatilmis egim (spike'tan etkilenmez).
    zamanlar : olcum zaman damgalari (sn); dt buradan. None -> sabit 0.2 s
               (5 Hz rate-limit varsayimi).
    z_dizi : bozuk z olcumleri (m veya cm; esik ayni birimde)
    Donus  : ayni uzunlukta temizlenmis z dizisi. GIRDIYI degistirmez.
    """
    z = list(map(float, z_dizi))
    if not z:
        return z
    tt = list(map(float, zamanlar)) if zamanlar is not None else [0.2 * i for i in range(len(z))]
    temiz = [z[0]]
    son = z[0]
    son_t = tt[0]
    vz = 0.0
    hold = 0
    for i in range(1, len(z)):
        dt = tt[i] - son_t
        if dt <= 0:
            dt = 0.2
        beklenen = son + vz * dt                     # son hizla ileri tasi
        if abs(z[i] - beklenen) > esik and hold < max_hold:
            temiz.append(beklenen)                   # spike: tahminle devam (dondurma YOK)
            son = beklenen                           # tahmini yeni 'son' yap -> plato olmaz
            son_t = tt[i]
            hold += 1
        else:
            yeni_vz = (z[i] - son) / dt              # gecerli olcum: hizi guncelle
            vz = (1 - vz_ema) * vz + vz_ema * yeni_vz
            temiz.append(z[i])
            son = z[i]
            son_t = tt[i]
            hold = 0
    return temiz


def x_spike_temizle(x_dizi, pencere=7, esik=18.0):
    """x eksenindeki spike'lari ele (kayan-pencere medyani ile).

    x hizli hareket ettigi icin z gibi mutlak esik kullanilamaz. Ama
    spike KISA OMURLUdur (firlar, ~1 sn kalir, doner) -- yani genis bir
    komsu penceresinde AZINLIKtadir. Gercek hareket ise pencerenin
    cogunlugudur. Her ornek, kendisi HARIC komsu penceresinin medyaninin
    'esik'ten uzaksa spike'tir -> medyanla degistirilir. Medyan azinliktaki
    spike'tan etkilenmez; gercek trendle birlikte kayar, onu bozmaz.

    x_dizi  : bozuk x olcumleri (m)
    pencere : tek yone bakilan komsu sayisi (toplam ~2*pencere+1)
    Donus   : temizlenmis kopya.
    """
    x = list(map(float, x_dizi))
    n = len(x)
    if n < 3:
        return x
    temiz = x.copy()
    for i in range(n):
        lo = max(0, i - pencere)
        hi = min(n, i + pencere + 1)
        komsu = x[lo:i] + x[i + 1:hi]
        if not komsu:
            continue
        med = sorted(komsu)[len(komsu) // 2]
        if abs(x[i] - med) > esik:
            temiz[i] = med
    return temiz
