# -*- coding: utf-8 -*-
"""veriseti/onar.py karar mantigi.

Bu fonksiyon EGITIM ETIKETINI degistirebiliyor ya da kareyi ATABILIYOR.
Yanlis bir "onarim" sessizce bozuk etiket uretir; testler ozellikle
MUDAHALE ETMEME tarafini kovaliyor -- supheli olmak tek basina yetmemeli.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veriseti.onar import onar_karari, ONAR, SIL, BIRAK

ESIK = 3.67          # denetimin insan dagilimindan ogrendigi kontrast esigi
KUTU = [100.0, 100.0, 200.0, 160.0]


def test_etiket_DOLU_ise_dokunma():
    """Kontrast iyiyse etiket muhtemelen dogru -> dedektor ne derse desin BIRAK."""
    k, s = onar_karari(9.0, KUTU, 12.0, 0.95, 0.0, ESIK)
    assert k == BIRAK and s == "etiket_dolu_gorunuyor"


def test_bos_kutu_dedektor_dolu_ve_ayrik_ONAR():
    k, s = onar_karari(0.4, KUTU, 11.0, 0.85, 0.02, ESIK)
    assert k == ONAR


def test_bos_kutu_dedektor_YOK_SIL():
    """Ne projeksiyon ne dedektor bir sey gosteriyor -> karede ne oldugu bilinmiyor."""
    k, s = onar_karari(0.3, None, None, None, None, ESIK)
    assert k == SIL and s == "kutu_bos_ve_dedektor_bulamadi"


def test_bos_kutu_dedektor_GUVENSIZ_SIL():
    k, _ = onar_karari(0.3, KUTU, 10.0, 0.35, 0.01, ESIK)
    assert k == SIL


def test_bos_kutu_dedektor_kutusu_da_BOS_SIL():
    """Dedektor bir sey buldu ama onun kutusu da bos -> kurtarilacak bilgi yok."""
    k, s = onar_karari(0.3, KUTU, 0.6, 0.90, 0.01, ESIK)
    assert k == SIL and s == "kutu_bos_ve_dedektor_kutusu_da_bos"


def test_kutular_AYNI_YERDEYSE_onarma():
    """Ikisi ayni yeri gosteriyorsa 'onarim' bir sey degistirmez, sadece
    olcum gurultusudur -> mudahale etme."""
    k, s = onar_karari(0.3, KUTU, 9.0, 0.90, 0.75, ESIK)
    assert k == BIRAK and s == "kutular_zaten_ayni_yerde"


def test_sinir_kontrast_esikte_DOLU_sayilir():
    """Tam esikte olan kutu bos SAYILMAZ (temkinli taraf)."""
    assert onar_karari(ESIK, KUTU, 9.0, 0.9, 0.0, ESIK)[0] == BIRAK
    assert onar_karari(ESIK - 0.01, KUTU, 9.0, 0.9, 0.0, ESIK)[0] == ONAR


def test_conf_esigi_tam_sinirda_onarir():
    assert onar_karari(0.3, KUTU, 9.0, 0.60, 0.0, ESIK, conf_esik=0.60)[0] == ONAR
    assert onar_karari(0.3, KUTU, 9.0, 0.59, 0.0, ESIK, conf_esik=0.60)[0] == SIL


def test_kontrast_olculemezse_dokunma():
    """Olcum yoksa hukum yok -- 'bilinmiyor' ile 'bos' ayni sey degil."""
    assert onar_karari(None, KUTU, 9.0, 0.9, 0.0, ESIK)[0] == BIRAK


def test_iou_bilinmiyorsa_onarim_engellenmez():
    """proj kutusu yoksa IoU hesaplanamaz; diger kanitlar yeterliyse onar."""
    assert onar_karari(-1.0, KUTU, 10.0, 0.9, None, ESIK)[0] == ONAR


def test_karar_kumesi_kapali():
    """Fonksiyon her zaman uc karardan birini dondurmeli."""
    for pk in (None, -1.0, 0.0, 3.0, 3.67, 20.0):
        for dk in (None, KUTU):
            for dc in (None, 0.1, 0.6, 0.99):
                for dkon in (None, 0.5, 9.0):
                    for io in (None, 0.0, 0.5, 1.0):
                        k, _ = onar_karari(pk, dk, dkon, dc, io, ESIK)
                        assert k in (ONAR, SIL, BIRAK)
