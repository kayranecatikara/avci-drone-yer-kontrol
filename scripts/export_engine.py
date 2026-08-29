# -*- coding: utf-8 -*-
"""
scripts/export_engine.py — talon agirligini TensorRT motoruna (.engine) cevirir.

    python -m scripts.export_engine                 # talon_v3.pt -> talon_v3.engine (FP16)
    python -m scripts.export_engine --model best.pt
    python -m scripts.export_engine --fp32          # motoru FP32 kur (karsilastirma icin)
    python -m scripts.export_engine --bench-only    # cevirme, sadece olc ve karsilastir
    python -m scripts.export_engine --runs 100      # olcum tekrari (varsayilan 50)
    AVCI_IMGSZ=1920 python -m scripts.export_engine # baska olcekte motor uret

NEDEN. Hat butcemizde darbogaz GPU hesabi degil, CEKIRDEK BASLATMA giderindir
(CLAUDE.md: imgsz 640 -> 10.48 ms / 21.7 GFLOPs, imgsz 960 -> 10.59 ms /
49.1 GFLOPs = 2.3 kat is, ayni sure). TensorRT'nin katman fuzyonu tam da bu
gideri hedefler: cok sayida kucuk cekirdek yerine az sayida buyuk cekirdek.
Kazanc VAAT EDILMEZ, bu betik OLCER.

⛔ MOTOR TASINMAZ. .engine dosyasi SU KARTA, SU SURUCUYE ve SU TensorRT
   surumune derlenir. Baska makineye kopyalanamaz (bu yuzden .gitignore'da).
   Kart, surucu, TensorRT ya da model degisince YENIDEN URETIN.

⭐ IMGSZ MOTORA GOMULUR ve motordan geri okunur. Static motorun girdisi
   960x960'a SABITTIR; baska olcekte kare gelirse TensorRT arka ucu assert
   atar ve detect_all sessizce bos doner. Bu yuzden olcu tek kaynaktan
   (perception.detector) alinir, motorun basligina yazilir, detector de
   calisirken oradan geri okur — arada elle tutulan ikinci bir sayi yoktur.

DOGRULAMA. Cevirim sonrasi .pt ve .engine AYNI girdi tensoru ile beslenir ve
NMS ONCESI ham cikti tensorleri karsilastirilir. Boylece dogrulama karenin
icerigine bagli olmaz: rastgele karede bile agin sayilari karsilastirilabilir.
Ayrica ikisinin kare basi suresi (arka uc ileri gecisi + uctan uca predict)
olculur.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.detector import MODELS_DIR, imgsz_for_model  # noqa: E402

# (yukseklik, genislik) piksel; olcum karesinin boyutu. GERCEK yakalama
# cozunurlugunde uretilir, cunku uctan uca sure letterbox + BGR->tensor
# maliyetini de icerir; kucuk kareyle olcmek o maliyeti gizler ve motoru
# oldugundan iyi gosterir.
BENCH_FRAME_HW = (1200, 1920)


def _log(msg):
    """Betigin tum ciktisi buradan gecer — [ENGINE] onekiyle, tamponsuz."""
    print("[ENGINE] %s" % msg, flush=True)


def export(pt_path, imgsz, fp16=True, workspace=None):
    """Agirligi TensorRT motoruna cevirir (.pt -> .engine).

    pt_path   : cevrilecek .pt agirligi
    imgsz     : px; motorun girdi olcegi. STATIC motorda bu deger DERLENIRKEN
                SABITLENIR; sonradan degistirilemez, yeniden uretmek gerekir.
    fp16      : True -> FP16 motor (daha hizli, dosya yari boyutta)
                False -> FP32 motor (.pt ile BIREBIR ayni sayi; bu depoda secilen)
    workspace : GiB; TensorRT'nin calisma alani (None -> ultralytics varsayilani)
    -> uretilen .engine dosyasinin yolu (.pt'nin yaninda birakilir)
    """
    from ultralytics import YOLO

    kwargs = dict(format="engine", imgsz=imgsz, device=0, batch=1,
                  dynamic=False, simplify=True, verbose=False)
    if workspace is not None:
        kwargs["workspace"] = float(workspace)

    # FP16 anahtarinin adi ultralytics surumleri arasinda degisti:
    # yeni surum quantize=16, eski surum half=True. Once yeniyi dene.
    precision = ([{"quantize": 16}, {"half": True}] if fp16 else [{}])
    last = None
    model = YOLO(pt_path)
    for kw in precision:
        try:
            return model.export(**kwargs, **kw)
        except TypeError as e:
            last = e
            continue
    raise last if last else RuntimeError("export basarisiz")


def _backend(path, device="cuda:0", fp16=True):
    """Agirligi AutoBackend ile yukler — .pt ve .engine AYNI arayuzden kosar.

    Boylece iki kol, ultralytics'in `predict()` giderini ICERMEDEN, yalnizca
    ARKA UC ILERI GECISI olarak karsilastirilabilir.
    """
    import torch
    from ultralytics.nn.autobackend import AutoBackend

    be = AutoBackend(path, device=torch.device(device), fp16=fp16, verbose=False)
    be.eval()
    return be


def _frame(frame_hw):
    """Olcum karesi uretir (rastgele gurultu, uint8 BGR).

    frame_hw : (yukseklik, genislik) piksel
    -> ndarray

    ⭐ TOHUM SABITTIR (0): iki arka uc BIREBIR ayni pikselleri gorur, yoksa
      cikti farki modelden mi girdiden mi geldi ayirt edilemezdi. Icerik
      rastgele olabilir cunku karsilastirma NMS ONCESI ham tensorler
      uzerindedir — anlamli bir tespit gerekmez.
    """
    import numpy as np

    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (frame_hw[0], frame_hw[1], 3), dtype=np.uint8)


def _input_tensor(frame, imgsz, device, fp16):
    """Gercek hattaki on islemin aynisi: letterbox -> BCHW -> /255.

    ⚠ TIP ARKA UCA GORE SECILIR. Ultralytics FP16 motorda bile GIRDI/CIKIS
       baglantilarini FP32 birakir; arka uca yanlis tipte tensor verilirse
       TensorRT bitleri OLDUGU GIBI yorumlar (sekil dogru oldugu icin assert
       de atmaz) ve cikti COPTUR. predictor bunu kendi yapar, elle olcerken
       atlanmasi kolaydir — bu yuzden burada acikca yaziliyor.
    """
    import torch
    from ultralytics.data.augment import LetterBox

    im = LetterBox((imgsz, imgsz), auto=False)(image=frame)
    x = torch.from_numpy(im.transpose(2, 0, 1)[None].copy()).to(device)
    return (x.half() if fp16 else x.float()) / 255.0


def compare(pt_path, engine_path, imgsz, runs=50):
    """Iki arka ucu AYNI kareyle karsilastirir: ham cikti farki + kare basi sure.

    runs : olcum tekrari (n >= 30 tutun; GPU saat rampasi kisa olcumu bozar)
    -> (kare, sonuc sozlugu)

    Karsilastirma NMS ONCESI ham tensorler uzerindedir; boylece dogrulama
    karenin ICERIGINE bagli olmaz. Skor kanali sinirli (0..1) oldugu icin
    farki dogrudan anlamlidir; kutu kanallari ise yalnizca SKORU YUKSEK
    capalarda anlamlidir.
    """
    import torch

    frame = _frame(BENCH_FRAME_HW)
    out = {}

    for tag, path in (("pt", pt_path), ("engine", engine_path)):
        be = _backend(path, fp16=True)
        x = _input_tensor(frame, imgsz, be.device, bool(be.fp16))
        with torch.inference_mode():
            for _ in range(10):           # isinma: ilk cagrilar tahsis yapar
                y = be(x)
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(runs):
                y = be(x)
            torch.cuda.synchronize()
            fwd_ms = (time.perf_counter() - t0) * 1000.0 / runs
        y0 = y[0] if isinstance(y, (list, tuple)) else y
        out[tag] = {"y": y0.float().cpu(), "fwd_ms": fwd_ms, "fp16_in": bool(be.fp16)}
        del be
        torch.cuda.empty_cache()

    a, b = out["pt"]["y"], out["engine"]["y"]
    if a.shape != b.shape:
        out["shape"] = (tuple(a.shape), tuple(b.shape))
        out["score_max"] = out["box_max"] = float("nan")
        return frame, out

    # Cikti duzeni: [1, 4+nc, anchor]. Skor kanali SINIRLI (0..1) -> farki
    # dogrudan anlamlidir. Kutu kanallari yalnizca SKORU YUKSEK capalarda
    # anlamlidir: dusuk skorlu capanin kutusu zaten kullanilmaz, oradaki fark
    # "model bozuldu" demek degildir.
    out["shape"] = tuple(a.shape)
    sa, sb = a[0, 4:].max(0).values, b[0, 4:].max(0).values
    out["score_max"] = float((sa - sb).abs().max())
    out["score_mean"] = float((sa - sb).abs().mean())
    k = min(32, sa.numel())
    idx = sa.topk(k).indices
    out["box_max"] = float((a[0, :4, idx] - b[0, :4, idx]).abs().max())
    out["top_score_pt"] = float(sa.max())
    out["top_score_en"] = float(sb.max())
    return frame, out


def end_to_end(path, frame, imgsz, runs=50):
    """Uctan uca `predict()` suresi — hatta FIILEN odenen milisaniye.

    -> kare basi ortalama sure (ms)

    `compare`in olctugu saf ileri geciste gorunmeyen her sey buraya dahildir:
    letterbox, tensore kopya, NMS, `Results` nesnesi. Motorun uctan uca
    kazanci saf ileri gecistekinden KUCUKTUR, cunku darbogaz o katmana kayar.
    """
    from ultralytics import YOLO

    model = YOLO(path)
    for _ in range(10):
        model.predict(frame, imgsz=imgsz, conf=0.10, device=0, verbose=False)
    t0 = time.perf_counter()
    for _ in range(runs):
        model.predict(frame, imgsz=imgsz, conf=0.10, device=0, verbose=False)
    return (time.perf_counter() - t0) * 1000.0 / runs


def main():
    """Giris noktasi: (istege bagli) cevir, sonra OLC ve dogrula.

    -> surec cikis kodu (0 = basarili, 2 = onkosul saglanmadi)

    Akis: agirligi bul -> CUDA/TensorRT var mi? -> cevir -> ara urunleri
    (.onnx) sil -> ham cikti farkini ve kare basi sureyi olc.
    """
    ap = argparse.ArgumentParser(description="talon agirligi -> TensorRT motoru")
    ap.add_argument("--model", default=None,
                    help="perception/models/ icindeki .pt (varsayilan: talon_v3.pt)")
    ap.add_argument("--fp32", action="store_true", help="motoru FP32 kur")
    ap.add_argument("--imgsz", type=int, default=None,
                    help="cikarim olcegi (varsayilan: AVCI_IMGSZ, yoksa modelin egitim olcegi)")
    ap.add_argument("--workspace", type=float, default=None, help="TensorRT calisma alani (GiB)")
    ap.add_argument("--runs", type=int, default=50, help="olcum tekrari (n>=30 tutun)")
    ap.add_argument("--bench-only", action="store_true", help="cevirme, sadece olc")
    ap.add_argument("--no-bench", action="store_true", help="cevir, olcme")
    args = ap.parse_args()

    name = args.model or os.environ.get("AVCI_MODEL") or "talon_v3.pt"
    pt_path = os.path.join(MODELS_DIR, os.path.basename(name))
    if not pt_path.endswith(".pt"):
        pt_path = os.path.splitext(pt_path)[0] + ".pt"
    if not os.path.isfile(pt_path):
        _log("YOK: %s" % pt_path)
        return 2
    engine_path = os.path.splitext(pt_path)[0] + ".engine"
    # Olcu onceligi: --imgsz > AVCI_IMGSZ > modelin egitim olcegi.
    # ⭐ AVCI_IMGSZ burada da okunur ki dedektorle AYNI anlama gelsin: orada
    #   "motorun olcusuyle cakisirsa .pt'ye dus" demek, burada "motoru O
    #   olcekte uret" demektir. Iki yerde farkli anlasilirsa kullanici
    #   AVCI_IMGSZ=1920 verip neden hala 960 kostugunu anlayamaz.
    imgsz = args.imgsz or int(os.environ.get("AVCI_IMGSZ") or imgsz_for_model(pt_path))

    import torch
    if not torch.cuda.is_available():
        _log("CUDA yok -> TensorRT motoru URETILEMEZ (sistem .pt ile calismaya devam eder).")
        return 2
    _log("GPU: %s | torch %s (cuda %s)" % (torch.cuda.get_device_name(0),
                                           torch.__version__, torch.version.cuda))

    if not args.bench_only:
        try:
            import tensorrt as trt
            _log("TensorRT %s" % trt.__version__)
        except Exception as e:
            _log("tensorrt kurulu degil (%r).  pip install tensorrt-cu13 onnx onnxslim" % e)
            return 2
        _log("cevriliyor: %s -> %s (imgsz=%d, %s)"
             % (os.path.basename(pt_path), os.path.basename(engine_path),
                imgsz, "FP32" if args.fp32 else "FP16"))
        t0 = time.perf_counter()
        out = export(pt_path, imgsz, fp16=not args.fp32, workspace=args.workspace)
        _log("motor kuruldu: %s (%.0f s, %.1f MB)"
             % (out, time.perf_counter() - t0, os.path.getsize(out) / 1e6))
        # ONNX yalnizca ARA URUNDUR (ultralytics .pt -> .onnx -> .engine gider).
        # Birakilirsa ~57 MB olu dosya kalir ve "hangisi kosuyor?" sorusunu
        # bulandirir; dedektor .onnx'e ZATEN bakmaz.
        for tmp in (os.path.splitext(pt_path)[0] + ".onnx",
                    os.path.splitext(pt_path)[0] + ".fp16.onnx"):
            if os.path.isfile(tmp):
                os.remove(tmp)
                _log("ara urun silindi: %s" % os.path.basename(tmp))

    if args.no_bench:
        return 0
    if not os.path.isfile(engine_path):
        _log("motor yok: %s" % engine_path)
        return 2

    frame, r = compare(pt_path, engine_path, imgsz, runs=args.runs)
    _log("ham cikti %s | skor farki max %.5f ort %.6f | en yuksek skor .pt %.5f / .engine %.5f"
         % (r["shape"], r["score_max"], r.get("score_mean", float("nan")),
            r.get("top_score_pt", float("nan")), r.get("top_score_en", float("nan"))))
    _log("en yuksek skorlu 32 capada kutu farki: max %.3f px (girdi tipi: .pt %s, .engine %s)"
         % (r["box_max"], "fp16" if r["pt"]["fp16_in"] else "fp32",
            "fp16" if r["engine"]["fp16_in"] else "fp32"))
    pt_ms, en_ms = r["pt"]["fwd_ms"], r["engine"]["fwd_ms"]
    _log("arka uc ileri gecis (n=%d):  .pt %.2f ms  |  .engine %.2f ms  (%.2fx)"
         % (args.runs, pt_ms, en_ms, pt_ms / en_ms if en_ms else float("nan")))

    e2e_pt = end_to_end(pt_path, frame, imgsz, runs=args.runs)
    e2e_en = end_to_end(engine_path, frame, imgsz, runs=args.runs)
    _log("uctan uca predict (n=%d):    .pt %.2f ms (%.1f FPS)  |  .engine %.2f ms (%.1f FPS)  (%.2fx)"
         % (args.runs, e2e_pt, 1000.0 / e2e_pt, e2e_en, 1000.0 / e2e_en,
            e2e_pt / e2e_en if e2e_en else float("nan")))
    _log("ARTIK VARSAYILAN: detector .engine varsa onu yukler (AVCI_ENGINE=0 ile .pt'ye don).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
