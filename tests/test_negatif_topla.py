# -*- coding: utf-8 -*-
"""veriseti/negatif_topla.py saf cekirdegi.

AGIRLIK GUVENLIK KURALINDA: bir kare yanlislikla negatif sayilirsa modele
"bu ucagi GORME" demis oluruz -> gercek tespiti bozar. Testlerin cogu bu tek
yonlu hatayi (gorunur hedefi negatif saymak) kovaliyor.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.negatif_topla import kutu_zarfi, negatif_mi, izgara_say, histogram

W, H = 1920, 1080


def _kp(*noktalar):
    """6 kp bekleniyor; verilen noktalari tekrarlayarak doldur."""
    ns = list(noktalar)
    while len(ns) < 6:
        ns.append(ns[-1])
    return ns


# ---------------------------------------------------------------- kutu_zarfi
def test_kutu_zarfi_sisirir():
    uvs = _kp((100.0, 200.0), (200.0, 300.0))
    x0, y0, x1, y1 = kutu_zarfi(uvs, marj_x=0.10, marj_y=0.30)
    # ham zarf 100..200 (w=100), 200..300 (h=100)
    assert x0 == 100 - 10 and x1 == 200 + 10
    assert y0 == 200 - 30 and y1 == 300 + 30


def test_kutu_zarfi_marjsiz_ham_zarf():
    uvs = _kp((10.0, 20.0), (30.0, 60.0))
    assert kutu_zarfi(uvs, 0.0, 0.0) == (10.0, 20.0, 30.0, 60.0)


# ---------------------------------------------------------------- negatif_mi
def test_tamami_arkada_guvenli():
    guvenli, sebep = negatif_mi([None] * 6, W, H)
    assert guvenli and sebep == "tamami_arkada"


def test_kismen_arkada_REDDEDILIR():
    """Hedef kamera duzlemini kesiyor = COK yakin. Asla negatif sayilmaz."""
    uvs = _kp((900.0, 500.0), (950.0, 520.0))
    uvs[0] = None
    guvenli, sebep = negatif_mi(uvs, W, H)
    assert not guvenli and sebep == "kismen_arkada"


def test_kadraj_ortasindaki_hedef_REDDEDILIR():
    uvs = _kp((950.0, 530.0), (990.0, 550.0))
    guvenli, sebep = negatif_mi(uvs, W, H)
    assert not guvenli and sebep == "kadrajda"


def test_tamamen_solda_guvenli():
    uvs = _kp((-400.0, 500.0), (-350.0, 520.0))
    guvenli, sebep = negatif_mi(uvs, W, H)
    assert guvenli and sebep == "kadraj_disi"


def test_tamamen_sagda_guvenli():
    uvs = _kp((float(W) + 300, 500.0), (float(W) + 360, 520.0))
    assert negatif_mi(uvs, W, H)[0] is True


def test_tamamen_ustte_ve_altta_guvenli():
    ust = _kp((900.0, -300.0), (950.0, -260.0))
    alt = _kp((900.0, float(H) + 260), (950.0, float(H) + 300))
    assert negatif_mi(ust, W, H)[0] is True
    assert negatif_mi(alt, W, H)[0] is True


def test_kenarda_TEK_PIKSEL_gorunur_REDDEDILIR():
    """En kritik test: hedefin bir pikseli bile kadrajdaysa negatif OLAMAZ."""
    uvs = _kp((-40.0, 500.0), (1.0, 520.0))      # sag kenari x=1 -> icerde
    guvenli, sebep = negatif_mi(uvs, W, H, marj_x=0.0, marj_y=0.0, kenar_pay=0.0)
    assert not guvenli and sebep == "kadrajda"


def test_kenar_payi_supheliyi_reddeder():
    """Kutu kadrajin 3 px disinda ama pay 8 px -> guvenli DEGIL (temkinli).
    pay_oran=0 ile SADECE sabit kenar payi sinaniyor (oran ayri testte)."""
    uvs = _kp((-50.0, 500.0), (-3.0, 520.0))
    assert negatif_mi(uvs, W, H, 0.0, 0.0, kenar_pay=8.0, pay_oran=0.0)[0] is False
    assert negatif_mi(uvs, W, H, 0.0, 0.0, kenar_pay=0.0, pay_oran=0.0)[0] is True


def test_marj_sisirmesi_guvenlik_yonunde_calisir():
    """Sisirme kutuyu buyutur -> 'tamamen disarida' demek ZORLASIR.
    Yani marj artinca supheli kare negatif olmaktan CIKAR, tersi olmaz."""
    uvs = _kp((-120.0, 500.0), (-20.0, 600.0))   # w=100, h=100, sag kenar -20
    assert negatif_mi(uvs, W, H, 0.0, 0.0, kenar_pay=0.0, pay_oran=0.0)[0] is True
    # marj_x=0.30 -> sag kenar -20+30 = +10 -> kadraja girer -> reddedilir
    assert negatif_mi(uvs, W, H, 0.30, 0.0, kenar_pay=0.0, pay_oran=0.0)[0] is False


# ---------------------------------------------------------------- izgara_say
def test_izgara_kose_hucrelerini_ayirir():
    merkezler = [(10.0, 10.0)] * 3 + [(W - 10.0, H - 10.0)] * 2
    iz = izgara_say(merkezler, W, H, nx=6, ny=4)
    assert iz[0][0] == 3         # sol ust
    assert iz[3][5] == 2         # sag alt
    assert sum(sum(s) for s in iz) == 5


def test_izgara_kadraj_disi_merkez_kirpilir():
    """Guvenlik: tasan koordinat indeks hatasi vermemeli."""
    iz = izgara_say([(W + 500.0, H + 500.0), (-30.0, -30.0)], W, H, 6, 4)
    assert iz[3][5] == 1 and iz[0][0] == 1


def test_izgara_bos_giris():
    assert izgara_say([], W, H) == [[0] * 6 for _ in range(4)]


# ---------------------------------------------------------------- histogram
def test_histogram_binleri():
    kenarlar = [0.0, 0.5, 1.0]
    assert histogram([0.1, 0.4, 0.6, 0.9], kenarlar) == [2, 2]


def test_histogram_ust_sinir_son_bine_girer():
    assert histogram([1.0], [0.0, 0.5, 1.0]) == [0, 1]


# ------------------------------------------------------------ disarida_pay
def test_pay_arkadakiler_sonsuz_ve_eksi_sonsuz():
    from veriseti.negatif_topla import disarida_pay
    assert disarida_pay([None] * 6, W, H) == float("inf")
    uvs = _kp((900.0, 500.0)); uvs[0] = None
    assert disarida_pay(uvs, W, H) == float("-inf")   # kismen arkada = en riskli


def test_pay_disarida_pozitif_iceride_negatif():
    from veriseti.negatif_topla import disarida_pay
    dis = _kp((-200.0, 500.0), (-150.0, 520.0))       # sag kenar -150
    assert disarida_pay(dis, W, H, 0.0, 0.0) == 150.0
    ic = _kp((900.0, 500.0), (1000.0, 520.0))
    assert disarida_pay(ic, W, H, 0.0, 0.0) < 0


def test_pay_ile_negatif_mi_AYNI_karari_verir():
    """QA'da gosterilen sayi ile kararin kendisi ayrisamamali: karar tam olarak
    disarida_pay() > gerekli_pay() olmali, baska hicbir sey degil."""
    from veriseti.negatif_topla import disarida_pay, gerekli_pay
    for sag in (-60.0, -20.0, -8.0, -1.0, 5.0, 100.0):
        for oran in (0.0, 0.5):
            uvs = _kp((sag - 40.0, 500.0), (sag, 520.0))
            pay = disarida_pay(uvs, W, H, 0.0, 0.0)
            ger = gerekli_pay(uvs, W, H, 0.0, 0.0, 8.0, oran)
            guvenli = negatif_mi(uvs, W, H, 0.0, 0.0, 8.0, pay_oran=oran)[0]
            assert guvenli == (pay > ger), "sag=%s oran=%s pay=%s ger=%s" % (
                sag, oran, pay, ger)


def test_pay_siralamasi_en_riskliyi_basa_alir():
    """QA sirasi: kucuk pay = sinira yakin = once incelenmeli."""
    from veriseti.negatif_topla import disarida_pay
    yakin = _kp((-60.0, 500.0), (-10.0, 520.0))
    uzak = _kp((-900.0, 500.0), (-850.0, 520.0))
    p_yakin = disarida_pay(yakin, W, H, 0.0, 0.0)
    p_uzak = disarida_pay(uzak, W, H, 0.0, 0.0)
    assert p_yakin < p_uzak
    assert sorted([p_uzak, float("inf"), p_yakin])[0] == p_yakin


# ------------------------------------------------------------- gerekli_pay
def test_gerekli_pay_kutu_boyutuyla_olceklenir():
    """Hedef rotasyonu bozulabilen kanaldan gelir; hatasi hedef boyutuyla
    sinirlidir -> pay kutu boyutuna gore buyumeli."""
    from veriseti.negatif_topla import gerekli_pay
    kucuk = _kp((-100.0, 500.0), (-96.0, 504.0))     # 4x4 px (uzak hedef)
    buyuk = _kp((-900.0, 300.0), (-500.0, 700.0))    # 400x400 px (yakin hedef)
    assert gerekli_pay(kucuk, W, H, 0.0, 0.0, 8.0, 0.5) == 8.0     # sabit baglar
    assert gerekli_pay(buyuk, W, H, 0.0, 0.0, 8.0, 0.5) == 200.0   # oran baglar


def test_pay_oran_yakin_hedefi_sikilastirir():
    """Buyuk kutu kadrajin 50 px disinda: sabit pay yeterdi, oran REDDEDER."""
    uvs = _kp((-450.0, 300.0), (-50.0, 700.0))       # 400x400, sag kenar -50
    assert negatif_mi(uvs, W, H, 0.0, 0.0, 8.0, pay_oran=0.0)[0] is True
    assert negatif_mi(uvs, W, H, 0.0, 0.0, 8.0, pay_oran=0.5)[0] is False


def test_pay_oran_uzak_hedefi_etkilemez():
    """Kucuk kutu icin oran devreye girmez -> uzak negatifler kaybedilmez."""
    uvs = _kp((-100.0, 500.0), (-96.0, 504.0))       # 4x4, sag kenar -96
    assert negatif_mi(uvs, W, H, 0.0, 0.0, 8.0, pay_oran=0.5)[0] is True


def test_pay_oran_artinca_asla_gevsemez():
    """Monotonluk: oran buyudukce guvenli kume KUCULMELI (tersi olursa bug)."""
    uvs = _kp((-300.0, 300.0), (-100.0, 500.0))      # 200x200, sag kenar -100
    onceki = True
    for oran in (0.0, 0.25, 0.5, 0.75, 1.0):
        simdi = negatif_mi(uvs, W, H, 0.0, 0.0, 8.0, pay_oran=oran)[0]
        assert not (simdi and not onceki), "oran %.2f'de gevsedi" % oran
        onceki = simdi
