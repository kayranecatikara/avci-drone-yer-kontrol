"""bench_sahi.py — IZOLE det_ms benchmark: SAHI acik vs kapali.

Amac: ayni ornek kare uzerinde gorsel_tespit.py'nin MEVCUT YOLO+SAHI sarmalayicisiyla
inference suresini kiyaslamak. Ucus dongusu / web sunucusu / drone_sdk YOK — yalniz dedektor.

Kullanim:
    python bench_sahi.py --frame ornek.png      # verilen kareyi kullan
    python bench_sahi.py                         # oyundan tek kare yakala, veri/bench_frame.png'e kaydet

Notlar:
- SAHI mantigi YENIDEN YAZILMAZ; var olan HedefDedektor cagrilir. Modlar tek dedektor
  ornegi uzerinde runtime override ile secilir (Cfg / dosya KALICI bozulmaz).
- SAHI=ON modda kosullu kapi (SAHI_KOSUL_CONF) DEVRE DISI (kosul_conf=0.0) -> her karede
  gercekten dilimler; boylece dilimlemenin HAM maliyeti olculur.
- det_ms olcumu canli hattaki gibi tespit_hepsi() cagrisini sarar; CUDA senkronludur.
"""
import argparse
import os
import statistics as st
import sys
import time

# proje kokunu sys.path'e ekle (script kokten de arac/ altindan da kossa calissin)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from detection.gorsel_tespit import HedefDedektor          # noqa: E402
from guidance.ana_kontrol import Cfg                        # noqa: E402

GAME_TITLE_HINTS = ["dronesofwar", "drones of war", "drone of war"]
VERI_DIR = os.path.join(_ROOT, "veri")
FP16_AKTIF = os.environ.get("AVCI_FP16", "1").strip() == "1"
N_TEKRAR = 30


def _cuda_senkron():
    """GPU is-kuyrugu bosalt (dogru zamanlama icin). Cuda yoksa no-op."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        pass


def _kare_yukle(frame_arg):
    """--frame verilmisse onu (BGR ndarray) yukle; verilmemisse oyundan tek kare yakala.
    Canli hat pencere-icerigini BGR olarak dedektore verdiginden cv2.imread (BGR) kullanilir."""
    import cv2
    if frame_arg:
        bgr = cv2.imread(frame_arg)
        if bgr is None:
            print("HATA: kare okunamadi:", frame_arg)
            sys.exit(1)
        return bgr, frame_arg

    # kare yok -> pencere_yakala ile oyundan tek kare
    from detection.pencere_yakala import PencereYakala
    yak = PencereYakala(title_hints=GAME_TITLE_HINTS)
    yak.baslat()
    bgr = None
    t0 = time.time()
    while time.time() - t0 < 5.0:                 # ~5 sn kare bekle
        bgr = yak.get_latest_bgr()
        if bgr is not None:
            break
        time.sleep(0.05)
    yak.durdur()
    if bgr is None:
        print("HATA: oyundan kare yakalanamadi (oyun acik mi? pencere basligi: %s)"
              % GAME_TITLE_HINTS)
        sys.exit(1)
    os.makedirs(VERI_DIR, exist_ok=True)
    yol = os.path.join(VERI_DIR, "bench_frame.png")
    cv2.imwrite(yol, bgr)
    return bgr, yol


def _olc(dedektor, bgr):
    """N_TEKRAR kez tespit_hepsi -> det_ms listesi (ilk kare warmup, ayri)."""
    dedektor.tespit_hepsi(bgr, maske=None)        # WARMUP (olculmez)
    _cuda_senkron()
    sureler = []
    for _ in range(N_TEKRAR):
        _cuda_senkron()
        t0 = time.perf_counter()
        dedektor.tespit_hepsi(bgr, maske=None)
        _cuda_senkron()
        sureler.append((time.perf_counter() - t0) * 1000.0)
    return sureler


def _ozet(sureler):
    s = sorted(sureler)
    n = len(s)
    p10 = s[max(0, int(0.10 * n))]
    p90 = s[min(n - 1, int(0.90 * n))]
    return st.median(s), p10, p90


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", default=None, help="ornek kare (png/jpg); yoksa oyundan yakalar")
    args = ap.parse_args()

    bgr, kare_yol = _kare_yukle(args.frame)
    H, W = int(bgr.shape[0]), int(bgr.shape[1])

    # TEK dedektor ornegi; modlar arasi runtime override (imgsz/half/SAHI param = canli hat).
    dedektor = HedefDedektor(
        Cfg.VIS_MODEL_PATH, conf=Cfg.VIS_CONF_MIN, imgsz=640, half=FP16_AKTIF,
        sahi=True,                                          # ON ile basla; asagida toggle
        sahi_dilim=getattr(Cfg, "SAHI_DILIM_PX", 640),
        sahi_ortusme=getattr(Cfg, "SAHI_ORTUSME", 0.2),
        sahi_kosul_conf=0.0,                                # KOSUL KAPISI KAPALI -> hep dilimle
    )
    if not dedektor.hazir:
        print("HATA: dedektor yuklenemedi ->", dedektor.hata)
        sys.exit(1)

    # SAHI=ON'da kare basina kac predict: 1 tam-kare + dilim sayisi
    dilimler = HedefDedektor._dilimler(W, H, dedektor.sahi_dilim, dedektor.sahi_ortusme)
    slice_count = 1 + len(dilimler)

    # hangi FP16 arg secildi (bos ise FP16 sessizce FP32'ye dustu -> onemli teshis)
    fp16_arg = dedektor._fp16_kwargs or "FP32(dustu)"

    # --- SAHI = ON (dilimlemeyi zorla) ---
    dedektor.sahi = True
    dedektor.sahi_kosul_conf = 0.0
    on = _olc(dedektor, bgr)

    # --- SAHI = OFF (tek tam-kare predict) ---
    dedektor.sahi = False
    off = _olc(dedektor, bgr)

    on_med, on_p10, on_p90 = _ozet(on)
    off_med, off_p10, off_p90 = _ozet(off)
    speedup = (on_med / off_med) if off_med > 1e-6 else float("nan")

    print("\n" + "=" * 56)
    print("device=%s / fp16=%s (arg=%s) / frame_res=%dx%d / slice_count=%d"
          % (dedektor.device, "on" if FP16_AKTIF else "off", fp16_arg, W, H, slice_count))
    print("kare: %s   (N=%d tekrar, ilk warmup haric)" % (kare_yol, N_TEKRAR))
    print("-" * 56)
    print("SAHI=ON   det_ms  med=%.1f  p10=%.1f  p90=%.1f" % (on_med, on_p10, on_p90))
    print("SAHI=OFF  det_ms  med=%.1f  p10=%.1f  p90=%.1f" % (off_med, off_p10, off_p90))
    print("speedup = ON/OFF = %.1fx" % speedup)
    print("=" * 56)


if __name__ == "__main__":
    main()
