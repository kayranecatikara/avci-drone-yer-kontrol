# -*- coding: utf-8 -*-
"""
================================================================================
 POSE VERI TOPLAMA UCUSU  (Faz 1 — bkz. POSE_REHBERI.md)
================================================================================
Amac: YOLO-pose egitimi icin HAM veri toplamak: oyun karesi (PNG) + o anin tam
telemetrisi (JSONL). Etiket URETMEZ — etiketleme sonradan pose/etiketle.py'de
(Faz 4) truth konum + rotasyon dogrulamasiyla yapilir.

Calistirma (repo kokunden; oyun ACIK ve PLAY modunda; WEB ARAYUZU KAPALI —
oyun tek TCP baglantisi kabul eder):
    python pose\\kayit_ucusu.py --dakika 10
    python pose\\kayit_ucusu.py --pasif        # komut GONDERMEZ, sadece kaydeder

Ne yapar:
  1. SDK'ya baglanir ve TRUTH (bozulmamis) telemetrinin geldigini DOGRULAR.
     Gelmiyorsa hemen cikar: etiketler truth konumdan uretilecek (kullanici
     karari); truth'suz kayit ise yaramaz. (Arayuzdeki "Gercek GPS" modu
     calisiyorsa oyun truth gonderiyor demektir — server.py de ayni
     get_debug_truth() alanini kullanir.)
  2. Basit ORBIT otopiloti: hedefin (truth) etrafinda mesafe/azimut/elevasyon
     kombinasyonlarindan rastgele noktalara gider, her noktada ~3 sn kalir.
     Burnu hedefe dondurur + RASTGELE YAW OFSETI -> hedef kadrajin farkli
     bolgelerine duser (merkez onyargisini onler).
  3. ~KAYIT_HZ'de kare+telemetri kaydeder. Kare ancak sunlar saglaninca yazilir:
     hedef AM'si kadraj icinde (%4 marj) ve MIN < mesafe < MAX. PNG yazimi ayri
     thread'de (kontrol dongusu bloklanmaz); JPEG KULLANILMAZ (artefakt keypoint
     hassasiyetini bozar).
  4. CTRL-C / sure bitince: HOVER birakir (0,0,0,0,arm=True; motorlar ACIK kalir,
     drone dusmez) ve dosyalari kapatir.

Cikti: <cikti>/oturum_YYYYMMDD_HHMMSS/
    meta.json        # HFOV/tilt/limitler/ayarlar (etiketleyici okur)
    telemetri.jsonl  # kaydedilen kare basina 1 satir (asagida alanlar)
    kare_000001.png  # BGR, kayipsiz PNG

Isaret notu: kontrol isaretleri CALISAN guidance/ana_kontrol.py ile ayni
varsayimdadir (+pitch=ileri, +roll=saga, +yaw=saga donus, +thr=tirman).
Ters davranis gorursen K.PITCH_SIGN / K.ROLL_SIGN / K.YAW_SIGN cevir.
Kazanclar kasitli YUMUSAK (net kare + stabil poz); drone noktalara agir agir
suzulur, bu normaldir.
"""
import os
import sys
import json
import math
import time
import queue
import random
import argparse
import threading

# Repo koku sys.path'e (script "python pose\kayit_ucusu.py" ile calistirilinca
# sys.path[0] = pose/ olur; sdk/detection/pose importlari icin kok gerekli).
_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import numpy as np
import cv2

from sdk import drone_sdk as drone
from pose import geometri


# =============================================================================
#  AYARLAR
# =============================================================================
class K:
    # --- kayit ---
    KAYIT_HZ       = 7.0        # kare kayit sikligi (kontrol dongusunden bagimsiz)
    KONTROL_HZ     = 50.0       # SDK onerisi
    MIN_MESAFE_CM  = 400.0      # 4 m'den yakini kaydetme (kadraj tasar / carpisma alani)
    MAX_MESAFE_CM  = 6000.0     # 60 m'den uzagi kaydetme (yaklasma->orbit gecis bandi dahil)
    KADRAJ_MARJ    = 0.04       # AM ekran kenarina bu orandan yakinsa kaydetme

    # --- iki faz: UZAKSA yaklasma(pursuit), YAKINSA orbit ---
    YAKIN_ESIK_CM   = 5000.0   # hedef bundan UZAKSA lead-pursuit; yakinsa orbit+kayit
    LEAD_MAX_S      = 2.5       # pursuit lead suresi tavani (hedefin gidecegi yere nisan)
    KAPANMA_REF_CMS = 2500.0   # lead zamani ~ mesafe / bu (kaba kapanma hizi olcegi)

    # --- orbit noktalari (hedefe GORELI; heading = hedefin ucus yonu) ---
    MESAFELER_CM   = [800, 1200, 1700, 2300, 3000, 3800]
    ELEVASYONLAR_DEG = [-40, -25, -10, 0, 12, 25, 40]   # + = drone hedefin USTUNDE
    NOKTA_SURE_S   = 3.0        # her noktada kalis
    YAW_OFSET_MAX_DEG = 32.0    # bakista rastgele ofset (125 derece HFOV icinde kalir)
    MIN_IRTIFA_CM  = 400.0      # nokta zemine bundan fazla yaklastirilmaz

    # --- kontrol kazanclari (birimler cm, cm/s) ---
    KP_POS   = 1.1              # konum hatasi (cm) -> istenen hiz (cm/s), 1/s
    V_MAX    = 3000.0           # yatay hiz istegi tavani (30 m/s — hedefe yetismek icin)
    VZ_MAX   = 1100.0           # dikey hiz istegi tavani
    KV       = 0.0016           # hiz hatasi (cm/s) -> pitch/roll komutu
    KV_Z     = 0.0020           # dikey hiz hatasi -> throttle
    KP_YAW   = 1.4              # yaw hatasi (rad) -> yaw komutu
    CMD_MAX  = 0.7              # pitch/roll tavani (yaklasmada daha atak)
    YAW_MAX  = 0.6
    THR_MIN, THR_MAX = -0.6, 1.0
    MAX_DELTA = 0.08            # komut degisim siniri / tik (rate limit)
    EMNIYET_CM = 500.0          # hedefe bundan fazla yaklasilirsa disari kac (carpma onleme)
    KACIS_CMS  = 800.0

    PITCH_SIGN = +1.0
    ROLL_SIGN  = +1.0
    YAW_SIGN   = +1.0


def wrap_pi(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# =============================================================================
#  PNG YAZICI (ayri thread — kontrol dongusunu diskte bekletme)
# =============================================================================
class PngYazici:
    def __init__(self):
        self.q = queue.Queue(maxsize=60)
        self.yazilan = 0
        self.dusen = 0          # kuyruk doluyken atlanan kare (disk yetisemedi)
        self._t = threading.Thread(target=self._dongu, daemon=True)
        self._t.start()

    def yaz(self, yol, bgr):
        try:
            self.q.put_nowait((yol, bgr))
            return True
        except queue.Full:
            self.dusen += 1
            return False

    def _dongu(self):
        while True:
            item = self.q.get()
            if item is None:
                return
            yol, bgr = item
            try:
                cv2.imwrite(yol, bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                self.yazilan += 1
            except Exception as e:
                print("[PNG] yazma hatasi:", e)

    def kapat(self):
        self.q.put(None)
        self._t.join(timeout=60)


# =============================================================================
#  KARE KAYNAGI: once windows-capture (pencere arkada olsa da calisir),
#  olmazsa mss + client-area (oyun penceresi GORUNUR/onde olmali).
# =============================================================================
def _client_rect(hwnd):
    """hwnd -> ekranda client alani (left, top, W, H). Baslik cubugunu DISLAR."""
    import ctypes
    from ctypes import wintypes
    r = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(int(hwnd), ctypes.byref(r))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(int(hwnd), ctypes.byref(pt))
    return int(pt.x), int(pt.y), int(r.right), int(r.bottom)


class KareKaynagi:
    def __init__(self):
        from detection.pencere_yakala import PencereYakala, pencere_bul
        self.mod = None
        self.pencere = None
        self.hwnd = None
        self.mss_ctx = None

        py = PencereYakala(title_hints=["drones of war"])
        if py.hazir and py.baslat():
            self.pencere = py
            self.mod = "windows-capture"
            return

        ad, hwnd = pencere_bul(["drones of war"])
        if hwnd is None:
            raise RuntimeError("Oyun penceresi bulunamadi. Oyun acik ve PLAY modunda mi?")
        import mss
        self.mss_ctx = mss.mss()
        self.hwnd = hwnd
        self.mod = "mss"
        print("[KARE] windows-capture yok/acilmadi -> mss client-area. "
              "Oyun penceresi GORUNUR ve ONDE kalmali.")

    def get(self):
        """Son kare (BGR, kopya) | None."""
        if self.pencere is not None:
            f = self.pencere.get_latest_bgr()
            return None if f is None else f.copy()
        l, t, w, h = _client_rect(self.hwnd)
        if w < 100 or h < 100:
            return None
        img = np.array(self.mss_ctx.grab({"left": l, "top": t, "width": w, "height": h}))
        return np.ascontiguousarray(img[:, :, :3])      # BGRA -> BGR


# =============================================================================
#  HEDEF IZLEYICI: truth konum sonlu-farkindan hiz + ucus yonu (heading).
#  (ana_kontrol._gercek_hedef_hiz kalibi; orbit noktalari heading'e gore doner.)
# =============================================================================
class HedefIzleyici:
    def __init__(self):
        self.son_p = None
        self.son_t = None
        self.vel = np.zeros(3)          # cm/s (EMA)
        self.heading_deg = 0.0          # hedef duruyorsa son deger korunur

    def guncelle(self, t, p):
        p = np.asarray(p, float)
        if self.son_p is not None and np.array_equal(p, self.son_p):
            return
        if self.son_p is not None and self.son_t is not None:
            dt = t - self.son_t
            if 1e-3 < dt < 3.0:
                v = (p - self.son_p) / dt
                self.vel = 0.7 * self.vel + 0.3 * v
                if np.linalg.norm(self.vel[:2]) > 300.0:     # >3 m/s: heading guvenilir
                    self.heading_deg = math.degrees(math.atan2(self.vel[1], self.vel[0]))
        self.son_p = p
        self.son_t = t


# =============================================================================
#  ORBIT OTOPILOTU: hedefe GORELI rastgele noktalara git, burnu hedefe (+ofset) tut.
# =============================================================================
class OrbitOtopilot:
    def __init__(self, seed=11):
        self.rng = random.Random(seed)
        self.nokta = None               # (mesafe_cm, azimut_deg, elev_deg)
        self.nokta_t0 = -1e9
        self.yaw_ofset = 0.0
        self.faz = "yaklas"             # "yaklas" (pursuit) | "orbit"
        self.prev = {"thr": 0.0, "pitch": 0.0, "roll": 0.0, "yaw": 0.0}

    def _yeni_nokta(self, t):
        self.nokta = (self.rng.choice(K.MESAFELER_CM),
                      self.rng.uniform(0.0, 360.0),
                      self.rng.choice(K.ELEVASYONLAR_DEG))
        self.nokta_t0 = t
        self.yaw_ofset = math.radians(self.rng.uniform(-K.YAW_OFSET_MAX_DEG,
                                                       K.YAW_OFSET_MAX_DEG))

    def _rl(self, ad, x):
        x = clamp(x, self.prev[ad] - K.MAX_DELTA, self.prev[ad] + K.MAX_DELTA)
        self.prev[ad] = x
        return x

    def komut(self, t, dpos, dyaw_rad, dvel, hpos, hvel, heading_deg):
        """-> (thr, pitch, roll, yaw) [-1..1] (rate-limitli). Iki faz:
        hedef UZAKSA lead-pursuit ile uzerine ucar; YAKINSA orbit nokta + kare toplar."""
        dpos = np.asarray(dpos, float)
        dvel = np.asarray(dvel, float)
        hpos = np.asarray(hpos, float)
        hvel = np.asarray(hvel, float)
        los = hpos - dpos
        dist = np.linalg.norm(los)

        if dist > K.YAKIN_ESIK_CM:
            # --- YAKLASMA (pursuit): hedefin LEAD konumuna dogrudan ucur ---
            t_lead = clamp(dist / K.KAPANMA_REF_CMS, 0.0, K.LEAD_MAX_S)
            nokta = hpos + hvel * t_lead
            self.yaw_ofset = 0.0          # pursuit'te hedefe TAM bak (kadraja alsin)
            self.faz = "yaklas"
        else:
            # --- ORBIT: hedef etrafinda nokta sec, kare topla ---
            if self.nokta is None or (t - self.nokta_t0) > K.NOKTA_SURE_S:
                self._yeni_nokta(t)
            d_cm, az_deg, el_deg = self.nokta
            phi = math.radians(heading_deg + az_deg)
            el = math.radians(el_deg)
            ofs = d_cm * np.array([math.cos(el) * math.cos(phi),
                                   math.cos(el) * math.sin(phi),
                                   math.sin(el)])
            nokta = hpos + ofs
            self.faz = "orbit"
        nokta[2] = max(nokta[2], K.MIN_IRTIFA_CM)

        e = nokta - dpos

        # --- yatay: konum -> hiz istegi -> (hiz hatasi) -> pitch/roll ---
        v_des = K.KP_POS * e[:2]
        n = np.linalg.norm(v_des)
        if n > K.V_MAX:
            v_des *= K.V_MAX / n

        if dist < K.EMNIYET_CM and dist > 1.0:                # carpma onleme
            v_des = -(los[:2] / dist) * K.KACIS_CMS

        a = v_des - dvel[:2]
        c, s = math.cos(dyaw_rad), math.sin(dyaw_rad)
        e_fwd = c * a[0] + s * a[1]                           # govde ileri bileseni
        e_rgt = -s * a[0] + c * a[1]                          # govde sag bileseni
        pitch = clamp(K.PITCH_SIGN * K.KV * e_fwd, -K.CMD_MAX, K.CMD_MAX)
        roll = clamp(K.ROLL_SIGN * K.KV * e_rgt, -K.CMD_MAX, K.CMD_MAX)

        # --- dikey ---
        vz_des = clamp(K.KP_POS * e[2], -K.VZ_MAX, K.VZ_MAX)
        thr = clamp(K.KV_Z * (vz_des - dvel[2]), K.THR_MIN, K.THR_MAX)

        # --- yaw: hedefe bak + rastgele ofset ---
        bearing = math.atan2(hpos[1] - dpos[1], hpos[0] - dpos[0])
        yaw = clamp(K.YAW_SIGN * K.KP_YAW * wrap_pi(bearing + self.yaw_ofset - dyaw_rad),
                    -K.YAW_MAX, K.YAW_MAX)

        return (self._rl("thr", thr), self._rl("pitch", pitch),
                self._rl("roll", roll), self._rl("yaw", yaw))


# =============================================================================
#  KAYIT OTURUMU
# =============================================================================
def kadrajda(uv, W, H, marj=K.KADRAJ_MARJ):
    if uv is None:
        return False
    u, v = uv
    return (W * marj <= u <= W * (1.0 - marj)) and (H * marj <= v <= H * (1.0 - marj))


def calistir(args):
    # --- cikti klasoru ---
    if "onedrive" in os.path.abspath(args.cikti).lower():
        print("[UYARI] Cikti OneDrive icinde gorunuyor! Binlerce PNG senkronu bogar.")
        print("        Oneri: --cikti C:\\talon_pose_data\\ham")
    oturum = os.path.join(args.cikti, time.strftime("oturum_%Y%m%d_%H%M%S"))
    os.makedirs(oturum, exist_ok=True)

    # --- baglan + truth dogrulamasi ---
    if not drone.connect():
        print("[HATA] Oyuna baglanilamadi (127.0.0.1:12345). Oyun acik + PLAY modunda mi?")
        print("       Web arayuzu ayni anda ACIK OLMAMALI (oyun tek TCP kabul eder).")
        return 1
    print("[SDK] baglandi, telemetri bekleniyor...")
    time.sleep(2.5)
    truth = drone.get_debug_truth()
    if not truth.get("available"):
        print("[HATA] TRUTH (bozulmamis) telemetri GELMIYOR. Etiketler truth konumdan")
        print("       uretilecegi icin bu kayit ise yaramaz — cikiliyor.")
        print("       Kontrol: arayuzdeki 'Gercek GPS (test)' modu calisiyor muydu?")
        print("       (Calisiyorsa oyun truth gonderiyor demektir; oyunu yeniden baslatip dene.)")
        drone.disconnect()
        return 1
    print("[SDK] truth telemetri AKIYOR (available=True).")

    kaynak = KareKaynagi()
    print("[KARE] kaynak:", kaynak.mod)

    # --- meta ---
    meta = {
        "olusturma": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hfov_deg": geometri.KAMERA_HFOV_DEG,
        "kamera_tilt_deg": geometri.KAMERA_TILT_DEG,
        "kayit_hz": args.hz,
        "min_mesafe_cm": K.MIN_MESAFE_CM, "max_mesafe_cm": K.MAX_MESAFE_CM,
        "kadraj_marj": K.KADRAJ_MARJ,
        "birimler": "cm, derece, cm/s; rot tuple sirasi SDK: (roll, pitch, yaw)",
        "not": ("Konum etiketi icin truth_target_pos kullanin (bozulmamis). "
                "target_rot_rpy truth'ta YOK -> normal kanaldan; Faz 4 heading "
                "capraz-kontroluyle dogrulanir."),
    }
    with open(os.path.join(oturum, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    jsonl = open(os.path.join(oturum, "telemetri.jsonl"), "w", encoding="utf-8")
    # Surekli (her tik ~50Hz) zaman-damgali telemetri akisi. Kare 't' ile AYNI saat
    # (perf_counter). pose/kalibre.py bunu kullanip latency Δt'yi cozer: kareyi
    # (t - Δt) anindaki poz'la eslestirip best.pt tespitine oturtan Δt'yi bulur.
    akis = open(os.path.join(oturum, "telemetri_akis.jsonl"), "w", encoding="utf-8")
    png = PngYazici()
    oto = OrbitOtopilot()
    izci = HedefIzleyici()

    if not args.pasif:
        drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # arm
        print("[UCUS] arm edildi; orbit otopiloti aktif (yumusak kazanclar).")
    else:
        print("[UCUS] PASIF mod: komut gonderilmiyor, sadece kayit.")

    dt_kontrol = 1.0 / K.KONTROL_HZ
    kayit_periyot = 1.0 / args.hz
    t0 = time.perf_counter()
    son_kayit = 0.0
    son_durum = 0.0
    n_kayit = 0
    n_red_kadraj = 0
    n_red_mesafe = 0

    print("[KAYIT] basladi -> %s  (durdurmak icin CTRL-C)" % oturum)
    try:
        while True:
            t = time.perf_counter()
            if args.dakika > 0 and (t - t0) > args.dakika * 60.0:
                print("[KAYIT] sure doldu.")
                break
            if not drone.is_connected():
                print("[HATA] SDK baglantisi koptu.")
                break

            # --- telemetri (tek seferde tutarli okuma) ---
            tel = drone.get_telemetry()
            tru = drone.get_debug_truth()
            dpos = tel["drone"]["position"]
            drot = tel["drone"]["rotation"]          # (roll, pitch, yaw)
            dvel = tel["drone"]["velocity"]
            hpos = tru["target"]["position"]         # TRUTH konum (bozulmamis)
            izci.guncelle(t, hpos)

            # --- surekli telemetri akisi (her tik; latency kalibrasyonu icin) ---
            akis.write(json.dumps({
                "t": t, "dp": list(dpos), "dr": list(drot),
                "tp": list(hpos), "tr": list(tel["target"]["rotation"]),
                "cm": int(tru.get("corruption_mask", 0)),
            }) + "\n")

            # --- kontrol ---
            if not args.pasif:
                thr, pit, rol, yw = oto.komut(t, dpos, math.radians(drot[2]),
                                              dvel, hpos, izci.vel, izci.heading_deg)
                drone.set_control_surfaces(thr, pit, rol, yw, True)

            # --- kayit ---
            if (t - son_kayit) >= kayit_periyot:
                son_kayit = t
                kare = kaynak.get()
                if kare is not None:
                    H, W = kare.shape[:2]
                    cam_pos, R_cam = geometri.kamera_pozu(dpos, drot)
                    fx = geometri.fx_from_hfov(W)
                    uv = geometri.projekte(hpos, cam_pos, R_cam, fx, W, H)
                    d_cm = float(np.linalg.norm(np.asarray(hpos) - np.asarray(dpos)))

                    if not (K.MIN_MESAFE_CM < d_cm < K.MAX_MESAFE_CM):
                        n_red_mesafe += 1
                    elif not kadrajda(uv, W, H):
                        n_red_kadraj += 1
                    else:
                        n_kayit += 1
                        ad = "kare_%06d.png" % n_kayit
                        png.yaz(os.path.join(oturum, ad), kare)
                        satir = {
                            "t": t, "kare": ad, "W": W, "H": H,
                            "drone_pos": list(dpos), "drone_rot_rpy": list(drot),
                            "drone_vel": list(dvel),
                            "target_pos_ham": list(tel["target"]["position"]),
                            "target_rot_rpy": list(tel["target"]["rotation"]),
                            "target_speed_ham": tel["target"]["speed"],
                            "truth_target_pos": list(hpos),
                            "truth_target_speed": tru["target"]["speed"],
                            "truth_drone_pos": list(tru["drone"]["position"]),
                            "corruption_mask": int(tru.get("corruption_mask", 0)),
                            "am_uv": [float(uv[0]), float(uv[1])],
                            "mesafe_cm": d_cm,
                            "hedef_heading_deg": izci.heading_deg,
                        }
                        jsonl.write(json.dumps(satir) + "\n")
                        jsonl.flush()

            # --- 1 Hz durum satiri ---
            if (t - son_durum) >= 1.0:
                son_durum = t
                akis.flush()                          # akisi periyodik diske yaz
                d_m = (np.linalg.norm(np.asarray(hpos) - np.asarray(dpos)) / 100.0)
                print("[KAYIT] %5.0fsn | %-6s | kayit=%d | red(kadraj=%d mesafe=%d) | "
                      "d=%.1fm | png_kuyruk=%d dusen=%d"
                      % (t - t0, ("PASIF" if args.pasif else oto.faz), n_kayit,
                         n_red_kadraj, n_red_mesafe, d_m, png.q.qsize(), png.dusen))

            kalan = dt_kontrol - (time.perf_counter() - t)
            if kalan > 0:
                time.sleep(kalan)
    except KeyboardInterrupt:
        print("\n[KAYIT] CTRL-C — durduruluyor.")
    finally:
        if not args.pasif:
            try:
                drone.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)   # hover birak
                print("[UCUS] hover komutu birakildi (motorlar ACIK).")
            except Exception:
                pass
        png.kapat()
        jsonl.close()
        akis.close()
        drone.disconnect()
        print("[OZET] kayit=%d | png yazilan=%d dusen=%d | red kadraj=%d mesafe=%d"
              % (n_kayit, png.yazilan, png.dusen, n_red_kadraj, n_red_mesafe))
        print("[OZET] klasor: %s" % oturum)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Pose veri toplama ucusu (Faz 1) — bkz. POSE_REHBERI.md")
    ap.add_argument("--cikti", default=r"C:\talon_pose_data\ham",
                    help=r"cikti koku (vars: C:\talon_pose_data\ham; OneDrive'a KOYMA)")
    ap.add_argument("--dakika", type=float, default=10.0,
                    help="kayit suresi dk (0 = CTRL-C'ye kadar; vars: 10)")
    ap.add_argument("--hz", type=float, default=K.KAYIT_HZ,
                    help="kare kayit sikligi (vars: %.0f)" % K.KAYIT_HZ)
    ap.add_argument("--pasif", action="store_true",
                    help="komut gonderme (arm dahil) — sadece izle ve kaydet")
    sys.exit(calistir(ap.parse_args()))


if __name__ == "__main__":
    main()
