# -*- coding: utf-8 -*-
"""
GORSEL PNG guduum offline dogrulama (oyunsuz).

Oracle: pose/geometri.py. Bilinen bir DUNYA hedefini kamera_pozu+projekte ile
sentetik bbox'a (det) cevir, sonra png_gorsel fonksiyonlarini bu det uzerinde
dogrula. Boylece piksel->LOS ters-donusum, pinhole menzil, LOS donme (Omega) ve
PN komut isaretleri gercek oyun olmadan test edilir.

Calistirma:  python tests/test_png_gorsel.py     (pytest de calisir)
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pose import geometri
from guidance.png_gorsel import piksel_to_los, menzil_pinhole, AvciPNGGuduum
from guidance.ana_kontrol import Cfg


TILT = 25.0
W, H = 1920.0, 1080.0
FX = geometri.fx_from_hfov(W)


def _det_yap(p_target_world, drone_pos, rot_rpy, span_cm=Cfg.VIS_SPAN_CM,
             len_cm=110.0, t=0.0, aspect="front"):
    """Dunya hedefinden sentetik det uret (projekte oracle + pinhole boyut)."""
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot_rpy, tilt_deg=TILT)
    uv = geometri.projekte(p_target_world, cam_pos, R_cam, FX, W, H)
    assert uv is not None, "hedef kamera arkasinda (test kurulumu hatali)"
    cx, cy = uv
    R = float(np.linalg.norm(np.asarray(p_target_world, float) - cam_pos))
    yatay = span_cm if aspect == "front" else len_cm   # yan aspect: govde boyu izduser
    w_px = FX * yatay / R
    h_px = FX * (len_cm if aspect == "front" else span_cm) / R
    return {"cx": cx, "cy": cy, "w": w_px, "h": h_px, "conf": 0.9,
            "cls": 0, "W": W, "H": H, "t": t}, R


def test_piksel_to_los_ters_donusum():
    """Rastgele tutum/konumda: piksel->LOS, gercek yonle ~ birebir ortusmeli."""
    rng = np.random.default_rng(0)
    kotu = 0
    for _ in range(200):
        drone_pos = rng.uniform(-2000, 2000, 3)
        rot = (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(-180, 180))
        # kamera onunde bir hedef uret (lokal +X yaride)
        cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
        yon_lokal = np.array([1.0, rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.4)])
        p_t = cam_pos + R_cam @ (yon_lokal * rng.uniform(500, 8000))
        uv = geometri.projekte(p_t, cam_pos, R_cam, FX, W, H)
        if uv is None:
            continue
        u = piksel_to_los(uv[0], uv[1], W, H, drone_pos, rot, tilt_deg=TILT)
        gercek = (p_t - cam_pos) / np.linalg.norm(p_t - cam_pos)
        if float(np.dot(u, gercek)) < 0.9999:
            kotu += 1
    assert kotu == 0, f"{kotu} ornekte LOS ters-donusumu tutmadi"


def test_menzil_pinhole_dogrulugu():
    """Front aspect: pinhole menzil gercek menzile < %2 hata (projekte tutarli)."""
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    for R_gercek in (500, 1000, 3000, 8000, 20000):
        # hedefi kameranin tam onune (lokal +X) koy
        cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
        p_t = cam_pos + R_cam @ np.array([float(R_gercek), 0.0, 0.0])
        det, R = _det_yap(p_t, drone_pos, rot, t=0.0, aspect="front")
        R_est = menzil_pinhole(det["w"], det["h"], W, Cfg.VIS_SPAN_CM)
        hata = abs(R_est - R) / R
        assert hata < 0.02, f"R={R:.0f}cm menzil hatasi %{hata*100:.1f}"


def test_yan_aspect_yanliligi_sinirli():
    """Yan aspect'te menzil ~x1.56'ya kadar fazla tahmin (belgelenen kabul siniri)."""
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    R_gercek = 3000.0
    p_t = cam_pos + R_cam @ np.array([R_gercek, 0.0, 0.0])
    det, R = _det_yap(p_t, drone_pos, rot, aspect="side")   # w = govde boyu izduser
    R_est = menzil_pinhole(det["w"], det["h"], W, Cfg.VIS_SPAN_CM)
    orann = R_est / R
    assert 1.0 <= orann <= 1.6, f"yan aspect yanliligi x{orann:.2f} sinir disinda"


def test_omega_carpisma_ucgeninde_sifir():
    """Tam carpisma rotasi (LOS sabit yonde): Omega ~ 0."""
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    # hedef LOS boyunca yaklassin (yon sabit) -> u degismez -> Omega=0
    u_dir = R_cam @ np.array([1.0, 0.2, 0.1]); u_dir /= np.linalg.norm(u_dir)
    dt = 0.05
    u_list = []
    for k in range(3):
        R = 5000.0 - k * 400.0
        p_t = cam_pos + u_dir * R
        uv = geometri.projekte(p_t, cam_pos, R_cam, FX, W, H)
        u_list.append(piksel_to_los(uv[0], uv[1], W, H, drone_pos, rot, tilt_deg=TILT))
    om = np.cross(u_list[-2], u_list[-1]) / dt
    assert float(np.linalg.norm(om)) < 1e-3, "sabit LOS'ta Omega sifir olmali"


def test_omega_yandan_gecen_hedef():
    """Yandan gecen CV hedefte Omega buyuklugu analitik |r x v|/R^2 ile ortusmeli."""
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    p0 = cam_pos + R_cam @ np.array([4000.0, 0.0, 0.0])   # onde
    v = R_cam @ np.array([0.0, 1500.0, 0.0])              # yatayda kessin (cm/s)
    dt = 0.05
    p1, p2 = p0, p0 + v * dt
    u1 = piksel_to_los(*geometri.projekte(p1, cam_pos, R_cam, FX, W, H), W=W, H=H,
                       drone_pos=drone_pos, drone_rot_rpy=rot, tilt_deg=TILT)
    u2 = piksel_to_los(*geometri.projekte(p2, cam_pos, R_cam, FX, W, H), W=W, H=H,
                       drone_pos=drone_pos, drone_rot_rpy=rot, tilt_deg=TILT)
    om_est = float(np.linalg.norm(np.cross(u1, u2) / dt))
    r = p1 - cam_pos
    om_analitik = float(np.linalg.norm(np.cross(r, v)) / np.dot(r, r))
    assert abs(om_est - om_analitik) / om_analitik < 0.05, \
        f"Omega est={om_est:.4f} analitik={om_analitik:.4f}"


def test_hesapla_bayat_kare_omega_patlamaz():
    """Ayni det VIS_STALE_S boyunca tekrar gelince Omega/Vc GUNCELLENMEMELI."""
    g = AvciPNGGuduum()
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    p_t = cam_pos + R_cam @ np.array([3000.0, 200.0, 0.0])
    det, _ = _det_yap(p_t, drone_pos, rot, t=1.0)
    g.hesapla(det, drone_pos, rot, np.zeros(2), Cfg)
    om1 = g.durum()["omega_rads"]
    # AYNI det'i (ayni t) 10 tik daha ver -> durum degismemeli, patlama olmamali
    for _ in range(10):
        g.hesapla(det, drone_pos, rot, np.zeros(2), Cfg)
    om2 = g.durum()["omega_rads"]
    assert om1 == om2, "bayat kare tekrarinda Omega degisti (dt->0 patlamasi riski)"
    thr, pitch, roll, yaw = g.hesapla(det, drone_pos, rot, np.zeros(2), Cfg)
    for c in (thr, pitch, roll, yaw):
        assert -1.0 <= c <= 1.0 and math.isfinite(c)


def test_hesapla_komut_sinirlari_ve_yon():
    """Hedef SAGDA -> yaw>0 (SIGN_YAW=+1); tum komutlar [-1,1] ve sonlu."""
    g = AvciPNGGuduum()
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    p_t = cam_pos + R_cam @ np.array([3000.0, 900.0, 0.0])   # belirgin SAGDA
    t = 0.0
    yaw = 0.0
    for k in range(4):   # birkac kare: EMA otursun
        p_k = p_t   # sabit -> ex sabit
        det, _ = _det_yap(p_k, drone_pos, rot, t=t)
        thr, pitch, roll, yaw = g.hesapla(det, drone_pos, rot, np.zeros(2), Cfg)
        t += 0.05
        for c in (thr, pitch, roll, yaw):
            assert -1.0 <= c <= 1.0 and math.isfinite(c)
    assert yaw > 0.0, f"hedef sagda ama yaw={yaw:.3f} (SIGN_YAW yonu?)"


def test_takip_fazi_dusuk_manevra_yetkisi():
    """Takip (vurus_izin=False) roll/pitch, terminal (True) komutundan KUCUK (bank siniri);
    oran ~ VIS_TRACK_TILT/VIS_PN_TILT. Yaw iki fazda AYNI (cerceveleme bozulmaz)."""
    drone_pos = np.array([0.0, 0.0, 1000.0]); rot = (0.0, 0.0, 0.0)
    cam_pos, R_cam = geometri.kamera_pozu(drone_pos, rot, tilt_deg=TILT)
    # yandan gecen hedef -> yanal PN (roll) uretsin
    p0 = cam_pos + R_cam @ np.array([2000.0, 300.0, 0.0])
    p1 = cam_pos + R_cam @ np.array([2000.0, 900.0, 0.0])   # saga kayiyor -> Omega != 0

    def _kos(vurus_izin):
        g = AvciPNGGuduum(); t = 0.0; komut = None
        for p_k in (p0, p1, p1):                             # Omega/EMA otursun
            det, _ = _det_yap(p_k, drone_pos, rot, t=t)
            komut = g.hesapla(det, drone_pos, rot, np.zeros(2), Cfg, vurus_izin=vurus_izin)
            t += 0.05
        return komut, g._tilt

    k_takip, tilt_takip = _kos(False)
    k_term, tilt_term = _kos(True)
    assert abs(tilt_takip - Cfg.VIS_TRACK_TILT) < 1e-9
    assert abs(tilt_term - Cfg.VIS_PN_TILT) < 1e-9
    # roll/pitch takip < terminal (bank/dalis kisildi)
    assert abs(k_takip[2]) < abs(k_term[2]) + 1e-12, "takip roll terminalden kucuk olmali"
    assert abs(k_takip[2]) <= Cfg.VIS_TRACK_TILT + 1e-9, "takip roll bank sinirini asmamali"
    # yaw AYNI (VIS_TRACK_TILT yaw'a dokunmaz)
    assert abs(k_takip[3] - k_term[3]) < 1e-9, "yaw iki fazda ayni olmali (cerceveleme)"


def test_kor_devam_hicbir_tespit_yoksa_hover():
    g = AvciPNGGuduum()
    assert g.kor_devam(Cfg, Cfg.DT) == (0.0, 0.0, 0.0, 0.0)


def _komuttan_yatay_ivme(pitch, roll, yaw_rad, a_max):
    """(pitch,roll) komutunu -> DUNYA yatay ivmesine cevir (g._komut eslemesinin tersi).
    a_fwd=pitch/(SIGN*TILT)*a_max; world_to_body kendi tersi: ax=af*c+ar*s, ay=af*s-ar*c."""
    a_fwd = pitch / (Cfg.PITCH_SIGN * Cfg.VIS_PN_TILT) * a_max
    a_right = roll / (Cfg.ROLL_SIGN * Cfg.VIS_PN_TILT) * a_max
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    ax = a_fwd * c + a_right * s
    ay = a_fwd * s - a_right * c
    return ax, ay


def test_uctan_uca_donen_hedefi_yakalar():
    """Kapali dongu: sentetik bbox'larla beslenen PNG, DONEN hedefi <3m iska ile yakalar.
    Yatay ivme g'nin komutundan geri-cozulur (mapping tersi); dikey ayni irtifada trivial.
    Bu, LOS->Omega->PN->komut zincirinin gercekten VURAN yorunge urettigini kanitlar."""
    g = AvciPNGGuduum()
    a_max = float(Cfg.VIS_PN_A_MAX)          # cm/s^2
    v_max = 2200.0                           # cm/s
    dt = 0.02                                 # 50 Hz kontrol
    det_periyot = 0.05                        # 20 Hz dedektor (yeni t)

    # Baslangic: onleyici orijinde, hedef 60 m onde/yanda, sabit donusle viraj
    p_i = np.array([0.0, 0.0, 1000.0])
    v_i = np.array([600.0, 0.0, 0.0])
    p_t = np.array([6000.0, 1500.0, 1000.0])
    v_t = np.array([-200.0, 900.0, 0.0])
    omega_t = math.radians(18.0)             # hedef donus hizi (rad/s)

    son_det = None; son_det_t = -1.0; R_min = 1e9
    for k in range(1500):                    # <=30 s
        t = k * dt
        # hedefi dondur (yatay hiz vektorunu cevir)
        c, s = math.cos(omega_t * dt), math.sin(omega_t * dt)
        vx, vy = v_t[0], v_t[1]
        v_t[0] = c * vx - s * vy; v_t[1] = s * vx + c * vy
        p_t = p_t + v_t * dt

        R = float(np.linalg.norm(p_t - p_i)); R_min = min(R_min, R)
        if R < 50.0:
            break

        # yeni dedektor karesi mi? (20 Hz) -> attitude yaw hedefe donuk, sentetik det uret
        if t - son_det_t >= det_periyot - 1e-9:
            bearing = math.degrees(math.atan2(p_t[1] - p_i[1], p_t[0] - p_i[0]))
            rot = (0.0, 0.0, bearing)         # level, burun hedefte (yaw servo etkisi)
            det, _ = _det_yap(p_t, p_i, rot, t=t)
            son_det, son_det_t, son_rot = det, t, rot

        if son_det is None:
            continue
        thr, pitch, roll, yaw = g.hesapla(son_det, p_i, son_rot, v_i[:2], Cfg)

        # komut -> yatay ivme, entegre et (dikey ayni irtifa -> thr trivial)
        yaw_rad = math.radians(son_rot[2])
        ax, ay = _komuttan_yatay_ivme(pitch, roll, yaw_rad, a_max)
        v_i = v_i + np.array([ax, ay, 0.0]) * dt
        sp = np.linalg.norm(v_i)
        if sp > v_max:
            v_i *= v_max / sp
        p_i = p_i + v_i * dt

    assert R_min < 300.0, f"PNG donen hedefi yakalayamadi; en yakin {R_min/100:.2f} m"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\n{len(fns)} test gecti.")
