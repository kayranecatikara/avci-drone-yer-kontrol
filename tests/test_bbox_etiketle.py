# -*- coding: utf-8 -*-
"""veriseti/bbox_etiketle.py saf cekirdegi (tkinter'siz test edilebilen kisim).

Kritik degismezler:
  - YOLO yaz/oku TUR-DONUSU (yazdigini geri okuyunca ayni kutu)
  - etiketli/etiketsiz ayrimi DOSYA BOYUTUNDAN (ayri durum dosyasi yok)
  - kare sirasi NUMARAYA gore (sozluk sirasi 10'u 9'dan once koyardi)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.bbox_etiketle import (yolo_satiri, yolo_oku, kutu_kirp, kutu_gecerli,
                                kutu_tasi, orta_kutu, etiketli_mi, kare_listesi,
                                sonraki_etiketsiz)

W, H = 1920, 1080


# ------------------------------------------------------------------- YOLO
def test_yolo_tur_donusu():
    """Yaz -> oku ayni kutuyu vermeli (etiketi tekrar duzenlerken sart)."""
    kutu = [100.0, 200.0, 340.0, 500.0]
    geri = yolo_oku(yolo_satiri(kutu, W, H), W, H)
    for a, b in zip(kutu, geri):
        assert abs(a - b) < 0.01


def test_yolo_satiri_normalize_ve_sinif_sifir():
    s = yolo_satiri([0.0, 0.0, float(W), float(H)], W, H)
    p = s.split()
    assert p[0] == "0"
    assert abs(float(p[1]) - 0.5) < 1e-6 and abs(float(p[2]) - 0.5) < 1e-6
    assert abs(float(p[3]) - 1.0) < 1e-6 and abs(float(p[4]) - 1.0) < 1e-6


def test_yolo_satiri_ters_koseleri_duzeltir():
    """Sag-alttan sol-uste surukleme de gecerli kutu vermeli."""
    duz = yolo_satiri([100.0, 200.0, 340.0, 500.0], W, H)
    ters = yolo_satiri([340.0, 500.0, 100.0, 200.0], W, H)
    assert duz == ters


def test_yolo_oku_bos_ve_bozuk():
    assert yolo_oku("", W, H) is None
    assert yolo_oku("0 0.5", W, H) is None
    assert yolo_oku("0 a b c d", W, H) is None


# ------------------------------------------------------------------- kutu
def test_kirp_sinirlara_oturur():
    assert kutu_kirp([-50.0, -20.0, W + 99.0, H + 5.0], W, H) == [0, 0, W, H]


def test_kirp_kose_sirasini_duzeltir():
    assert kutu_kirp([300.0, 400.0, 100.0, 200.0], W, H) == [100, 200, 300, 400]


def test_gecerli_kucuk_kutuyu_reddeder():
    assert kutu_gecerli([100.0, 100.0, 140.0, 140.0], W, H) is True
    assert kutu_gecerli([100.0, 100.0, 101.0, 140.0], W, H) is False
    assert kutu_gecerli(None, W, H) is False


def test_gecerlilik_KIRPMA_SONRASI_bakilir():
    """Kadraj disinda genis gorunen kutu, kirpilinca yok olabilir."""
    assert kutu_gecerli([-500.0, 100.0, -1.0, 300.0], W, H) is False


def test_tasi_kadrajda_tutar_ve_boyutu_korur():
    kutu = [100.0, 100.0, 300.0, 260.0]
    tasinan = kutu_tasi(list(kutu), -9999.0, -9999.0, W, H)
    assert tasinan[0] == 0.0 and tasinan[1] == 0.0
    assert (tasinan[2] - tasinan[0]) == (kutu[2] - kutu[0])
    assert (tasinan[3] - tasinan[1]) == (kutu[3] - kutu[1])
    sag = kutu_tasi(list(kutu), 9999.0, 9999.0, W, H)
    assert sag[2] == float(W) and sag[3] == float(H)


def test_orta_kutu_merkezde():
    k = orta_kutu(W, H, 0.10)
    assert abs((k[0] + k[2]) / 2 - W / 2) < 1e-6
    assert abs((k[1] + k[3]) / 2 - H / 2) < 1e-6
    assert abs((k[2] - k[0]) - W * 0.10) < 1e-6


# --------------------------------------------------------------- dosya durumu
def test_etiketli_mi_dosya_boyutundan(tmp_path):
    bos = tmp_path / "a.txt"; bos.write_text("")
    dolu = tmp_path / "b.txt"; dolu.write_text("0 0.5 0.5 0.1 0.1\n")
    assert etiketli_mi(str(bos)) is False
    assert etiketli_mi(str(dolu)) is True
    assert etiketli_mi(str(tmp_path / "yok.txt")) is False


def test_kare_listesi_NUMARA_sirasinda(tmp_path):
    """Sozluk sirasi talon1_0010'u talon1_0009'dan once koyardi -> numara sart."""
    for i in (0, 1, 2, 9, 10, 11, 100):
        (tmp_path / ("talon1_%04d.png" % i)).write_text("x")
    (tmp_path / "baska_0000.png").write_text("x")     # baska on ek: alinmamali
    liste = kare_listesi(str(tmp_path), "talon1")
    adlar = [os.path.basename(p) for p in liste]
    assert adlar == ["talon1_0000.png", "talon1_0001.png", "talon1_0002.png",
                     "talon1_0009.png", "talon1_0010.png", "talon1_0011.png",
                     "talon1_0100.png"]


def test_sonraki_etiketsiz_ileri_arar(tmp_path):
    yollar = []
    for i, dolu in enumerate([True, True, False, True, False]):
        p = tmp_path / ("t_%d.txt" % i)
        p.write_text("0 0.5 0.5 0.1 0.1\n" if dolu else "")
        yollar.append(str(p))
    assert sonraki_etiketsiz(yollar, 0) == 2
    assert sonraki_etiketsiz(yollar, 3) == 4


def test_sonraki_etiketsiz_basa_sarar(tmp_path):
    yollar = []
    for i, dolu in enumerate([False, True, True]):
        p = tmp_path / ("t_%d.txt" % i)
        p.write_text("0 0.5 0.5 0.1 0.1\n" if dolu else "")
        yollar.append(str(p))
    assert sonraki_etiketsiz(yollar, 2) == 0      # sondan basa sarmali


def test_sonraki_etiketsiz_hepsi_etiketliyse_None(tmp_path):
    yollar = []
    for i in range(3):
        p = tmp_path / ("t_%d.txt" % i)
        p.write_text("0 0.5 0.5 0.1 0.1\n")
        yollar.append(str(p))
    assert sonraki_etiketsiz(yollar, 0) is None


# ------------------------------------------------ truth projeksiyonu on-doldurma
def test_projeksiyon_truth_yoksa_None():
    from veriseti.bbox_etiketle import projeksiyon_kutusu
    assert projeksiyon_kutusu(None) is None
    assert projeksiyon_kutusu({}) is None
    assert projeksiyon_kutusu({"W": W, "H": H, "truth_target_pos": None}) is None


def test_telemetri_oku_bozuk_satiri_atlar(tmp_path):
    from veriseti.bbox_etiketle import telemetri_oku
    (tmp_path / "telemetri.jsonl").write_text(
        '{"kare":"talon1_0000.png","W":1920,"H":1080}\n'
        'YARIM SATIR{\n'
        '\n'
        '{"kare":"talon1_0001.png","W":1920,"H":1080}\n'
        '{"kare_yok":1}\n', encoding="utf-8")
    d = telemetri_oku(str(tmp_path))
    assert set(d) == {"talon1_0000.png", "talon1_0001.png"}


def test_telemetri_oku_dosya_yoksa_bos(tmp_path):
    from veriseti.bbox_etiketle import telemetri_oku
    assert telemetri_oku(str(tmp_path)) == {}


# --------------------------------------------------- tus tekrari kisitlamasi
def test_gezinme_kabul_hizli_tekrari_eler():
    """Windows tus tekrari ~30/sn; kare yukleme ~15/sn -> fark kuyruga birikip
    liste sonuna firlatiyordu. Kapi 0.08 sn'den sik olani yutmali."""
    from veriseti.bbox_etiketle import gezinme_kabul
    assert gezinme_kabul(1.00, 0.00) is True      # ilk hareket
    assert gezinme_kabul(1.02, 1.00) is False     # 20 ms sonra -> yut
    assert gezinme_kabul(1.09, 1.00) is True      # 90 ms sonra -> kabul


def test_gezinme_kabul_sinir():
    from veriseti.bbox_etiketle import gezinme_kabul
    assert gezinme_kabul(0.08, 0.0, 0.08) is True     # tam sinir kabul
    assert gezinme_kabul(0.079, 0.0, 0.08) is False


# ------------------------------------------------------- tutamac klavye itme
def test_tutamac_kose_iki_eksende_hareket():
    from veriseti.bbox_etiketle import tutamac_tasi, TUT_SOL_UST, TUT_SAG_ALT
    k = [100.0, 100.0, 300.0, 260.0]
    assert tutamac_tasi(k, TUT_SOL_UST, -5, -7, W, H) == [95.0, 93.0, 300.0, 260.0]
    assert tutamac_tasi(k, TUT_SAG_ALT, 5, 7, W, H) == [100.0, 100.0, 305.0, 267.0]


def test_tutamac_kenar_TEK_eksende_hareket():
    """Ust tutamac yatay itmeye TEPKISIZ olmali (yoksa kenar surukleyince kutu kayar)."""
    from veriseti.bbox_etiketle import tutamac_tasi, TUT_UST, TUT_SOL
    k = [100.0, 100.0, 300.0, 260.0]
    assert tutamac_tasi(k, TUT_UST, 99, -10, W, H) == [100.0, 90.0, 300.0, 260.0]
    assert tutamac_tasi(k, TUT_SOL, -10, 99, W, H) == [90.0, 100.0, 300.0, 260.0]


def test_tutamac_kutuyu_TERS_CEVIREMEZ():
    """Karsi kenari gecmeye calisirsa asgari genislik kala durmali."""
    from veriseti.bbox_etiketle import tutamac_tasi, TUT_SOL, TUT_ALT, ASGARI_PX
    k = [100.0, 100.0, 200.0, 200.0]
    r = tutamac_tasi(k, TUT_SOL, 9999, 0, W, H)
    assert r[0] == 200.0 - ASGARI_PX and r[2] == 200.0
    r = tutamac_tasi(k, TUT_ALT, 0, -9999, W, H)
    assert r[3] == 100.0 + ASGARI_PX and r[1] == 100.0


def test_tutamac_kadraj_disina_TASMAZ():
    from veriseti.bbox_etiketle import tutamac_tasi, TUT_SOL_UST, TUT_SAG_ALT
    k = [10.0, 10.0, 300.0, 260.0]
    assert tutamac_tasi(k, TUT_SOL_UST, -9999, -9999, W, H)[:2] == [0.0, 0.0]
    k = [10.0, 10.0, float(W) - 5, float(H) - 5]
    r = tutamac_tasi(k, TUT_SAG_ALT, 9999, 9999, W, H)
    assert r[2] == float(W) and r[3] == float(H)


def test_tus_haritasi_kullanicinin_dizilimi():
    """Kullanicinin tarif ettigi dizilim birebir korunmali."""
    from veriseti.bbox_etiketle import TUS_TUTAMAC, TUTAMAC_AD
    bekle = {"a": "sol ust", "w": "ust", "d": "sag ust",
             "q": "sol", "e": "sag",
             "z": "sol alt", "s": "alt", "x": "sag alt"}
    assert {t: TUTAMAC_AD[i] for t, i in TUS_TUTAMAC.items()} == bekle


def test_tus_haritasi_8_ayri_tutamac():
    from veriseti.bbox_etiketle import TUS_TUTAMAC
    assert len(TUS_TUTAMAC) == 8 and len(set(TUS_TUTAMAC.values())) == 8


# ------------------------------------------------------------- Tab (dikkat)
def test_sonraki_dikkat_bos_etiketi_bulur():
    from veriseti.bbox_etiketle import sonraki_dikkat
    bayrak = [True, True, False, True]
    assert sonraki_dikkat(bayrak, [0, 0, 0, 0], 0) == 2


def test_sonraki_dikkat_banka_karesini_bulur():
    """Etiketli ama hedef bankada -> goz gerekir."""
    from veriseti.bbox_etiketle import sonraki_dikkat
    bayrak = [True] * 5
    assert sonraki_dikkat(bayrak, [0, 5, 45, 3, 2], 0) == 2


def test_sonraki_dikkat_ILERI_gider_geri_donmez():
    """Kullanici sirayla ilerliyor; Tab onu geriye atmamali (sarma haric)."""
    from veriseti.bbox_etiketle import sonraki_dikkat
    bayrak = [True] * 6
    rolls = [45, 0, 0, 45, 0, 0]
    assert sonraki_dikkat(bayrak, rolls, 1) == 3        # 0'a degil 3'e
    assert sonraki_dikkat(bayrak, rolls, 4) == 0        # sonda basa SARAR


def test_sonraki_dikkat_temiz_sette_None():
    from veriseti.bbox_etiketle import sonraki_dikkat
    assert sonraki_dikkat([True] * 4, [0, 1, 2, 3], 0) is None


def test_sonraki_dikkat_roll_None_gormezden_gelinir():
    """Telemetrisi olmayan kare banka yuzunden isaretlenmemeli."""
    from veriseti.bbox_etiketle import sonraki_dikkat
    assert sonraki_dikkat([True] * 3, [None, None, None], 0) is None


# ------------------------------------------------------------- kare silme
def test_silme_hedefi_alt_klasore_gider():
    from veriseti.bbox_etiketle import silme_hedefi, SILINEN_DIR
    hp, ht = silme_hedefi(os.path.join("C:", "ds", "talon1_0042.png"),
                          os.path.join("C:", "ds"))
    assert os.path.basename(hp) == "talon1_0042.png"
    assert os.path.basename(ht) == "talon1_0042.txt"
    assert os.path.basename(os.path.dirname(hp)) == SILINEN_DIR
    assert os.path.dirname(hp) == os.path.dirname(ht)


def test_silme_hedefi_kaynagin_USTUNE_yazmaz():
    """Hedef, kaynakla ayni yol OLMAMALI (yoksa tasima dosyayi yok eder)."""
    from veriseti.bbox_etiketle import silme_hedefi
    kaynak = os.path.join("C:", "ds", "talon1_0001.png")
    hp, _ = silme_hedefi(kaynak, os.path.join("C:", "ds"))
    assert os.path.normpath(hp) != os.path.normpath(kaynak)


# ------------------------------------------------- dosya numarasi -> indeks
def test_kare_no_indeksi_silinme_sonrasi_dogru_bulur():
    """Kare silinince sira ile numara ayrisir; arama NUMARAYA gore olmali."""
    from veriseti.bbox_etiketle import kare_no_indeksi
    kareler = ["d/talon1_0000.png", "d/talon1_0001.png",
               "d/talon1_0003.png", "d/talon1_0004.png"]   # 0002 silinmis
    assert kare_no_indeksi(kareler, "talon1", 3) == 2      # sira 2, numara 3
    assert kare_no_indeksi(kareler, "talon1", 0) == 0
    assert kare_no_indeksi(kareler, "talon1", 4) == 3


def test_kare_no_indeksi_olmayan_numara_None():
    from veriseti.bbox_etiketle import kare_no_indeksi
    kareler = ["d/talon1_0000.png", "d/talon1_0003.png"]
    assert kare_no_indeksi(kareler, "talon1", 2) is None
