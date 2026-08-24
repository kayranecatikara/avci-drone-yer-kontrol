# -*- coding: utf-8 -*-
"""
================================================================================
  HEDEF IZ KAYDI  --  simulasyondaki hedef aracin GERCEK GPS izi + hizi
================================================================================
NE ISE YARAR
--------------------------------------------------------------------------------
Sorulara olcumle cevap verir:
    * hedefin hizi kac?  max / min?
    * manevrada hiz DUSUYOR mu?
    * ucus deseni KARE mi DAIRE mi?

NEDEN SUNUCUNUN ICINDE
--------------------------------------------------------------------------------
Oyun TEK TCP baglantisi kabul ediyor ve o baglantiyi arayuz sunucusu tutuyor.
Ayri bir kayit betigi ayni anda baglanamaz -> soketi birbirinden koparirlar
(bkz. web/server.py "CIFT ORNEK KAPISI" notu). Bu yuzden kayit AYNI
baglantidan, ayri bir thread olarak akiyor.

NEDEN get_debug_truth
--------------------------------------------------------------------------------
Normal telemetri kanali hedefi BOZUYOR (gurultu, kayma, dropout, ~1 sn gecikme)
ve 5 Hz. Desen/hiz sorusuna bozuk veriyle cevap verilemez. truth alanlari her
telemetri satirinda gelir -> ~30 Hz TEMIZ konum.

HIZ ALANI: sdk v[26] (truth target speed) OLCULDU ve konum degisirken bile
0 geliyor -- oyun o alani doldurmuyor. Yine de CSV'ye yaziliyor (bir gun
dolarsa diye); hiz KONUMDAN turetiliyor, bkz. hedef_iz_grafik.py.

CIKTI  veri/hedef_iz/hedef_iz_<zaman>.csv
--------------------------------------------------------------------------------
    t_s          kayit baslangicindan beri gecen sure
    hx_m,hy_m,hz_m   hedef konumu (m, oyun dunyasi)
    h_hiz_ms     hedefin gercek surati (m/s)
    dx_m,dy_m,dz_m   bizim drone (m)  -- baglam icin
    d_hiz_ms     bizim suratimiz (m/s)

KAPATMA:  set AVCI_IZ_KAPALI=1     (varsayilan ACIK -- maliyet ~1 MB/dk)
================================================================================
"""
import os
import time
import threading

# 200 Hz: 50 Hz OLCULDU ve yetmedi. Oyun hedef konumunu ~30 Hz gunceller;
# 50 Hz yoklamada "degisimi gorme ani" +-20 ms kayar, bu da komsu-fark
# hizina dogrudan biner (dt-hiz korelasyonu -0.861, sahte +-%50 yayilim).
# 200 Hz -> kayma +-5 ms. Maliyet: kucuk bir dict kopyasi, ihmal edilebilir.
HZ = float(os.environ.get("AVCI_IZ_HZ", "200") or 200)
KAPALI = os.environ.get("AVCI_IZ_KAPALI", "").strip() not in ("", "0")

_durum = {"aktif": False, "satir": 0, "dosya": None}


def durum():
    return dict(_durum)


def _dongu(drone, kok):
    """~50 Hz truth oku, KONUM DEGISTIYSE yaz. Oyun bagli degilken beklemede."""
    klasor = os.path.join(kok, "veri", "hedef_iz")
    os.makedirs(klasor, exist_ok=True)
    yol = os.path.join(klasor, "hedef_iz_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))
    _durum["dosya"] = yol

    f = open(yol, "w", encoding="utf-8", newline="\n")
    # FAZ + MUTLAK ZAMAN eklendi (2026-08-15): kullanici "faza gecince baska
    # yere gidiyor" diyor. Teshis icin iki sey sart:
    #   faz      -> gecis ANI hangi satirda, gozle degil veriyle bulunsun
    #   t_mutlak -> bbox_ibvs CSV'si ile AYNI saat ekseninde hizalanabilsin
    #               (o dosya da time.perf_counter kullaniyor)
    # ⚠ 2026-08-16: TUTUM + HIZ VEKTORU eklendi. Kolonlar SONA eklendi,
    # mevcutlar degismedi -> okuyucular DictReader ile isimle aliyor, bozulmaz.
    # NEDEN: "arac sacma yone gidiyor" iddiasi konum + hiz BUYUKLUGU ile
    # olculemez. Burun nereye bakiyor (yaw), govde ne kadar yatik (roll),
    # hiz vektoru hangi yonde -- ucu AYRI sey. Multirotor yan ucabilir:
    # yaw ile hiz yonunun ayrismasi normaldir, hata degildir.
    # Alan yoksa BOS yazilir (0 degil) -- "olculmedi" ile "sifir" karismasin.
    f.write("t_s,t_mutlak,faz,gecis,hx_m,hy_m,hz_m,h_hiz_ms,"
            "dx_m,dy_m,dz_m,d_hiz_ms,"
            "h_roll,h_pitch,h_yaw,h_vx,h_vy,h_vz,"
            "d_roll,d_pitch,d_yaw,d_vx,d_vy,d_vz\n")
    print("[IZ] hedef iz kaydi -> %s  (%.0f Hz, faz damgali)" % (yol, HZ))

    CM = 100.0
    periyot = 1.0 / max(HZ, 1.0)
    t0 = None
    son_konum = None
    son_uyari = 0.0
    son_akis = 0.0
    n = 0
    while True:
        time.sleep(periyot)
        try:
            if not drone.is_connected():
                _durum["aktif"] = False
                continue
            d = drone.get_debug_truth()
            if not d.get("available"):
                # Oyunda debug kapaliysa truth gelmez -> sessiz kalma, soyle.
                simdi = time.time()
                if simdi - son_uyari > 20.0:
                    son_uyari = simdi
                    print("[IZ] !! get_debug_truth YOK (oyunda debug kapali) "
                          "-> iz kaydi bekliyor.")
                _durum["aktif"] = False
                continue

            h = d["target"]
            b = d.get("drone", {})
            hp = h["position"]
            if hp == son_konum:
                continue                      # yeni paket gelmemis, tekrar yazma
            son_konum = hp

            simdi = time.perf_counter()
            if t0 is None:
                t0 = simdi
                print("[IZ] BASLADI (hedef hareket verisi akiyor).")
            _durum["aktif"] = True

            bp = b.get("position", (0.0, 0.0, 0.0))
            # Faz, supervisor'in kendi durumundan okunur (tembel import:
            # kopru yolu ancak gorev baslayinca sys.path'e giriyor).
            faz, gecis = "?", -1
            try:
                from control.guidance import supervisor as _sv
                faz = str(_sv.status.get("faz", "?"))
                gecis = int(_sv.status.get("gecis_sayisi", -1) or -1)
            except Exception:
                pass
            f.write("%.3f,%.4f,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%s\n" % (
                simdi - t0, simdi, faz, gecis,
                # ⚠ HIZ da cm/s (2026-08-15 yakalanan hata): konumlar CM'ye
                # bolunuyordu ama hiz bolunmuyordu -> d_hiz_ms 1847 gibi
                # sacma degerler yaziyordu. Turetilmis hizla korelasyon
                # +0.978 ve oran tam 100 -> birim kesin cm/s.
                hp[0] / CM, hp[1] / CM, hp[2] / CM, float(h.get("speed", 0.0)) / CM,
                bp[0] / CM, bp[1] / CM, bp[2] / CM, float(b.get("speed", 0.0)) / CM,
                _ek_alanlar(h, b, drone, CM)))
            n += 1
            _durum["satir"] = n
            if n % 500 == 0:
                f.flush()
                if simdi - son_akis > 10.0:
                    son_akis = simdi
                    print("[IZ] %d ornek | hedef hizi %.1f m/s"
                          % (n, float(h.get("speed", 0.0))))
        except Exception as e:
            simdi = time.time()
            if simdi - son_uyari > 20.0:
                son_uyari = simdi
                print("[IZ] hata (kayit devam ediyor): %r" % (e,))


def baslat(drone, kok):
    """Env ile kapatilmadiysa arka plan thread'ini kurar. Hatada SESSIZ DUSMEZ."""
    if KAPALI:
        print("[IZ] AVCI_IZ_KAPALI ayarli -> hedef iz kaydi kapali.")
        return False
    threading.Thread(target=_dongu, args=(drone, kok), daemon=True).start()
    return True


def _uc(d, ad):
    """Sozlukten 3'lu al. Yoksa/bozuksa None -- kayit ASLA durmasin."""
    try:
        v = d.get(ad)
        if v is None or len(v) < 3:
            return None
        return (float(v[0]), float(v[1]), float(v[2]))
    except (TypeError, ValueError, AttributeError):
        return None


def _ek_alanlar(h, b, drone, CM):
    """h_roll,h_pitch,h_yaw,h_vx,h_vy,h_vz,d_roll,...,d_vz -> 12 alan.

    ⚠ Eksik alan BOS birakilir, 0 YAZILMAZ: analizde "olculmedi" ile "sifir"
    karistirilirsa 'arac hic donmemis' gibi sahte bulgu uretir.
    ⚠ Rotasyon DERECE, hiz cm/s -> m/s'ye bolunur (bkz. yukaridaki birim notu).
    Kendi tutumumuz truth paketinde yoksa CANLI telemetriye dusulur; kopru
    zaten oradan okuyor (dow_kopru._drone_dow).
    """
    hr, hv = _uc(h, "rotation"), _uc(h, "velocity")
    # ⚠ 2026-08-16 OLCULDU: get_debug_truth()["target"] rotasyon TASIMIYOR.
    #   sdk/drone_sdk.py:223-226 truth paketine hedef icin yalniz position(v[23..25])
    #   ve speed(v[26]) yaziyor. Rotasyon oyun paketinde VAR ama v[14..16] ->
    #   telemetry["target"]["rotation"], yani ANA (bozulabilen) kanala gidiyor.
    #   124.363 satirlik ucusta h_roll/h_pitch/h_yaw'in %100'u BOS cikti.
    #   Bu yuzden ana kanala DUSULUR -- hic veri olmamasindansa isaretli veri.
    # ⚠ GUVENILIRLIK OLCULMEDI: ana kanalda konum/hiz bozuluyor (gurultu, gecikme,
    #   5 Hz). Rotasyonun bozulup bozulmadigi HENUZ olculmedi -- repoda iki celisen
    #   yorum var (ana_kontrol.py:820 "bozuk", server.py:1890 "bozulmaz").
    #   Bu sutunu truth gibi kullanmadan once poz modeline karsi olc.
    if hr is None or hv is None:
        try:
            _ht = drone.get_telemetry()["target"]
            hr = hr if hr is not None else _uc(_ht, "rotation")
            hv = hv if hv is not None else _uc(_ht, "velocity")
        except Exception:
            pass
    br, bv = _uc(b, "rotation"), _uc(b, "velocity")
    if br is None or bv is None:
        try:
            t = drone.get_telemetry()["drone"]
            br = br if br is not None else _uc(t, "rotation")
            bv = bv if bv is not None else _uc(t, "velocity")
        except Exception:
            pass

    def f3(v, olcek=1.0):
        return ",," if v is None else "%.2f,%.2f,%.2f" % (
            v[0] * olcek, v[1] * olcek, v[2] * olcek)

    return "%s,%s,%s,%s" % (f3(hr), f3(hv, 1.0 / CM), f3(br), f3(bv, 1.0 / CM))
