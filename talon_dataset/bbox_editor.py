# -*- coding: utf-8 -*-
"""
======================================================================
 TALON BBOX EDITOR  —  Manuel Bounding Box Cizim / Dogrulama Araci
======================================================================
Amac:
  - dataset/ icindeki her .png icin bounding box'i FARE ile surukleyerek
    Talon'un gercek goruntusune SIKI ve PADDING'SIZ oturtmak.
  - Sonucu YOLO Detection formatinda TEXT (.txt) olarak kaydetmek.

KUTSAL KURALLAR (degismez):
  - capture_controller'a ASLA dokunulmaz (o ayri calisir, JSON'lari o uretir).
  - Kaynak dataset/ icindeki .png ve .json SADECE OKUNUR. Hicbiri degistirilmez.
  - JSON'dan SADECE "keypoints_2d" (Talon'un ekran konumu) okunur.
    FOV / kamera acisi / kamera konumu / drone_rotation = OKUNMAZ, kullanilmaz.
  - Save -> Desktop'taki Talon_Box_Dataset klasorune: png KOPYASI + .txt gider.
  - Dosya isimleri ASLA degismez (talon_0001.png <-> talon_0001.txt).

Etiket formati (Detection):  "0 cx cy w h"   (hepsi 0-1 normalize)
======================================================================
"""

import os
import json
import shutil
import math
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


def _recycle(paths):
    """Verilen dosya(lar)i Windows Geri Donusum Kutusu'na tasir (GERI ALINABILIR).
    paths: tek yol (str) veya yol listesi. Var olmayanlar sessizce atlanir.
    Donus: True = islem tamam. shell32 yoksa (Windows disi) kalici silmeye duser."""
    if isinstance(paths, str):
        paths = [paths]
    existing = [p for p in paths if p and os.path.exists(p)]
    if not existing:
        return True  # silinecek bir sey yok = basarili say
    try:
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]
        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040        # <-- Geri Donusum Kutusu (kalici degil)
        FOF_NOCONFIRMATION = 0x0010   # ekstra "emin misin" sormaz
        FOF_SILENT = 0x0004
        FOF_NOERRORUI = 0x0400
        buf = "\0".join(existing) + "\0\0"   # pFrom cift-null ile bitmeli
        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = buf
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        return res == 0
    except Exception:
        # shell32 yok (Windows disi) -> kalici sil (en azindan temizlenir)
        ok = True
        for p in existing:
            try:
                os.remove(p)
            except Exception:
                ok = False
        return ok


# ------------------------------------------------------------------
# AYARLAR  (raw string r"" - Windows uyumlu)
# ------------------------------------------------------------------
SOURCE_DIR = r"C:\Users\Zeylo\Desktop\talon_dataset\dataset"     # Kaynak (SALT OKUNUR)
OUTPUT_DIR = r"C:\Users\Zeylo\Desktop\Talon_Box_Dataset"         # Cikti (png + txt buraya)


def _find_model_path():
    """Paket icinde best.pt'yi bilinen yerlerde arar (tasinabilir, hardcoded yol yok)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "model", "best.pt"),
              os.path.join(here, "best", "best.pt"),
              os.path.join(here, "best.pt")):
        if os.path.exists(c):
            return c
    return None


MODEL_PATH = _find_model_path()   # opsiyonel YOLO modeli (yoksa None -> elle/keypoint)
MODEL_CONF = 0.25                 # model icin minimum guven skoru

# Kose renkleri (senin istegin: her koseye bir renk)
CORNER_COLORS = {
    "TL": "#FF3030",   # Sol-Ust  -> kirmizi
    "TR": "#22C55E",   # Sag-Ust  -> yesil
    "BR": "#3B82F6",   # Sag-Alt  -> mavi
    "BL": "#FACC15",   # Sol-Alt  -> sari
}
CORNER_TR = {"TL": "Sol-Ust", "TR": "Sag-Ust", "BR": "Sag-Alt", "BL": "Sol-Alt"}

BOX_OUTLINE = "#00E5FF"   # kutu cizgisi (camgobegi)
EDGE_HANDLE = "#FFFFFF"   # kenar-ortasi tutamaklari (beyaz kare)
SEED_PT     = "#9CA3AF"   # tohum keypoint noktalari (gri)


class BBoxEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("TALON BBOX EDITOR — Manuel Bounding Box Araci")
        self.root.geometry("1400x900")
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        # Cikti klasorunu olustur (yoksa)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Durum degiskenleri
        self.frames_list = []
        self.current_idx = 0
        self.pil_img = None
        self.img_w = 1920
        self.img_h = 1080
        self.current_json_data = {}

        # Kutu = [x1, y1, x2, y2] orijinal piksel koordinatinda (x1<x2, y1<y2)
        self.box = None
        self.drag_mode = None        # "TL".."BL", "T/R/B/L", "MOVE", "NEW" veya None
        self.new_start = None
        self.move_anchor_img = None
        self.box_at_grab = None

        # Zoom / Pan durumu
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Tutamak boyutlari
        self.handle_r = 7
        self.grab_radius = 15

        self.show_points = tk.BooleanVar(value=True)

        # Model (best.pt) - opsiyonel, arka planda lazy yuklenir
        self.model = None
        self.model_loaded = False
        self.current_img_path = None
        self.box_is_seed = False
        self.auto_model = tk.BooleanVar(value=bool(MODEL_PATH))

        self.create_widgets()
        self.load_dataset_files()

        # Model varsa arka planda yukle (GUI donmasin); bitince mevcut kareye uygula
        if MODEL_PATH and self.auto_model.get():
            self._start_model_load()

    # ==============================================================
    # ARAYUZ
    # ==============================================================
    def create_widgets(self):
        # Ust baslik + yardim
        title_frame = tk.Frame(self.root, bg="#2A2D32", pady=8)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="TALON BBOX EDITOR  —  Manuel Bounding Box",
                 font=("Arial", 15, "bold"), fg="white", bg="#2A2D32").pack()
        tk.Label(title_frame,
                 text="Sol-tik: koseyi/kenari surukle  |  Kutu icini surukle: tasi  |  "
                      "Bos alana tikla-surukle: yeni kutu  |  Sag-tik: kaydir  |  Tekerlek: zoom  |  "
                      "ENTER: kaydet + sonraki kare",
                 font=("Arial", 9), fg="#A0A5B0", bg="#2A2D32").pack()

        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4, bg="#101418")
        main_pane.pack(fill=tk.BOTH, expand=True)

        # --- SOL PANEL: liste + legend ---
        left_frame = tk.Frame(main_pane, bg="#1E2022", width=270)
        tk.Label(left_frame, text="Kareler (dataset/)", font=("Arial", 11, "bold"),
                 fg="white", bg="#1E2022", pady=5).pack()

        # Renk legend'i (altta)
        leg = tk.LabelFrame(left_frame, text="Kose Renkleri", bg="#1E2022", fg="white",
                            font=("Arial", 9, "bold"), padx=5, pady=5)
        leg.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        for key in ["TL", "TR", "BR", "BL"]:
            row = tk.Frame(leg, bg="#1E2022")
            row.pack(fill=tk.X, pady=1)
            tk.Canvas(row, width=12, height=12, bg=CORNER_COLORS[key],
                      highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(row, text=f"  {CORNER_TR[key]}", fg="white", bg="#1E2022",
                     font=("Arial", 8)).pack(side=tk.LEFT)
        # Durum aciklamasi
        tk.Label(leg, text="[✓]=etiketli  [–]=atlandi", fg="#9CA3AF", bg="#1E2022",
                 font=("Arial", 8)).pack(anchor=tk.W, pady=(4, 0))

        self.listbox = tk.Listbox(left_frame, bg="#2D3035", fg="white",
                                  selectbackground="#1E64FA", font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        main_pane.add(left_frame)

        # --- SAG ALAN: canvas + butonlar ---
        right_area = tk.Frame(main_pane, bg="#252729")
        main_pane.add(right_area)

        self.canvas = tk.Canvas(right_area, bg="#18191B", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_drag)

        # Alt buton seridi
        bottom = tk.Frame(right_area, bg="#1E2022", pady=8)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        bar = tk.Frame(bottom, bg="#1E2022")
        bar.pack(anchor=tk.CENTER)

        def mkbtn(text, cmd, color, w=11):
            b = tk.Button(bar, text=text, bg=color, fg="white", font=("Arial", 10, "bold"),
                          command=cmd, width=w, relief=tk.FLAT, activebackground="#555")
            b.pack(side=tk.LEFT, padx=4, pady=4)
            return b

        mkbtn("<< Onceki", self.prev_frame, "#3D4045")
        mkbtn("Sonraki >>", self.next_frame, "#3D4045")
        mkbtn("Zoom +", self.zoom_in, "#3D4045", 7)
        mkbtn("Zoom -", self.zoom_out, "#3D4045", 7)
        mkbtn("KAYDET & Dogrula", self.save_current_frame, "#1E64FA", 16)
        mkbtn("Sifirla (tohum)", self.reset_to_seed, "#0E7490", 13)
        mkbtn("Temizle", self.clear_box, "#7C3AED", 9)
        mkbtn("Modelden Ciz", self.draw_from_model, "#0D9488", 12)
        mkbtn("Bu Kareyi SIL (Atla)", self.skip_current_frame, "#B91C1C", 16)
        mkbtn("Yenile", self.refresh_list, "#15803D", 8)

        tk.Checkbutton(bar, text="Talon noktalari", variable=self.show_points,
                       command=self.render_canvas, bg="#1E2022", fg="white",
                       selectcolor="#1E2022", font=("Arial", 9),
                       activebackground="#1E2022").pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(bar, text="Otomatik model", variable=self.auto_model,
                       bg="#1E2022", fg="white", selectcolor="#1E2022",
                       font=("Arial", 9), activebackground="#1E2022").pack(side=tk.LEFT, padx=4)

        # Klavye kisayollari
        self.root.bind("<Right>", lambda e: self.next_frame())
        self.root.bind("<Left>", lambda e: self.prev_frame())
        self.root.bind("<Return>", lambda e: self.save_and_next())
        self.root.bind("<KP_Enter>", lambda e: self.save_and_next())

    # ==============================================================
    # VERI YUKLEME
    # ==============================================================
    def load_dataset_files(self):
        if not os.path.isdir(SOURCE_DIR):
            messagebox.showerror("Hata", f"Kaynak klasor bulunamadi:\n{SOURCE_DIR}")
            return
        files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".png")]
        # 'oncelik.txt' varsa o sirayi kullan (cesitli yaw/roll once etiketlensin); yoksa alfabetik
        order_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oncelik.txt")
        if os.path.exists(order_file):
            try:
                with open(order_file, encoding="utf-8") as of:
                    pref = [ln.strip() for ln in of if ln.strip()]
                present = set(files)
                ordered = [p for p in pref if p in present]
                seen = set(ordered)
                self.frames_list = ordered + sorted(p for p in files if p not in seen)
            except Exception:
                self.frames_list = sorted(files)
        else:
            self.frames_list = sorted(files)

        self.listbox.delete(0, tk.END)
        for f in self.frames_list:
            base = os.path.splitext(f)[0]
            self.listbox.insert(tk.END, f"{self._status_prefix(base)}{f}")

        if self.frames_list:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.load_frame(0)
        else:
            self.canvas.delete("all")
            self.canvas.create_text(40, 40, anchor=tk.NW, fill="#E5E7EB",
                                    font=("Arial", 12),
                                    text="dataset/ klasoru bos. Capture ile kare cektikten "
                                         "sonra 'Yenile'ye bas.")

    def _status_prefix(self, base):
        """Cikti klasorundeki .txt durumuna gore listede on-ek dondurur."""
        txt = os.path.join(OUTPUT_DIR, base + ".txt")
        if os.path.exists(txt):
            try:
                return "[✓] " if os.path.getsize(txt) > 0 else "[–] "
            except Exception:
                return "[✓] "
        return "    "

    def on_listbox_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self.load_frame(sel[0])

    def load_frame(self, index):
        if index < 0 or index >= len(self.frames_list):
            return
        self.current_idx = index
        filename = self.frames_list[index]
        base = os.path.splitext(filename)[0]
        img_path = os.path.join(SOURCE_DIR, filename)
        json_path = os.path.join(SOURCE_DIR, base + ".json")
        self.current_img_path = img_path

        # Zoom/pan sifirla
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_mode = None

        # Resmi yukle
        try:
            self.pil_img = Image.open(img_path).convert("RGB")
            self.img_w, self.img_h = self.pil_img.size
        except Exception as e:
            messagebox.showerror("Hata", f"Resim acilamadi: {filename}\n{e}")
            return

        # JSON'u SADECE keypoints_2d icin oku (SALT OKUNUR - dosyaya dokunulmaz)
        self.current_json_data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    self.current_json_data = json.load(jf)
            except Exception:
                self.current_json_data = {}

        # Kutuyu belirle (oncelik): .txt -> MODEL (otomatik) -> keypoint tohumu -> bos
        out_txt = os.path.join(OUTPUT_DIR, base + ".txt")
        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0:
            self.box = self.box_from_yolo_txt(out_txt)
            self.box_is_seed = False
        elif os.path.exists(out_txt):
            self.box = None  # bos .txt -> daha once 'atlandi'
            self.box_is_seed = False
        else:
            self.box = None
            if self.auto_model.get() and self.model is not None:
                self.box = self.detect_box_from_model()
            if self.box is None:
                self.box = self.seed_box_from_keypoints()
            self.box_is_seed = True

        self.render_canvas()

    # ==============================================================
    # KUTU TOHUMLAMA / DONUSUM
    # ==============================================================
    def seed_box_from_keypoints(self):
        """SADECE keypoints_2d'den (Talon konumu) baslangic kutusu. PADDING YOK."""
        kps = self.current_json_data.get("keypoints_2d", {})
        pts = []
        for p in kps.values():
            if not isinstance(p, dict):
                continue
            x = p.get("x", -1)
            y = p.get("y", -1)
            if x is None or y is None:
                continue
            if 0 <= x <= self.img_w and 0 <= y <= self.img_h:
                pts.append((x, y))
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        if x2 - x1 < 2:
            x2 = min(self.img_w, x1 + 2)
        if y2 - y1 < 2:
            y2 = min(self.img_h, y1 + 2)
        return [x1, y1, x2, y2]

    # ---------- MODEL (best.pt) entegrasyonu — opsiyonel ----------
    def _ensure_model(self):
        """YOLO modelini ilk ihtiyacta yukler. ultralytics/best.pt yoksa sessizce devre disi."""
        if self.model_loaded:
            return self.model is not None
        self.model_loaded = True
        if not MODEL_PATH:
            print("[NOT] Model yok (model/best.pt bulunamadi). Keypoint/elle devam.")
            return False
        try:
            from ultralytics import YOLO
            print(f"[BILGI] Model yukleniyor: {MODEL_PATH}")
            self.model = YOLO(MODEL_PATH)
        except Exception as e:
            print(f"[NOT] Model yuklenemedi (ultralytics kurulu mu?): {e}")
            self.model = None
        return self.model is not None

    def _start_model_load(self):
        """Modeli arka plan thread'inde yukle; bitince mevcut kareye uygula (GUI donmasin)."""
        import threading

        def worker():
            self._ensure_model()
            try:
                self.root.after(0, self._apply_model_to_current)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _apply_model_to_current(self):
        """Model hazir olunca: kare henuz etiketlenmemis ve kutuya dokunulmamissa model kutusunu ciz."""
        if not self.auto_model.get() or self.model is None or not self.frames_list:
            return
        if not self.box_is_seed:
            return  # .txt'ten geldi ya da kullanici dokundu -> dokunma
        base = os.path.splitext(self.frames_list[self.current_idx])[0]
        if os.path.exists(os.path.join(OUTPUT_DIR, base + ".txt")):
            return
        b = self.detect_box_from_model()
        if b is not None:
            self.box = b
            self.render_canvas()

    def detect_box_from_model(self):
        """best.pt ile mevcut resimde en yuksek guvenli kutu -> [x1,y1,x2,y2] veya None."""
        if not self._ensure_model() or not self.current_img_path:
            return None
        try:
            import numpy as np
            res = self.model.predict(source=self.current_img_path, conf=MODEL_CONF, verbose=False)
            boxes = res[0].boxes
            if boxes is None or len(boxes) == 0:
                return None
            confs = boxes.conf.cpu().numpy()
            i = int(np.argmax(confs))
            x1, y1, x2, y2 = boxes.xyxy.cpu().numpy()[i].tolist()
            x1 = min(max(x1, 0), self.img_w); x2 = min(max(x2, 0), self.img_w)
            y1 = min(max(y1, 0), self.img_h); y2 = min(max(y2, 0), self.img_h)
            if x2 - x1 < 2 or y2 - y1 < 2:
                return None
            return [x1, y1, x2, y2]
        except Exception as e:
            print(f"[NOT] Model tahmini basarisiz: {e}")
            return None

    def draw_from_model(self):
        """'Modelden Ciz' butonu: modeli calistir (gerekirse simdi yukle), kutuyu yenile."""
        self.root.config(cursor="watch")
        self.root.update()
        b = self.detect_box_from_model()
        self.root.config(cursor="")
        if b is None:
            messagebox.showinfo("Model", "Model kutu bulamadi (ya da model/ultralytics yok). Elle ciz.")
            return
        self.box = b
        self.box_is_seed = False
        self.render_canvas()

    def box_to_yolo_line(self, box):
        """[x1,y1,x2,y2] piksel -> YOLO 'class cx cy w h' (0-1 normalize)."""
        x1, y1, x2, y2 = box
        cx = ((x1 + x2) / 2.0) / self.img_w
        cy = ((y1 + y2) / 2.0) / self.img_h
        w = (x2 - x1) / self.img_w
        h = (y2 - y1) / self.img_h
        cx, cy, w, h = [min(1.0, max(0.0, v)) for v in (cx, cy, w, h)]
        return f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

    def box_from_yolo_txt(self, txt_path):
        """YOLO .txt ilk satirini geri okuyup piksel kutusuna cevirir (yeniden duzenleme icin)."""
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                line = f.readline().strip()
            parts = line.split()
            if len(parts) < 5:
                return None
            cx, cy, w, h = map(float, parts[1:5])
            bx1 = (cx - w / 2.0) * self.img_w
            by1 = (cy - h / 2.0) * self.img_h
            bx2 = (cx + w / 2.0) * self.img_w
            by2 = (cy + h / 2.0) * self.img_h
            return [bx1, by1, bx2, by2]
        except Exception:
            return None

    # ==============================================================
    # KAYDETME / ATLAMA / SIFIRLAMA
    # ==============================================================
    def save_current_frame(self):
        if self.box is None:
            messagebox.showwarning("Kutu yok", "Once bir kutu ciz/ayarla, sonra kaydet.")
            return False
        # Dogrula + resim sinirlarina clamp
        x1, y1, x2, y2 = self.box
        x1 = min(max(x1, 0), self.img_w)
        x2 = min(max(x2, 0), self.img_w)
        y1 = min(max(y1, 0), self.img_h)
        y2 = min(max(y2, 0), self.img_h)
        if x2 - x1 < 2 or y2 - y1 < 2:
            messagebox.showwarning("Gecersiz kutu", "Kutu cok kucuk (en az 2px).")
            return False
        self.box = [x1, y1, x2, y2]

        filename = self.frames_list[self.current_idx]
        base = os.path.splitext(filename)[0]
        src_png = os.path.join(SOURCE_DIR, filename)

        try:
            # png KOPYASI (orijinale dokunulmaz) + .txt cikti klasorune
            shutil.copy2(src_png, os.path.join(OUTPUT_DIR, filename))
            with open(os.path.join(OUTPUT_DIR, base + ".txt"), "w", encoding="utf-8") as f:
                f.write(self.box_to_yolo_line(self.box) + "\n")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydedilemedi:\n{e}")
            return False

        self._update_prefix(self.current_idx, "[✓] ")
        self.render_canvas()
        return True

    def save_and_next(self):
        """Enter: kaydet + dogrula; basariliysa otomatik sonraki kareye gec."""
        if self.save_current_frame():
            self.next_frame()

    def skip_current_frame(self):
        """Bu kareyi SIL: kaynak png+json (varsa cikti png+txt) -> Geri Donusum Kutusu.
        Geri alinabilir (FOF_ALLOWUNDO). Silince listeden cikar + sonraki kareye gecer."""
        if not self.frames_list:
            return
        idx = self.current_idx
        filename = self.frames_list[idx]
        base = os.path.splitext(filename)[0]
        # Kaynak ve (varsa) cikti kopyalarinin hepsi gitsin
        targets = [
            os.path.join(SOURCE_DIR, filename),        # kaynak png
            os.path.join(SOURCE_DIR, base + ".json"),  # kaynak json
            os.path.join(OUTPUT_DIR, filename),        # varsa cikti png kopyasi
            os.path.join(OUTPUT_DIR, base + ".txt"),   # varsa cikti txt
        ]
        if not _recycle(targets):
            messagebox.showerror("Hata", f"Geri Donusum Kutusu'na atilamadi:\n{filename}")
            return

        # Listeden ve hafizadan cikar
        self.box = None
        self.frames_list.pop(idx)
        self.listbox.delete(idx)

        # Hicbir kare kalmadiysa temizle
        if not self.frames_list:
            self.current_idx = -1
            self.current_img_path = None
            self.pil_img = None
            self.canvas.delete("all")
            self.canvas.create_text(40, 40, anchor=tk.NW, fill="#E5E7EB",
                                    font=("Arial", 12),
                                    text="Tum kareler silindi/bitti.")
            return

        # pop'tan sonra ayni indekste artik SONRAKI kare var -> onu ac
        new_idx = min(idx, len(self.frames_list) - 1)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(new_idx)
        self.listbox.see(new_idx)
        self.load_frame(new_idx)

    def reset_to_seed(self):
        """Kutuyu tekrar Talon konumundan (keypoints) tohumla."""
        self.box = self.seed_box_from_keypoints()
        if self.box is None:
            messagebox.showinfo("Bilgi", "Bu karede keypoints_2d yok. Elle ciz "
                                          "(bos alana tikla-surukle).")
        self.render_canvas()

    def clear_box(self):
        """Kutuyu temizle -> bos alana tikla-surukle ile sifirdan ciz."""
        self.box = None
        self.render_canvas()

    def refresh_list(self):
        """dataset/ klasorunu yeniden tara (yeni cekilen kareler gelsin)."""
        cur = self.frames_list[self.current_idx] if self.frames_list else None
        self.load_dataset_files()
        if cur and cur in self.frames_list:
            idx = self.frames_list.index(cur)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            self.load_frame(idx)

    def _update_prefix(self, idx, prefix):
        filename = self.frames_list[idx]
        self.listbox.delete(idx)
        self.listbox.insert(idx, f"{prefix}{filename}")
        self.listbox.selection_set(idx)

    # ==============================================================
    # NAVIGASYON
    # ==============================================================
    def prev_frame(self):
        if self.current_idx > 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_idx - 1)
            self.listbox.see(self.current_idx - 1)
            self.load_frame(self.current_idx - 1)

    def next_frame(self):
        if self.current_idx < len(self.frames_list) - 1:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_idx + 1)
            self.listbox.see(self.current_idx + 1)
            self.load_frame(self.current_idx + 1)

    # ==============================================================
    # ZOOM / PAN  (keypoint_editor.py'den birebir, kanitlanmis hassasiyet)
    # ==============================================================
    def on_mouse_wheel(self, event):
        step = 1.15
        old = self.zoom_factor
        if event.delta > 0:
            self.zoom_factor *= step
        else:
            self.zoom_factor = max(0.5, self.zoom_factor / step)
        self.zoom_factor = min(self.zoom_factor, 20.0)
        mult = self.zoom_factor / old
        self.pan_x = int(event.x - (event.x - self.pan_x) * mult)
        self.pan_y = int(event.y - (event.y - self.pan_y) * mult)
        self.render_canvas()

    def zoom_in(self):
        self.on_mouse_wheel(type("E", (), {"x": self.canvas.winfo_width() / 2,
                                           "y": self.canvas.winfo_height() / 2, "delta": 120})())

    def zoom_out(self):
        self.on_mouse_wheel(type("E", (), {"x": self.canvas.winfo_width() / 2,
                                           "y": self.canvas.winfo_height() / 2, "delta": -120})())

    def on_pan_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_pan_drag(self, event):
        self.pan_x += event.x - self.drag_start_x
        self.pan_y += event.y - self.drag_start_y
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.render_canvas()

    def update_image_size(self):
        if not self.pil_img:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10:
            cw = 1100
        if ch < 10:
            ch = 700
        iw, ih = self.pil_img.size
        base_scale = min(cw / iw, ch / ih)
        self.canvas_scale = base_scale * self.zoom_factor

        x1s = max(0, -self.pan_x)
        y1s = max(0, -self.pan_y)
        x2s = min(iw * self.canvas_scale, cw - self.pan_x)
        y2s = min(ih * self.canvas_scale, ch - self.pan_y)
        x1 = max(0.0, min(float(iw), x1s / self.canvas_scale))
        y1 = max(0.0, min(float(ih), y1s / self.canvas_scale))
        x2 = max(0.0, min(float(iw), x2s / self.canvas_scale))
        y2 = max(0.0, min(float(ih), y2s / self.canvas_scale))

        if x2 > x1 and y2 > y1:
            self.crop_x1, self.crop_y1 = int(x1), int(y1)
            self.crop_x2, self.crop_y2 = int(x2), int(y2)
            cropped = self.pil_img.crop((self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2))
            self.crop_w_scaled = max(1, int((x2 - x1) * self.canvas_scale))
            self.crop_h_scaled = max(1, int((y2 - y1) * self.canvas_scale))
            resized = cropped.resize((self.crop_w_scaled, self.crop_h_scaled),
                                     Image.Resampling.BILINEAR)
            self.tk_img = ImageTk.PhotoImage(resized)
            self.draw_img_x = int(self.pan_x + x1 * self.canvas_scale)
            self.draw_img_y = int(self.pan_y + y1 * self.canvas_scale)
        else:
            self.tk_img = None
            self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2 = 0, 0, 1, 1
            self.crop_w_scaled = self.crop_h_scaled = 1
            self.draw_img_x = self.draw_img_y = 0

    def canvas_to_image(self, cx, cy):
        if not getattr(self, "tk_img", None):
            return cx, cy
        rx = (cx - self.draw_img_x) / self.crop_w_scaled
        ry = (cy - self.draw_img_y) / self.crop_h_scaled
        mx = self.crop_x1 + rx * (self.crop_x2 - self.crop_x1)
        my = self.crop_y1 + ry * (self.crop_y2 - self.crop_y1)
        return mx, my

    def image_to_canvas(self, mx, my):
        if not getattr(self, "tk_img", None):
            return mx, my
        ow = self.crop_x2 - self.crop_x1
        oh = self.crop_y2 - self.crop_y1
        if ow == 0 or oh == 0:
            return mx, my
        rx = (mx - self.crop_x1) / ow
        ry = (my - self.crop_y1) / oh
        return self.draw_img_x + rx * self.crop_w_scaled, self.draw_img_y + ry * self.crop_h_scaled

    # ==============================================================
    # KUTU TUTAMAKLARI (hit-test + render)
    # ==============================================================
    def _corner_points_img(self):
        x1, y1, x2, y2 = self.box
        return {"TL": (x1, y1), "TR": (x2, y1), "BR": (x2, y2), "BL": (x1, y2)}

    def _edge_points_img(self):
        x1, y1, x2, y2 = self.box
        return {"T": ((x1 + x2) / 2, y1), "B": ((x1 + x2) / 2, y2),
                "L": (x1, (y1 + y2) / 2), "R": (x2, (y1 + y2) / 2)}

    def _all_handles_screen(self):
        out = {}
        for k, (mx, my) in {**self._corner_points_img(), **self._edge_points_img()}.items():
            out[k] = self.image_to_canvas(mx, my)
        return out

    def _point_in_box_screen(self, sx, sy):
        c1 = self.image_to_canvas(self.box[0], self.box[1])
        c2 = self.image_to_canvas(self.box[2], self.box[3])
        return (min(c1[0], c2[0]) <= sx <= max(c1[0], c2[0]) and
                min(c1[1], c2[1]) <= sy <= max(c1[1], c2[1]))

    def on_canvas_click(self, event):
        self.drag_mode = None
        if self.box is not None:
            # 1) Bir tutamaga yakin mi?
            best, grab = self.grab_radius, None
            for k, (sx, sy) in self._all_handles_screen().items():
                d = math.hypot(sx - event.x, sy - event.y)
                if d < best:
                    best, grab = d, k
            if grab:
                self.drag_mode = grab
                return
            # 2) Kutu icinde mi? -> tasi
            if self._point_in_box_screen(event.x, event.y):
                self.drag_mode = "MOVE"
                self.move_anchor_img = self.canvas_to_image(event.x, event.y)
                self.box_at_grab = list(self.box)
                return
            # 3) Kutu var ama disina tiklandi -> kazara yeniden cizimi onle (Temizle kullan)
            return
        # Kutu yok -> yeni kutu cizmeye basla
        mx, my = self.canvas_to_image(event.x, event.y)
        mx = min(max(mx, 0), self.img_w)
        my = min(max(my, 0), self.img_h)
        self.new_start = (mx, my)
        self.box = [mx, my, mx, my]
        self.drag_mode = "NEW"

    def on_canvas_drag(self, event):
        if not self.drag_mode or self.box is None:
            return
        self.box_is_seed = False  # kullanici kutuya elle dokundu
        mx, my = self.canvas_to_image(event.x, event.y)
        mx = min(max(mx, 0), self.img_w)
        my = min(max(my, 0), self.img_h)
        x1, y1, x2, y2 = self.box
        m = self.drag_mode

        if m == "NEW":
            sx, sy = self.new_start
            x1, x2 = min(sx, mx), max(sx, mx)
            y1, y2 = min(sy, my), max(sy, my)
        elif m == "MOVE":
            ax, ay = self.move_anchor_img
            dx, dy = mx - ax, my - ay
            ox1, oy1, ox2, oy2 = self.box_at_grab
            w, h = ox2 - ox1, oy2 - oy1
            nx1 = min(max(ox1 + dx, 0), self.img_w - w)
            ny1 = min(max(oy1 + dy, 0), self.img_h - h)
            x1, y1, x2, y2 = nx1, ny1, nx1 + w, ny1 + h
        else:
            # Kose / kenar
            if m in ("TL", "L", "BL"):
                x1 = mx
            if m in ("TR", "R", "BR"):
                x2 = mx
            if m in ("TL", "T", "TR"):
                y1 = my
            if m in ("BL", "B", "BR"):
                y2 = my
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)

        self.box = [x1, y1, x2, y2]
        self.render_canvas()

    def on_canvas_release(self, event):
        self.drag_mode = None

    # ==============================================================
    # CIZIM
    # ==============================================================
    def render_canvas(self):
        self.update_image_size()
        self.canvas.delete("all")
        if getattr(self, "tk_img", None):
            self.canvas.create_image(self.draw_img_x, self.draw_img_y,
                                     image=self.tk_img, anchor=tk.NW)
        if self.show_points.get():
            self._draw_seed_points()
        if self.box is not None:
            self._draw_box()
        self._draw_status()

    def _draw_seed_points(self):
        kps = self.current_json_data.get("keypoints_2d", {})
        for p in kps.values():
            if not isinstance(p, dict):
                continue
            x = p.get("x", -1)
            y = p.get("y", -1)
            if x is None or y is None:
                continue
            if 0 <= x <= self.img_w and 0 <= y <= self.img_h:
                sx, sy = self.image_to_canvas(x, y)
                self.canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3,
                                        fill=SEED_PT, outline="white")

    def _draw_box(self):
        c1 = self.image_to_canvas(self.box[0], self.box[1])
        c2 = self.image_to_canvas(self.box[2], self.box[3])
        self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1],
                                     outline=BOX_OUTLINE, width=2)
        # Kenar-ortasi tutamaklari (beyaz kare)
        for mx, my in self._edge_points_img().values():
            sx, sy = self.image_to_canvas(mx, my)
            r = self.handle_r - 3
            self.canvas.create_rectangle(sx - r, sy - r, sx + r, sy + r,
                                         fill=EDGE_HANDLE, outline="#222222")
        # Kose tutamaklari (renkli, beyaz halkali)
        for key, (mx, my) in self._corner_points_img().items():
            sx, sy = self.image_to_canvas(mx, my)
            r = self.handle_r
            self.canvas.create_oval(sx - r - 2, sy - r - 2, sx + r + 2, sy + r + 2,
                                    fill="white", outline="")
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                    fill=CORNER_COLORS[key], outline="")

    def _draw_status(self):
        w = self.canvas.winfo_width()
        self.canvas.create_rectangle(0, 0, w, 26, fill="#101418", outline="")
        if self.box is not None:
            x1, y1, x2, y2 = [round(v, 1) for v in self.box]
            txt = (f"Kutu px: ({x1},{y1})-({x2},{y2})   |   {self.img_w}x{self.img_h}   "
                   f"|   TXT: {self.box_to_yolo_line(self.box)}")
        else:
            txt = "Kutu yok — cizmek icin bos alana tikla-surukle (ya da 'Sifirla')"
        self.canvas.create_text(12, 13, anchor=tk.W, text=txt, fill="#E5E7EB",
                                font=("Consolas", 10))


if __name__ == "__main__":
    root = tk.Tk()
    app = BBoxEditor(root)
    root.update()
    app.render_canvas()
    root.mainloop()
