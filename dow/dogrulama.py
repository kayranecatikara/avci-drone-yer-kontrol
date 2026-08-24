# -*- coding: utf-8 -*-
"""
================================================================================
DOGRULAMA - yeni yasalarin ISARET/YON sinamalari (oyun ACMADAN)
================================================================================
Bu depoda ayna/isaret hatasi UC KEZ tekrarladi ve her seferinde ancak UCUSTA
fark edildi. Bu dosya o siniflar hatayi tezgahta yakalar: sentetik bir durum
kurar, yasayi cagirir ve komutun YONUNU dogrular.

Sabitler DOSYALARDAN okunur (kamera.py / ayarlar.py); burada hicbir deger
sabitlenmez -- boylece o dosyalar guncellenince sinama kendini uyarlar.

Kosum:  python dow/dogrulama.py        (depo kokunden)
================================================================================
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dow.ayarlar import Ayar                       # noqa: E402
from dow import gps as YGPS                        # noqa: E402
from dow import ibvs as YIBVS                      # noqa: E402
from dow.gorus import kamera as KAM                # noqa: E402
from dow import amir                               # noqa: E402

GECTI = []


def kontrol(ad, kosul, aciklama):
    GECTI.append(bool(kosul))
    print("  [%s] %-46s %s" % ("GECTI" if kosul else "KALDI", ad, aciklama))


print("=" * 78)
print("0) YURURLUKTEKI SABITLER (dosyalardan okundu)")
print("=" * 78)
print("  kamera : TILT=%.2f deg  f=%.1f px  MENZIL_C=%.0f px*m  %dx%d"
      % (KAM.TILT_DEG, KAM.F_PX, KAM.MENZIL_C, KAM.IMG_W, KAM.IMG_H))
print("  istasyon: %.1f m arkada, oran %.2f -> %.1f m altta (yukselis %.1f deg)"
      % (Ayar.ISTASYON_MENZIL_M, Ayar.ISTASYON_ALT_ORAN,
         Ayar.ISTASYON_MENZIL_M * Ayar.ISTASYON_ALT_ORAN,
         math.degrees(math.atan(Ayar.ISTASYON_ALT_ORAN))))
print("  faz     : %d ardisik tespit -> GORSEL | %d ardisik kayip -> GPS"
      % (Ayar.DEVIR_KARE, Ayar.KAYIP_KARE))
print("  zarf    : V_MAX=%.1f  vz +%.1f/-%.1f  yaw_max=%.0f deg/s  dongu %.0f Hz"
      % (Ayar.V_MAX, Ayar.VZ_MAX_TIRMAN, Ayar.VZ_MAX_ALCAL,
         Ayar.YAW_RATE_MAX, Ayar.LOOP_HZ))

print()
print("=" * 78)
print("1) KAMERA MODELI")
print("=" * 78)
kontrol("merkez isini azimut=0",
        abs(KAM.piksel_kerteriz(KAM.CX, KAM.CY, 0, 0)[0]) < 1e-9,
        "kadraj merkezi burun dogrultusunda")
az_sag = KAM.piksel_kerteriz(KAM.CX + 300, KAM.CY, 0, 0)[0]
kontrol("kadrajda SAG -> azimut POZITIF", az_sag > 0, "az=%+.2f deg" % az_sag)
_, el_ust = KAM.piksel_kerteriz(KAM.CX, KAM.CY - 300, 0, 0)
_, el_mrk = KAM.piksel_kerteriz(KAM.CX, KAM.CY, 0, 0)
kontrol("kadrajda YUKARI -> yukselis ARTAR", el_ust > el_mrk,
        "merkez %.2f -> ust %.2f deg" % (el_mrk, el_ust))
kontrol("merkez yukselisi = kamera tilti", abs(el_mrk - KAM.TILT_DEG) < 1e-9,
        "%.3f deg" % el_mrk)
# pitch isareti: kamera.py sozlesmesi "pitch NEGATIF = burun ASAGI"
_, el_burun_asagi = KAM.piksel_kerteriz(KAM.CX, KAM.CY, -15.0, 0)
kontrol("burun ASAGI (pitch<0) -> yukselis DUSER", el_burun_asagi < el_mrk,
        "pitch -15 -> %.2f deg (duz iken %.2f)" % (el_burun_asagi, el_mrk))
kontrol("menzil kutu ile TERS orantili", KAM.menzil(40) < KAM.menzil(20),
        "20px->%.1f m, 40px->%.1f m" % (KAM.menzil(20), KAM.menzil(40)))

print()
print("  -- gidis-donus kimligi (kamera.py'nin kendi bekcisi) --")
enb = 0.0
for cx in (200.0, 960.0, 1700.0):
    for cy in (200.0, 540.0, 900.0):
        for roll in (0.0, 20.0, -35.0):
            for pitch in (0.0, -15.0, 8.0):
                a, e = KAM.los_seviye(cx, cy, roll, pitch)
                rx, ry = KAM.seviye_piksel(a, e, roll, pitch)
                enb = max(enb, math.hypot(rx - cx, ry - cy))
kontrol("los_seviye <-> seviye_piksel tur-donusu", enb < 1e-6,
        "en buyuk sapma %.3e px (81 kombinasyon)" % enb)
enb2 = 0.0
for cx in (200.0, 960.0, 1700.0):
    for cy in (200.0, 540.0, 900.0):
        for roll in (0.0, 20.0, -35.0):
            for pitch in (0.0, -15.0):
                a, e = KAM.piksel_kerteriz(cx, cy, pitch, roll)
                rx, ry = KAM.kerteriz_piksel(a, e, pitch, roll)
                enb2 = max(enb2, math.hypot(rx - cx, ry - cy))
kontrol("piksel_kerteriz <-> kerteriz_piksel tur-donusu", enb2 < 1e-6,
        "en buyuk sapma %.3e px (54 kombinasyon)" % enb2)

print()
print("  -- YAPISAL kiyas: depodaki OLCULMUS zincirle ayni matematik mi? --")
# bbox_geometri YASA cercevesinde (640x480, FX=166.58, tilt 25) calisir.
# Kalibrasyon farkini notrlemek icin AYNI tilt ve esdeger piksel verilir;
# esitlik cikiyorsa iki los_seviye ayni ZINCIRDIR, yalniz sabitleri farklidir.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                    "kopru", "gazebo_kaynak"))
    from control.guidance import bbox_geometri as BG      # noqa: E402
    enb3 = 0.0
    for lcx in (60.0, 320.0, 600.0):
        for lcy in (60.0, 240.0, 420.0):
            for roll in (0.0, -35.0):
                for pitch in (0.0, 10.0):
                    a_ref, e_ref = BG.los_seviye(lcx, lcy, math.radians(roll),
                                                 math.radians(pitch),
                                                 tilt_deg=KAM.TILT_DEG)
                    # ayni ISINI kamera.py cercevesinde ifade et
                    ncx = KAM.CX + (lcx - BG.CX) * (KAM.F_PX / BG.FX)
                    ncy = KAM.CY + (lcy - BG.CY) * (KAM.F_PX / BG.FY)
                    a_new, e_new = KAM.los_seviye(ncx, ncy, roll, pitch)
                    enb3 = max(enb3, abs(math.degrees(a_ref) - a_new),
                               abs(math.degrees(e_ref) - e_new))
    kontrol("los_seviye = bbox_geometri zinciri", enb3 < 1e-9,
            "en buyuk sapma %.3e deg (36 kombinasyon)" % enb3)
except Exception as _e:
    print("  [ATLANDI] bbox_geometri kiyasi: %r" % (_e,))

print()
print("=" * 78)
print("2) PIKSEL OLCEK CEVIRISI (canli akis 640 -> ham 1920)")
print("=" * 78)
cx, cy, w, h = amir._yasa_pikselden_ham(320.0, 240.0, 10.0, 6.0)
kontrol("merkez merkeze gider", abs(cx - KAM.CX) < 1e-6 and abs(cy - KAM.CY) < 1e-6,
        "(320,240) -> (%.0f,%.0f)" % (cx, cy))
kontrol("kutu da olceklenir", abs(w - 10 * amir.OLCEK) < 1e-6,
        "10 px -> %.1f px (olcek %.4f)" % (w, amir.OLCEK))
kontrol("olcek AKIS f'inden turer (kamera f'inden DEGIL)",
        abs(amir.FX_AKIS - 531.36) < 0.05 and abs(amir.FX_AKIS - KAM.F_PX) > 1.0,
        "FX_AKIS=%.2f  KAM.F_PX=%.1f" % (amir.FX_AKIS, KAM.F_PX))

print()
print("=" * 78)
print("3) GPS YASASI - ISTASYON TUTMA")
print("=" * 78)
# Hedef 100 m irtifada, +X yonunde 18 m/s. Drone 60 m GERIDE, AYNI irtifada.
# NOT: yasaya Z-YUKARI cercevede verilir (amir.py bu cevirinin sorumlusu).
hedef_p = (0.0, 0.0, 100.0)
drone_p = (-60.0, 0.0, 100.0)
hedef_v = (18.0, 0.0, 0.0)
v_xy, vz_ned, yaw_rate, tani = YGPS.komut(drone_p, 0.0, hedef_p, hedef_v, 0.0, Ayar)

kontrol("burun hedefe (yaw_hata ~ 0)", abs(tani["yaw_hata"]) < 1e-6,
        "yaw_hata=%+.2f deg" % tani["yaw_hata"])
kontrol("ILERI dogru hizlanir (vx>hedef hizi)", v_xy[0] > 18.0,
        "vx=%+.1f m/s (hedef 18.0) -> kapanma %+.1f" % (v_xy[0], v_xy[0] - 18.0))
kontrol("yanal komut yok", abs(v_xy[1]) < 1e-6, "vy=%+.3f" % v_xy[1])
kontrol("hedefin ALTINA inmek icin ALCALIR (vz_ned>0)", vz_ned > 0,
        "vz_ned=%+.2f m/s (NED: + = ASAGI)" % vz_ned)
kontrol("istasyon hedefin GERISINDE", tani["ist_x"] < hedef_p[0],
        "ist_x=%+.2f m (hedef 0.0)" % tani["ist_x"])
kontrol("istasyon hedefin ALTINDA", tani["ist_z"] < hedef_p[2],
        "ist_z=%.2f m -> %.2f m altta" % (tani["ist_z"], hedef_p[2] - tani["ist_z"]))

ist_p = (tani["ist_x"], tani["ist_y"], tani["ist_z"])
v2, vz2, _, t2 = YGPS.komut(ist_p, 0.0, hedef_p, hedef_v, 0.0, Ayar)
kontrol("istasyonda: hiz = hedef hizi (ileri besleme)", abs(v2[0] - 18.0) < 1e-6,
        "vx=%+.3f m/s, ist_hata=%.3f m" % (v2[0], t2["ist_hata_m"]))
kontrol("istasyonda: dikey komut ~0", abs(vz2) < 1e-6, "vz_ned=%+.4f" % vz2)

v3, _, _, t3 = YGPS.komut(drone_p, 0.0, hedef_p, (0.0, 18.0, 0.0), 90.0, Ayar)
kontrol("hedef +Y'ye giderse istasyon -Y'de", t3["ist_y"] < 0,
        "ist=(%.2f, %.2f)" % (t3["ist_x"], t3["ist_y"]))

# ⭐ SUREKLILIK: GPS istasyonu ile gorsel nisanin AYNI geometriye bakmasi
ist_elev = math.degrees(math.atan(Ayar.ISTASYON_ALT_ORAN))
gorsel_elev_uzak = KAM.piksel_kerteriz(KAM.CX, YIBVS.IbvsCfg.CY_REF_UZAK, 0, 0)[1]
kontrol("GPS istasyonu ~ gorsel nisan (devirde sicrama yok)",
        abs(ist_elev - gorsel_elev_uzak) < 10.0,
        "istasyon %.1f deg  vs  gorsel cy_ref_uzak %.1f deg" % (ist_elev, gorsel_elev_uzak))

print()
print("=" * 78)
print("4) GORSEL YASA (IBVS)")
print("=" * 78)
C = YIBVS.IbvsCfg
v_xy, vz_ned, yaw_hedef, hiz_I, tani = YIBVS.komut(
    KAM.CX, KAM.CY, 25.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.05, C, own_vz=0.0)
kontrol("merkezdeki hedef -> yaw degismez", abs(yaw_hedef) < 1e-9,
        "yaw_hedef=%+.3f deg" % yaw_hedef)
kontrol("hiz tavana oturur (V_HUCUM)", abs(tani["ibvs_v"] - C.V_HUCUM) < 1e-6,
        "v=%.1f m/s" % tani["ibvs_v"])

_, _, yaw_sag, _, t_sag = YIBVS.komut(
    KAM.CX + 300, KAM.CY, 25.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.05, C, own_vz=0.0)
kontrol("hedef SAGDA -> yaw hedefi POZITIF (saga)", yaw_sag > 0,
        "yaw_hedef=%+.1f deg (az=%+.1f)" % (yaw_sag, t_sag["ibvs_azimut"]))
_, _, yaw_sol, _, t_sol = YIBVS.komut(
    KAM.CX - 300, KAM.CY, 25.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.05, C, own_vz=0.0)
kontrol("hedef SOLDA -> yaw hedefi NEGATIF (sola)", yaw_sol < 0,
        "yaw_hedef=%+.1f deg (az=%+.1f)" % (yaw_sol, t_sol["ibvs_azimut"]))
kontrol("simetrik (ayna bozulmamis)", abs(yaw_sag + yaw_sol) < 1e-9,
        "|%+.3f| vs |%+.3f|" % (yaw_sag, yaw_sol))

_, vz_asagi, _, _, t_a = YIBVS.komut(
    KAM.CX, 900.0, 25.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.05, C, own_vz=0.0)
kontrol("hedef kadrajda ASAGIDA -> ALCAL (vz_ned>0)", vz_asagi > 0,
        "cy=900 (ref %.0f) -> vz_ned=%+.2f" % (t_a["ibvs_cy_ref"], vz_asagi))
_, vz_yukari, _, _, t_y = YIBVS.komut(
    KAM.CX, 200.0, 25.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.05, C, own_vz=0.0)
kontrol("hedef kadrajda YUKARIDA -> TIRMAN (vz_ned<0)", vz_yukari < 0,
        "cy=200 (ref %.0f) -> vz_ned=%+.2f" % (t_y["ibvs_cy_ref"], vz_yukari))

_, _, _, _, t_uzak = YIBVS.komut(KAM.CX, KAM.CY, 20.0, 12.0, 0, 0, 0, 0.0, 0.05, C)
_, _, _, _, t_yakin = YIBVS.komut(KAM.CX, KAM.CY, 120.0, 70.0, 0, 0, 0, 0.0, 0.05, C)
kontrol("kutu buyuyunce nisan merkeze kayar",
        t_yakin["ibvs_cy_ref"] > t_uzak["ibvs_cy_ref"],
        "uzak cy_ref=%.0f -> yakin cy_ref=%.0f"
        % (t_uzak["ibvs_cy_ref"], t_yakin["ibvs_cy_ref"]))

print()
print("=" * 78)
print("5) GECERLILIK KAPILARI")
print("=" * 78)
_boyut_ok = KAM.MENZIL_C / 40.0     # 40 px -> menzil
ok, s = YIBVS.gecerli(KAM.CX, KAM.CY, 40.0, 24.0, 0.9, C)
kontrol("normal kutu gecer", ok, "40 px -> %.1f m, sebep=%r" % (_boyut_ok, s))
ok, s = YIBVS.gecerli(KAM.CX, KAM.CY, 40.0, 24.0, 0.10, C)
kontrol("dusuk conf elenir", not ok and s == "conf", "sebep=%r" % s)
ok, s = YIBVS.gecerli(KAM.CX, KAM.CY, 5.0, 3.0, 0.9, C)
kontrol("cok kucuk kutu elenir", not ok, "sebep=%r" % s)
ok, s = YIBVS.gecerli(KAM.CX, KAM.CY, 600.0, 400.0, 0.9, C)
kontrol("dev kutu (yanlis pozitif) elenir", not ok and s == "menzil_yakin",
        "sebep=%r menzil=%.1f m" % (s, KAM.menzil(600)))
# Gorsel devrin acildigi asgari kutu (MENZIL_MAX_M kapisi)
_px_devir = KAM.MENZIL_C / C.MENZIL_MAX_M
print("       -> gorsel devir icin gereken asgari kutu: %.1f px ham "
      "(%.1f px canli akista) = %.0f m" % (_px_devir, _px_devir / amir.OLCEK,
                                           C.MENZIL_MAX_M))

print()
print("=" * 78)
n_ok = sum(GECTI)
print("SONUC: %d/%d sinama gecti" % (n_ok, len(GECTI)))
print("=" * 78)
sys.exit(0 if n_ok == len(GECTI) else 1)
