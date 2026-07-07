# -*- coding: utf-8 -*-
"""
KILITLENME/TAKIP alt-FSM dogrulama (oyunsuz) — sartname 6.1.2 / 6.1.4.

Test edilenler:
  1) Kilit kosulu: hedef merkezi AV icinde (yatay %25-75, dikey %10-90) VE bbox
     EN AZ BIR eksende >= VIS_LOCK_PCT (tek eksen yeter).
  2) 10 sn pencere aritmetigi: kumulatif >= 5 sn (kesintili sayilir; sartname
     ornegi 1+2+2 sn), pencere disina dusen eski kilitler SAYILMAZ.
  3) png_gorsel vurus_izin=False (TAKIP modu): commit-freeze tetiklenmez;
     kapanma kanali MENZIL TUTMA (R > R_hold iken ileri, R < R_hold iken geri).
     vurus_izin=True: eski davranis (commit-freeze calisir).
  4) Uctan uca alt-FSM: YAKLASMA -> TAKIP (bbox >= esik) -> 5 sn kilit ->
     kilit_ok -> TERMINAL.

Calistirma:  python tests/test_kilit_takip.py     (pytest de calisir)
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pose import geometri
from guidance.png_gorsel import AvciPNGGuduum
from guidance.ana_kontrol import AvciKontrol, Cfg

W, H = 1920.0, 1080.0
FX = geometri.fx_from_hfov(W)


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
#  3) png_gorsel TAKIP modu (vurus_izin=False)
# ---------------------------------------------------------------------------
def _hesapla_iki_kare(png, R_cm, vurus_izin, area_buyuk=False):
    """Duz onde, sabit R'de hedef: iki kare besle (R_f/Vc kurulsun), son komutu dondur.
    area_buyuk=True: bbox alan orani > 0.5 (commit-freeze alan kosulu)."""
    if area_buyuk:
        wp, hp = 0.9, 0.7                      # alan 0.63 > 0.5
    else:
        wp = (FX * Cfg.VIS_SPAN_CM / R_cm) / W  # pinhole'a tutarli genislik
        hp = wp * 0.4
    drone_pos = np.zeros(3); rot = (0.0, 0.0, 0.0)
    # hedef pikseli merkezde: cy'yi tilt'e gore merkeze koymak sart degil,
    # LOS yonu sabit oldugundan Omega~0 kalir (ayni piksel her karede).
    komutlar = []
    for i, t in enumerate((0.0, 0.1, 0.2)):
        d = _det(cxn=0.5, cyn=0.5, wp=wp, hp=hp, t=t)
        komutlar.append(png.hesapla(d, drone_pos, rot, np.zeros(2), Cfg,
                                    vurus_izin=vurus_izin))
    return komutlar


def test_takip_modu_commit_freeze_yok():
    # R ~2.5 m (300 cm alti) + buyuk alan: TERMINAL'de donardi; TAKIP'te DONMAZ.
    png = AvciPNGGuduum()
    _hesapla_iki_kare(png, 250.0, vurus_izin=False, area_buyuk=True)
    assert png._commit is False, "TAKIP modunda commit-freeze tetiklenmemeli"
    assert png.durum()["vurus_izin"] is False

    # ayni kurulum TERMINAL'de (vurus_izin=True) commit-freeze'e girer (eski davranis)
    png2 = AvciPNGGuduum()
    k = _hesapla_iki_kare(png2, 250.0, vurus_izin=True, area_buyuk=True)
    assert png2._commit is True, "TERMINAL'de commit-freeze eski haliyle calismali"
    assert k[1] == k[2], "commit-freeze son komutu dondurmali"


def test_takip_modu_menzil_tutma_isaret():
    """R >> R_hold -> ileri kapanma; R << R_hold -> geri acilma (pitch isaretleri zit)."""
    r_hold = float(geometri.fx_from_hfov(1.0)) * float(Cfg.VIS_SPAN_CM) / float(Cfg.VIS_HOLD_PCT)
    uzak = AvciPNGGuduum()
    k_uzak = _hesapla_iki_kare(uzak, r_hold * 4.0, vurus_izin=False)[-1]
    yakin = AvciPNGGuduum()
    k_yakin = _hesapla_iki_kare(yakin, r_hold * 0.4, vurus_izin=False)[-1]
    p_uzak, p_yakin = k_uzak[1], k_yakin[1]     # pitch kanali (ileri/geri)
    assert p_uzak != 0.0 and p_yakin != 0.0
    assert (p_uzak > 0) != (p_yakin > 0), (
        "menzil tutma calismiyor: uzakta pitch=%.3f, yakinda pitch=%.3f "
        "(zit isaret bekleniyor)" % (p_uzak, p_yakin))


# ---------------------------------------------------------------------------
#  4) Uctan uca alt-FSM: YAKLASMA -> TAKIP -> kilit_ok -> TERMINAL
# ---------------------------------------------------------------------------
def test_alt_fsm_zinciri():
    b = _beyin()
    b.durum = "GORSEL_GUDUM"
    drone_pos = np.zeros(3); rot = (0.0, 0.0, 0.0)

    # (a) kucuk bbox (%3): YAKLASMA'da kalir, vurus izni yok
    b._gorsel_guduum(_det(wp=0.03, hp=0.02, t=0.0), 0.0, drone_pos, rot, np.zeros(2))
    assert b.gorsel_faz == "YAKLASMA"
    assert b.png_tlm.get("vurus_izin") is False

    # (b) bbox esigi asar (%8): TAKIP'e gecer, henuz TERMINAL degil
    b._gorsel_guduum(_det(wp=0.08, hp=0.04, t=0.02), 0.02, drone_pos, rot, np.zeros(2))
    assert b.gorsel_faz == "TAKIP"
    assert b.kilit_ok is False

    # (c) 5+ sn merkezde/esik-ustu kilit -> kilit_ok -> TERMINAL + vurus izni
    t = 0.02
    for i in range(280):                        # 5.6 sn @ 50 Hz
        t += 0.02
        b._gorsel_guduum(_det(wp=0.08, hp=0.04, t=t), t, drone_pos, rot, np.zeros(2))
    assert b.kilit_ok is True, "5+ sn surekli kilit isteri saglamali"
    assert b.gorsel_faz == "TERMINAL"
    assert b.png_tlm.get("vurus_izin") is True

    # (d) latch kalici: tespit kaybolsa da kilit_ok dusmez
    b._gorsel_guduum(None, t + 0.02, drone_pos, rot, np.zeros(2))
    assert b.kilit_ok is True


# ---------------------------------------------------------------------------
#  5) YAKIN-MENZIL YAPISKANLIGI (#2): kilit menzilinde tespit kopunca GPS'e DONME
# ---------------------------------------------------------------------------
def _kayip_kos(b, drone, rot, t_bas, sure_s):
    """t_bas'tan itibaren sure_s boyunca None (kayip) besle; GPS'e dondu mu (None) dondur."""
    t = t_bas
    for _ in range(int(sure_s / 0.02) + 1):
        t += 0.02
        r = b._gorsel_guduum(None, t, drone, rot, np.zeros(2), revert_izin=True)
        if r is None:
            return True, t - t_bas          # GPS'e dondu
    return False, t - t_bas


def test_yakin_menzilde_yapiskan_kayip():
    """R_f < VIS_STICKY_R iken 2.0 sn kayipta GPS'e DONMEMELI (eski esik 1.0'i asar,
    yeni yakin esik 3.0'i asmaz -> kapanma ilerlemesi korunur, kilit dolabilir)."""
    b = _beyin(); b.durum = "GORSEL_GUDUM"
    drone = np.zeros(3); rot = (0.0, 0.0, 0.0)
    for i in range(5):                          # yakin tespit -> R_f kucuk kurulsun
        tt = i * 0.05
        b._gorsel_guduum(_det(wp=0.12, hp=0.06, t=tt), tt, drone, rot, np.zeros(2), revert_izin=True)
    assert b.pngg.R_f is not None and b.pngg.R_f < Cfg.VIS_STICKY_R, \
        "yakin R_f kurulmadi: %s" % b.pngg.R_f
    reverted, _ = _kayip_kos(b, drone, rot, 0.25, 2.0)
    assert not reverted, "yakin menzilde 2.0 sn kayipta GPS'e DONMEMELIYDI (yapiskan)"
    assert b.durum == "GORSEL_GUDUM"


def test_uzak_menzilde_normal_revert():
    """R_f > VIS_STICKY_R iken eski (kisa) esikle ~1.5 sn sonra GPS'e doner (hizli re-acquire)."""
    b = _beyin(); b.durum = "GORSEL_GUDUM"
    drone = np.zeros(3); rot = (0.0, 0.0, 0.0)
    for i in range(5):                          # uzak tespit (kucuk bbox -> buyuk R_f)
        tt = i * 0.05
        b._gorsel_guduum(_det(wp=0.02, hp=0.01, t=tt), tt, drone, rot, np.zeros(2), revert_izin=True)
    assert b.pngg.R_f is not None and b.pngg.R_f > Cfg.VIS_STICKY_R, \
        "uzak R_f kurulmadi: %s" % b.pngg.R_f
    reverted, sure = _kayip_kos(b, drone, rot, 0.25, 2.5)
    assert reverted, "uzak menzilde GPS'e donmeliydi"
    assert sure < 2.0, "uzak revert cok gec (%.2f s); yakin esik yanlislikla uygulanmis olabilir" % sure


# ---------------------------------------------------------------------------
#  6) YUMUSAK BASLANGIC (soft-start): handoff transiyentini ehlilestir
# ---------------------------------------------------------------------------
def test_softstart_yetki_rampasi():
    b = _beyin()
    b._gorsel_giris_t = 100.0
    mn = float(Cfg.VIS_SOFTSTART_MIN); s = float(Cfg.VIS_SOFTSTART_S)
    assert abs(b._softstart_gain(100.0) - mn) < 1e-6, "giris aninda yetki MIN olmali"
    assert abs(b._softstart_gain(100.0 + s) - 1.0) < 1e-6, "ramp sonunda tam yetki"
    assert abs(b._softstart_gain(100.0 + s/2) - (mn + (1.0-mn)*0.5)) < 1e-6, "yarida dogrusal"
    b._gorsel_giris_t = None
    assert b._softstart_gain(100.0) == 1.0, "gorselde degilken (giris None) tam yetki"


def test_softstart_komutu_kucultur():
    """Ayni tespit: giris aninda komut ~MIN carpanli, ramp sonrasi tam."""
    drone = np.zeros(3); rot = (0.0, 0.0, 0.0)
    det = _det(cxn=0.75, cyn=0.5, wp=0.10, hp=0.05, t=0.0)   # sagda -> yaw != 0
    b1 = _beyin(); b1.durum = "GORSEL_GUDUM"; b1._gorsel_giris_t = 0.0       # giris ani -> MIN
    k_ilk = b1._gorsel_guduum(dict(det), 0.0, drone, rot, np.zeros(2))
    b2 = _beyin(); b2.durum = "GORSEL_GUDUM"; b2._gorsel_giris_t = -10.0     # cok once -> tam
    k_tam = b2._gorsel_guduum(dict(det), 0.0, drone, rot, np.zeros(2))
    assert abs(k_tam[3]) > 1e-6, "kurulum: yaw sifir olmamali (hedef sagda)"
    assert abs(k_ilk[3]) < abs(k_tam[3]), "giris aninda komut kuculmus olmali"
    assert abs(k_ilk[3] - float(Cfg.VIS_SOFTSTART_MIN) * k_tam[3]) < 1e-6, "carpani MIN olmali"


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
