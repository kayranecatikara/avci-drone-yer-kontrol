# -*- coding: utf-8 -*-
"""HEDEF TEKRAR KESTIRICISI testleri.

Bu testler ucus kararlarini kilitler. En onemlileri kapinin KAPANMASI
gereken durumlar: uydurma kestirimle ucmak, hic kestirim yapmamaktan
COK daha tehlikelidir (yasa yanlis yere nisan alir).

Olculen dayanaklar (2026-08-18, 47 iz parcasi):
  - periyot 29.60 s (p10 = p90 = 29.60)
  - tekrar kestiricisi hatasi ufuktan BAGIMSIZ: 2/5/10/20/30 s ->
    1.06/0.72/0.62/0.65/0.66 m
  - nedensel (canli besleme) dogrulama: 0.50/0.39/0.42/0.60/0.64 m
"""
import os
import sys
import math

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kopru", "gazebo_kaynak"))

from control.guidance.hedef_tekrar import HedefTekrar  # noqa: E402


def _cember(tk, sure_s, P=29.6, R=40.0, hz=10.0, t0=0.0, faz=0.0):
    """Yaricap R, periyot P olan cembere oturt; son zamani dondur."""
    n = int(sure_s * hz)
    t = t0
    for i in range(n):
        t = t0 + i / hz
        a = faz + 2.0 * math.pi * (t - t0) / P
        tk.ekle(t, R * math.cos(a), R * math.sin(a), 50.0)
        tk.guncelle()
    return t


def test_veri_yokken_hazir_degil():
    tk = HedefTekrar()
    assert tk.hazir() is False
    assert tk.kestir(10.0) is None


def test_yarim_turda_hazir_degil():
    """Bir tam tur gormeden kapi ACILMAMALI."""
    tk = HedefTekrar()
    _cember(tk, 15.0)
    assert tk.hazir() is False
    assert tk.kestir(100.0) is None


def test_bir_turdan_sonra_acilir_ve_periyodu_bulur():
    """⚠ 40 s YETMEZ: P=29.6 icin ortusme yalniz ~10 s olur, kestirim
    gurultulenir (olculdu: periyot 28.5, kalite 9.32) ve kapi -- DOGRU
    sekilde -- KAPALI kalir. Yeterli ortusmede kalite 1e-12. Bu test o siniri kilitler."""
    az = HedefTekrar()
    _cember(az, 40.0)
    assert az.hazir() is False, "yetersiz ortusmeyle kapi ACILMAMALI"
    tk = HedefTekrar()
    _cember(tk, 60.0)
    assert tk.hazir() is True
    assert tk.periyot == pytest.approx(29.6, abs=0.25)
    assert tk.kalite < 1.0


def test_kestirim_dogru_cemberde():
    """Ufuk ne olursa olsun hata kucuk kalmali (tekrarin ozu budur)."""
    tk = HedefTekrar()
    P, R = 29.6, 40.0
    son = _cember(tk, 60.0, P=P, R=R)
    for ufuk in (2.0, 5.0, 10.0, 20.0, 30.0):
        p = tk.kestir(son + ufuk)
        assert p is not None, "ufuk %.0f s icin kestirim yok" % ufuk
        a = 2.0 * math.pi * (son + ufuk) / P
        hata = math.hypot(p[0] - R * math.cos(a), p[1] - R * math.sin(a))
        assert hata < 1.5, "ufuk %.0f s -> hata %.2f m" % (ufuk, hata)


def test_harmonik_periyot_GECERLI_kestiricidir():
    """⚠ 15 s'lik pistte modul 30 s buluyor ve kapiyi ACIYOR -- bu DOGRU.
    30, gercek periyodun harmonigidir ve kestirim kusursuz calisir.
    Bu yuzden `PERIYOT_TOLERANS` sert kapi DEGILDIR; asil kapi KALITE'dir.
    (8 oyun varyantinin ovalleri farkli; periyodu 29.6'ya baglamak
    baska varyantta kapiyi bosuna kapatirdi.)"""
    P, R = 15.0, 30.0
    tk = HedefTekrar()
    son = _cember(tk, 60.0, P=P, R=R)
    assert tk.hazir() is True
    assert tk.kalite < 1.0
    p = tk.kestir(son + 7.0)
    assert p is not None
    a = 2.0 * math.pi * (son + 7.0) / P
    assert math.hypot(p[0] - R * math.cos(a), p[1] - R * math.sin(a)) < 1.5


def test_tekrarsiz_pistte_kapi_kapali():
    """Gercek koruma KALITE esigidir: pist tekrar etmiyorsa kapi kapanmali."""
    tk = HedefTekrar()
    t = 0.0
    for i in range(700):
        t = i / 10.0
        tk.ekle(t, 0.9 * t + 3.0 * math.sin(0.11 * t),
                0.4 * t * math.cos(0.07 * t), 50.0)
        tk.guncelle()
    assert tk.hazir() is False


def test_gurultulu_pist_kaliteyi_dusurur_kapi_kapanir():
    """Hedef pistini birakirsa (rastgele gezinme) kapi KAPANMALI."""
    tk = HedefTekrar()
    t = 0.0
    x = y = 0.0
    # deterministik ama tekrarsiz gezinme
    for i in range(600):
        t = i / 10.0
        x += 1.7 * math.sin(0.37 * i) + 0.9
        y += 1.3 * math.cos(0.21 * i) - 0.4
        tk.ekle(t, x, y, 50.0)
        tk.guncelle()
    assert tk.hazir() is False


def test_saat_geriye_giderse_tampon_sifirlanir():
    """Sunucu yeniden baslayinca `t` sifirlanir -> eski veri GECERSIZ."""
    tk = HedefTekrar()
    _cember(tk, 60.0)
    assert tk.hazir() is True
    tk.ekle(1.0, 0.0, 0.0, 50.0)           # saat geriye gitti
    assert tk.hazir() is False
    assert tk.kestir(50.0) is None


def test_olumsuz_kontrol_carpani_kestirimi_KAYDIRIR():
    """Periyot carpani 1.2 -> kestirim bilerek bozulur (olumsuz kontrol).

    Bu kolun sonucu KOTU cikmali; cikmiyorsa kazanc kestirimden gelmiyordur.
    """
    P, R = 29.6, 40.0
    ta = HedefTekrar()
    son = _cember(ta, 60.0, P=P, R=R)
    tb = HedefTekrar(periyot_carpan=1.2)
    _cember(tb, 60.0, P=P, R=R)
    a = ta.kestir(son + 10.0)
    b = tb.kestir(son + 10.0)
    assert a is not None and b is not None
    assert math.hypot(a[0] - b[0], a[1] - b[1]) > 5.0, \
        "bozuk periyot kestirimi kaydirmadi -> olumsuz kontrol ISE YARAMAZ"


def test_tani_alanlari():
    tk = HedefTekrar()
    _cember(tk, 60.0)
    d = tk.tani()
    for k in ("tekrar_periyot_s", "tekrar_kalite_m", "tekrar_hazir",
              "tekrar_ornek", "tekrar_sure_s", "tekrar_carpan"):
        assert k in d
    assert d["tekrar_hazir"] is True


def test_tampon_pencereyi_asmaz():
    tk = HedefTekrar(pencere_s=20.0)
    _cember(tk, 60.0)
    assert tk.tani()["tekrar_sure_s"] <= 20.5


def test_cok_ileri_ufukta_None_donmez_tur_sarar():
    """3 tur sonrasi da bilinebilmeli (tur tur geri sarma)."""
    tk = HedefTekrar()
    son = _cember(tk, 60.0)
    p = tk.kestir(son + 3 * 29.6 + 5.0)
    assert p is not None


# ════════ BULUSMA NOKTASI SECIMI (bulusma_sec) ════════════════════════
from control.guidance.hedef_tekrar import bulusma_sec  # noqa: E402


def test_bulusma_hazir_degilken_None():
    """Kestirici hazir degilse ASLA nokta uretme -- cagiran eski davranista kalir."""
    tk = HedefTekrar()
    _cember(tk, 10.0)
    assert bulusma_sec(tk, 10.0, 100.0, 0.0) is None


def test_bulusma_hedef_aspecti_tutturur():
    """Cemberde 75 derece aspect veren bir nokta bulunmali."""
    tk = HedefTekrar()
    son = _cember(tk, 60.0, P=29.6, R=40.0)
    r = bulusma_sec(tk, son, 200.0, 0.0, aspect_hedef=75.0)
    assert r is not None
    x, y, z, ux, uy, tgo, asp = r
    assert 60.0 <= asp <= 90.0, "secilen aspect en iyi bantta olmali (%.1f)" % asp
    assert 2.0 <= tgo <= 30.0


def test_bulusma_ULASILAMAZ_noktayi_secmez():
    """Cok uzaktayken kisa tgo'lar ELENMELI (mesafe > V*tgo*pay)."""
    tk = HedefTekrar()
    son = _cember(tk, 60.0, P=29.6, R=40.0)
    # 2000 m uzaktayiz: 30 s x 20 m/s = 600 m -> hicbir nokta ulasilamaz
    assert bulusma_sec(tk, son, 2000.0, 0.0, v_kabul=20.0, tgo_max=30.0) is None
    # ayni yerden cok yuksek hizla ulasilabilir olmali
    r = bulusma_sec(tk, son, 2000.0, 0.0, v_kabul=200.0, tgo_max=30.0)
    assert r is not None


def test_bulusma_kurs_BULUSMA_ANININDAKI_olmali():
    """Donen hedefte, dondurulen kurs SIMDIKI degil BULUSMA ANINDAKI olmali."""
    tk = HedefTekrar()
    P, R = 29.6, 40.0
    son = _cember(tk, 60.0, P=P, R=R)
    r = bulusma_sec(tk, son, 200.0, 0.0)
    assert r is not None
    x, y, z, ux, uy, tgo, asp = r
    # cemberde konum aciyla, kurs ise +90 derece ile iliskilidir
    a = 2.0 * math.pi * (son + tgo) / P
    bek_ux, bek_uy = -math.sin(a), math.cos(a)
    assert math.hypot(ux - bek_ux, uy - bek_uy) < 0.25, \
        "kurs bulusma anina ait degil (fark %.2f)" % math.hypot(ux - bek_ux, uy - bek_uy)


def test_bulusma_bozuk_periyotla_FARKLI_nokta_secer():
    """OLUMSUZ KONTROL: periyot %20 bozulunca secilen nokta kaymali."""
    P, R = 29.6, 40.0
    ta = HedefTekrar()
    son = _cember(ta, 60.0, P=P, R=R)
    tb = HedefTekrar(periyot_carpan=1.2)
    _cember(tb, 60.0, P=P, R=R)
    a = bulusma_sec(ta, son, 200.0, 0.0)
    b = bulusma_sec(tb, son, 200.0, 0.0)
    assert a is not None and b is not None
    assert math.hypot(a[0] - b[0], a[1] - b[1]) > 3.0, \
        "bozuk periyot ayni noktayi secti -> olumsuz kontrol ISE YARAMAZ"


def test_bulusma_SAPMA_SINIRI_uygulanir():
    """⚠ HAYATI: istasyon hedefin simdiki yerinden cok uzaga KONMAMALI.

    Sinirsiz secim olculdu: medyan 130.6 m sapma -> hedef kadraj disi ->
    tespit olur -> devir olcutu (10 ardisik kare) hic dolmaz -> sistem coker.
    """
    tk = HedefTekrar()
    P, R = 29.6, 40.0
    son = _cember(tk, 60.0, P=P, R=R)
    a = 2.0 * math.pi * son / P
    hx, hy = R * math.cos(a), R * math.sin(a)      # hedefin SIMDIKI yeri
    genis = bulusma_sec(tk, son, 200.0, 0.0, sapma_max=999.0, hx=hx, hy=hy)
    dar = bulusma_sec(tk, son, 200.0, 0.0, sapma_max=15.0, hx=hx, hy=hy)
    assert genis is not None and dar is not None
    assert math.hypot(dar[0] - hx, dar[1] - hy) <= 15.0 + 1e-6, \
        "sapma siniri UYGULANMADI"
    assert math.hypot(genis[0] - hx, genis[1] - hy) > \
        math.hypot(dar[0] - hx, dar[1] - hy), "sinir hic baglamadi"


def test_bulusma_sapma_siniri_hepsini_elerse_None():
    """Sinir cok darsa hicbir aday kalmaz -> None -> eski davranis."""
    tk = HedefTekrar()
    P, R = 29.6, 40.0
    son = _cember(tk, 60.0, P=P, R=R)
    a = 2.0 * math.pi * son / P
    hx, hy = R * math.cos(a), R * math.sin(a)
    assert bulusma_sec(tk, son, 200.0, 0.0, sapma_max=0.01, hx=hx, hy=hy) is None
