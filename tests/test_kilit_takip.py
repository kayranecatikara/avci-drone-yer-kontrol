# -*- coding: utf-8 -*-
"""
KILITLENME ISTERI SAYACI + gorsel kayip yonetimi dogrulama (oyunsuz) — sartname 6.1.2/6.1.4.

2026-07-07: eski PN/alt-FSM testleri (TAKIP menzil-tutma, commit-freeze, yapiskan
kayip, soft-start) yasayla birlikte SILINDI. Kalanlar basit-IBVS mimarisine gore:

Test edilenler:
  1) Kilit kosulu: hedef merkezi AV icinde (yatay %25-75, dikey %10-90) VE bbox
     EN AZ BIR eksende >= VIS_LOCK_PCT (tek eksen yeter).
  2) 10 sn pencere aritmetigi: kumulatif >= 5 sn (kesintili sayilir; sartname
     ornegi 1+2+2 sn), pencere disina dusen eski kilitler SAYILMAZ.
  3) Sayac SALT GOZLEM: kilit_ok latch'i olsun olmasin AYNI tespit AYNI komutu
     uretir (tek yasa; vurus fazi/izin kapisi yok).
  4) Kayip yonetimi: tespit yokken HOVER; VIS_LOST_TO_GPS_S asilinca (yalniz
     revert_izin=True/OTO) GPS'e doner (None + durum=ARAMA); manuel GORSEL'de
     asla donmez; revert'te kilit_ok latch'i KORUNUR.

Calistirma:  python tests/test_kilit_takip.py     (pytest de calisir)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidance.ana_kontrol import AvciKontrol, Cfg

# Kilit/kopru testleri yumusak-gecis rampasini KAPALI test eder: bu testler kopru/kilit
# davranisini dogrular, handoff rampasini DEGIL. Rampa acikken taze beyinde ilk gorsel tik
# s=0 (ileri~0) olur; gercek ucusta kopru ~1sn rampa dolduktan SONRA olur. Rampa ayri
# olarak test_ibvs_gorsel.test_handoff_* ile dogrulanir.
Cfg.IBVS_HANDOFF_S = 0.0

W, H = 1920.0, 1080.0


def _beyin():
    """Drone'suz beyin: bu testler yalniz _kilit_degerlendir/_gorsel_guduum kullanir
    (ikisi de drone'a dokunmaz; girdiler parametreyle gelir)."""
    return AvciKontrol(drone=None, debug_olc=False, kaynak="gercek")


def _det(cxn=0.5, cyn=0.5, wp=0.08, hp=0.04, t=0.0, conf=0.9):
    """Normalize merkez/boyut oranlarindan piksel-cinsi sentetik det."""
    return {"cx": cxn * W, "cy": cyn * H, "w": wp * W, "h": hp * H,
            "conf": conf, "cls": 0, "W": W, "H": H, "t": t}


# ---------------------------------------------------------------------------
#  1) Kilit kosulu
# ---------------------------------------------------------------------------
def test_kilit_kosulu_tek_eksen_yeter():
    b = _beyin()
    # yatay %7, dikey %3 -> tek eksen esigi (%6) asiyor -> KILIT VAR
    assert b._kilit_degerlendir(_det(wp=0.07, hp=0.03), 0.0) is True
    # iki eksen de %4 -> KILIT YOK
    b2 = _beyin()
    assert b2._kilit_degerlendir(_det(wp=0.04, hp=0.04), 0.0) is False


def test_kilit_kosulu_av_siniri():
    # merkez x=%24 -> AV disi (sinir %25) -> kilit yok; x=%26 -> var
    assert _beyin()._kilit_degerlendir(_det(cxn=0.24, wp=0.08), 0.0) is False
    assert _beyin()._kilit_degerlendir(_det(cxn=0.26, wp=0.08), 0.0) is True
    # dikey sinir: y=%8 -> disi; y=%12 -> ici
    assert _beyin()._kilit_degerlendir(_det(cyn=0.08, wp=0.08), 0.0) is False
    assert _beyin()._kilit_degerlendir(_det(cyn=0.12, wp=0.08), 0.0) is True


def test_kilit_kosulu_tespit_yok():
    b = _beyin()
    assert b._kilit_degerlendir(None, 0.0) is False
    assert b.kilit_boyut is None


# ---------------------------------------------------------------------------
#  2) Pencere aritmetigi
# ---------------------------------------------------------------------------
def _pencere_kos(b, araliklar, t_son, hz=50.0):
    """araliklar: kilitli (t0,t1) listesi; 0..t_son boyunca hz'de ornekle."""
    dt = 1.0 / hz
    n = int(round(t_son / dt))
    for i in range(n + 1):
        t = i * dt
        kilitli = any(a <= t < z for a, z in araliklar)
        b._kilit_degerlendir(_det() if kilitli else None, t)


def test_pencere_sartname_ornegi_kesintili_5sn():
    # sartname 6.1.4 ornegi: 1-2 (1 sn) + 3-5 (2 sn) + 6-8 (2 sn) = 5 sn -> GECERLI
    b = _beyin()
    _pencere_kos(b, [(1.0, 2.0), (3.0, 5.0), (6.0, 8.1)], t_son=8.2)
    assert b.kilit_ok is True, "kesintili 5 sn kumulatif kilit gecerli sayilmali"


def test_pencere_yetersiz_kilit():
    # toplam ~4.5 sn < 5 sn -> ISTER SAGLANMAZ
    b = _beyin()
    _pencere_kos(b, [(1.0, 3.0), (4.0, 6.5)], t_son=9.9)
    assert b.kilit_ok is False
    assert 4.0 < b.kilit_sure < 5.0


def test_pencere_eski_kilitler_dusuyor():
    # 0-4 sn kilit (4 sn, latch YOK), sonra 12 sn bosluk: pencere disinda kalan
    # kilitler sayilmamali -> kilit_sure ~0
    b = _beyin()
    _pencere_kos(b, [(0.0, 4.0)], t_son=16.0)
    assert b.kilit_ok is False
    assert b.kilit_sure < 0.2, "pencere disindaki eski kilit sayildi: %.2f" % b.kilit_sure


# ---------------------------------------------------------------------------
#  3) Sayac SALT GOZLEM (gudume karismaz)
# ---------------------------------------------------------------------------
def test_kilit_salt_gozlem_komutu_degistirmez():
    """kilit_ok latch'i olsun olmasin ayni tespit AYNI komutu uretmeli (tek yasa)."""
    d = _det(cxn=0.7, cyn=0.4, wp=0.10, hp=0.05, t=1.0)
    b1 = _beyin(); b1.durum = "GORSEL_GUDUM"
    k1 = b1._gorsel_guduum(dict(d), 1.0)
    b2 = _beyin(); b2.durum = "GORSEL_GUDUM"; b2.kilit_ok = True
    k2 = b2._gorsel_guduum(dict(d), 1.0)
    assert k1 == k2, "kilit_ok komutu degistirdi (salt gozlem olmali): %s vs %s" % (k1, k2)


# ---------------------------------------------------------------------------
#  4) Kayip yonetimi: hover -> GPS revert
# ---------------------------------------------------------------------------
def _kayip_kos(b, t_bas, sure_s, revert_izin=True):
    """t_bas'tan itibaren sure_s boyunca None (kayip) besle; GPS'e dondu mu dondur."""
    t = t_bas
    for _ in range(int(sure_s / Cfg.DT) + 1):
        t += Cfg.DT
        r = b._gorsel_guduum(None, t, revert_izin=revert_izin)
        if r is None:
            return True, t - t_bas          # GPS'e dondu
    return False, t - t_bas


def test_kayipta_hover_sonra_gps_revert():
    # VIS_LOST_TO_GPS_S > 0 secilirse: once hover, sure asilinca GPS'e don
    eski = Cfg.VIS_LOST_TO_GPS_S
    Cfg.VIS_LOST_TO_GPS_S = 2.0
    try:
        b = _beyin(); b.durum = "GORSEL_GUDUM"
        b._gorsel_guduum(_det(t=0.0), 0.0)
        # kisa kayip: HOVER komutu (0,0,0,0), GPS'e donmez
        r = b._gorsel_guduum(None, 0.02)
        assert r == (0.0, 0.0, 0.0, 0.0), "kisa kayipta hover bekleniyordu: %s" % (r,)
        assert b.durum == "GORSEL_GUDUM"
        # uzun kayip: VIS_LOST_TO_GPS_S asilinca None + ARAMA
        reverted, sure = _kayip_kos(b, 0.02, Cfg.VIS_LOST_TO_GPS_S + 1.0)
        assert reverted, "uzun kayipta GPS'e donmeliydi"
        assert b.durum == "ARAMA"
        assert sure > Cfg.VIS_LOST_TO_GPS_S - 0.1, "cok erken revert: %.2f s" % sure
    finally:
        Cfg.VIS_LOST_TO_GPS_S = eski


def test_kayipta_sifir_aninda_gps():
    """VIS_LOST_TO_GPS_S=0 (yeni default): kayipta HOVER YOK, ILK tikte GPS'e don.
    (Kullanici istegi 2026-07-08: ara hover beklemesi kafa karistiriyordu; dedektor
    titremesini zaten VIS_STALE_S koprusu emer — buraya dusen gercek kayiptir.)"""
    eski = Cfg.VIS_LOST_TO_GPS_S
    Cfg.VIS_LOST_TO_GPS_S = 0.0
    try:
        b = _beyin(); b.durum = "GORSEL_GUDUM"
        b._gorsel_guduum(_det(t=0.0), 0.0)
        r = b._gorsel_guduum(None, 0.02)     # ilk kayip tiki
        assert r is None, "aninda GPS'e donmeliydi (None), gelen: %s" % (r,)
        assert b.durum == "ARAMA"
    finally:
        Cfg.VIS_LOST_TO_GPS_S = eski


def test_manuel_gorselde_gps_revert_yok():
    """revert_izin=False (manuel GORSEL switch): kayip ne kadar uzarsa uzasin hover."""
    b = _beyin(); b.durum = "GORSEL_GUDUM"
    b._gorsel_guduum(_det(t=0.0), 0.0)
    reverted, _ = _kayip_kos(b, 0.0, Cfg.VIS_LOST_TO_GPS_S + 2.0, revert_izin=False)
    assert not reverted, "manuel GORSEL'de GPS'e DONMEMELIYDI"
    assert b.durum == "GORSEL_GUDUM"


def test_revert_kilit_ok_latch_korunur():
    """GPS'e donuste kilit penceresi temizlenir ama kilit_ok latch'i KORUNUR."""
    b = _beyin(); b.durum = "GORSEL_GUDUM"; b.kilit_ok = True
    _kayip_kos(b, 0.0, Cfg.VIS_LOST_TO_GPS_S + 1.0)
    assert b.durum == "ARAMA"
    assert b.kilit_ok is True, "revert kilit_ok latch'ini dusurmemeli"
    assert b.kilit_sure == 0.0 and len(b.kilit_win) == 0


# ---------------------------------------------------------------------------
#  5) GORUNTU-DUZLEMI KOPRU (olu-hesap): dedektor deliginde sanal bbox
# ---------------------------------------------------------------------------
import time as _time


def _kopru_beyin(yas_s, vx_px=200.0, vy_px=0.0, wp=0.08, hp=0.04):
    """GORSEL_GUDUM'da beyin: son GERCEK tespit 'yas_s' saniye once, hiz olculmus."""
    b = _beyin(); b.durum = "GORSEL_GUDUM"
    now = _time.perf_counter()
    b.son_tespit = _det(cxn=0.5, cyn=0.5, wp=wp, hp=hp, t=now - yas_s)
    b.son_tespit_t = now - yas_s
    b._vis_v = (vx_px, vy_px)
    return b


def test_kopru_sentetik_tespit_uretir():
    """Bayat tespit + hiz var -> oku KOPRU det dondurur; cx hiz*yas kadar ilerlemis,
    cy ise DONMUS (dikey ekstrapole edilmez: olculen vy cogunlukla ego-pitch urunu;
    8 Tem kacak-tirmanma dersi)."""
    yas = Cfg.VIS_STALE_S + 0.4                    # stale asildi, kopru penceresi icinde
    b = _kopru_beyin(yas, vx_px=200.0, vy_px=300.0)
    d = b._gorsel_tespit_oku()
    assert d is not None and d.get("kopru") is True, "kopru det bekleniyordu: %s" % (d,)
    assert b.vis_kopru is True
    beklenen = 0.5 * W + 200.0 * yas
    assert abs(d["cx"] - beklenen) < 1.0, "cx hizla ilerlemeliydi: %.1f vs %.1f" % (d["cx"], beklenen)
    assert abs(d["cy"] - 0.5 * H) < 1e-6, "cy DONMALIYDI (vy uygulanmaz): %.1f" % d["cy"]
    # kopru det ile gorsel yasa KOMUT uretir (revert/hover degil) ve faz korunur;
    # DIKEY komut koprude 0 (irtifa-tut) — tahminle tirmanis/alcalis entegre edilmez.
    r = b._gorsel_guduum(d, 0.0)
    assert r is not None and b.durum == "GORSEL_GUDUM"
    assert r[0] == 0.0, "koprude thr=0 (irtifa-tut) bekleniyordu: %s" % (r,)
    assert b.ibvs_tlm.get("dikey") == 0.0


def test_kopru_kilit_sayaci_saymaz():
    """DURUSTLUK: kopru tikleri kilit penceresine SURE BIRIKTIRMEZ."""
    b = _kopru_beyin(Cfg.VIS_STALE_S + 0.2)
    d = b._gorsel_tespit_oku()
    assert d is not None and d.get("kopru")
    for i in range(50):                            # 1 sn kopru tiki isle
        b._gorsel_guduum(dict(d), i * Cfg.DT)
    assert b.kilit_sure == 0.0, "kopru kilit biriktirdi: %.2f" % b.kilit_sure
    assert b.kilit_anlik is False


def test_kopru_bitince_kayip_mantigi():
    """Kopru suresi de dolunca oku None -> (LOST=0 default) ilk tikte GPS'e don."""
    yas = Cfg.VIS_STALE_S + float(Cfg.VIS_KOPRU_S) + 0.2
    b = _kopru_beyin(yas)
    assert b._gorsel_tespit_oku() is None, "kopru penceresi disinda None beklenirdi"
    eski = Cfg.VIS_LOST_TO_GPS_S
    Cfg.VIS_LOST_TO_GPS_S = 0.0
    try:
        assert b._gorsel_guduum(None, 0.02) is None and b.durum == "ARAMA"
    finally:
        Cfg.VIS_LOST_TO_GPS_S = eski


def test_kopru_hiz_yoksa_ve_fazdisi_kapali():
    """Hiz olculmemisse ya da GORSEL_GUDUM disindaysa kopru DEVREYE GIRMEZ."""
    yas = Cfg.VIS_STALE_S + 0.3
    b = _kopru_beyin(yas); b._vis_v = None
    assert b._gorsel_tespit_oku() is None, "hiz yokken kopru olmamali"
    b2 = _kopru_beyin(yas); b2.durum = "ARAMA"     # OTO kilit sayaci sismesin
    assert b2._gorsel_tespit_oku() is None, "ARAMA'da kopru olmamali"


def test_kopru_boyut_donuk():
    """Koprude w/h DONUK -> boyut istegi son gercek olcumde kalir; ileri surer, thr=0."""
    # bbox hedefin (BOYUT_HEDEF=0.08) ALTINDA (0.04) -> boyut yasasi ileri surmeli.
    b = _kopru_beyin(Cfg.VIS_STALE_S + 0.3, wp=0.04, hp=0.02)
    d = b._gorsel_tespit_oku()
    assert d is not None and d.get("kopru")
    r = b._gorsel_guduum(d, 0.0)
    assert b.ibvs_tlm.get("boyut") == 0.04, "koprude boyut donuk kalmali: %s" % b.ibvs_tlm.get("boyut")
    assert r[1] > 0, "boyut<hedef -> koprude ileri surmeli (yatay takip): %s" % (r,)
    assert r[0] == 0.0, "koprude dikey-tut (thr=0)"


def test_kopru_hiz_ema_gercek_tespitten():
    """set_gorsel_tespit ardisik GERCEK tespitlerden hiz cikarir (isaret dogru);
    uzun delik sonrasi ilk tespit hizi SIFIRLAR (bayat hizla kopru kurulmaz)."""
    b = _beyin()
    t0 = _time.perf_counter()
    b.set_gorsel_tespit(_det(cxn=0.50, t=t0))
    b.set_gorsel_tespit(_det(cxn=0.52, t=t0 + 0.1))          # saga hareket
    assert b._vis_v is not None and b._vis_v[0] > 0, "saga hiz bekleniyordu: %s" % (b._vis_v,)
    b.set_gorsel_tespit(_det(cxn=0.60, t=t0 + 0.1 + Cfg.VIS_STALE_S + 1.0))  # uzun delik
    assert b._vis_v is None, "uzun delik sonrasi hiz sifirlanmali"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    gecen = 0
    for n, f in fns:
        try:
            f()
            print("OK  " + n)
            gecen += 1
        except AssertionError as e:
            print("FAIL " + n + " -> " + str(e))
        except Exception as e:
            print("ERR  " + n + " -> " + repr(e))
    print("\n%d/%d test gecti." % (gecen, len(fns)))
    sys.exit(0 if gecen == len(fns) else 1)
