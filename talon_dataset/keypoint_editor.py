import os
import json
import math
import shutil
import zipfile
import datetime
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageDraw

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
WORKSPACE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR    = os.path.join(WORKSPACE_DIR, "dataset")
EDITED_DIR     = os.path.join(WORKSPACE_DIR, "dataset_edited")   # ← save target

# Image resolution (must match the game capture settings)
IMG_WIDTH  = 1920
IMG_HEIGHT = 1080

KEYPOINT_COLORS = {
    "nose":           "#1E64FA",  # Blue
    "left_wingtip":   "#FF1E1E",  # Red
    "right_wingtip":  "#FF64C8",  # Pink
    "tail":           "#FF7800",  # Orange
    "left_tail_fin":  "#FFD700",  # Yellow
    "right_tail_fin": "#00C850",  # Green
}

KEYPOINT_ORDER = ["nose", "left_wingtip", "right_wingtip",
                  "tail", "left_tail_fin", "right_tail_fin"]

# Drone scale factor (in-game)
DRONE_SCALE = 1.422

# Raw CAD offsets (UE centimetres, unscaled)
RAW_CAD_DATA = {
    "nose":           {"x":  69.13, "y":   0.19, "z":  -2.77},
    "left_wingtip":   {"x":   1.65, "y": -99.93, "z":   5.81},
    "right_wingtip":  {"x":   1.65, "y":  99.93, "z":   5.81},
    "tail":           {"x": -55.38, "y":   0.10, "z":   0.10},
    "left_tail_fin":  {"x": -43.17, "y": -28.25, "z":  16.98},
    "right_tail_fin": {"x": -43.17, "y":  28.25, "z":  16.98},
}

# Python + Lua target files for 3-D optimisation output
TARGET_FILES = {
    "draw_keypoints":     os.path.join(WORKSPACE_DIR, "draw_keypoints.py"),
    "capture_controller": os.path.join(WORKSPACE_DIR, "capture_controller.py"),
    "capture_controller_yeni": os.path.join(WORKSPACE_DIR, "capture_controller_yeni.py"),
    "special_capture":    os.path.join(WORKSPACE_DIR, "special_capture.py"),
    "main_lua":           os.path.join(WORKSPACE_DIR, "main.lua"),
    "game_lua":           os.path.join(WORKSPACE_DIR, "main_game.lua"),
}


# ──────────────────────────────────────────────────────────────────────────────
# MATH HELPERS  (identical logic to draw_keypoints.py)
# ──────────────────────────────────────────────────────────────────────────────
def get_unreal_matrix(pitch, yaw, roll):
    """Build Unreal-Engine rotation matrix (ZYX intrinsic, right-handed Y-up)."""
    SP, CP = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    SY, CY = math.sin(math.radians(yaw)),   math.cos(math.radians(yaw))
    SR, CR = math.sin(math.radians(roll)),  math.cos(math.radians(roll))
    r00 = CP * CY;  r10 = CP * SY;  r20 = SP
    r01 = SR*SP*CY - CR*SY;  r11 = SR*SP*SY + CR*CY;  r21 = -SR*CP
    r02 = -(CR*SP*CY + SR*SY); r12 = CY*SR - CR*SP*SY; r22 = CR*CP
    return [[r00, r01, r02],
            [r10, r11, r12],
            [r20, r21, r22]]


def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    R  = get_unreal_matrix(pitch, yaw, roll)
    rx = x*R[0][0] + y*R[0][1] + z*R[0][2]
    ry = x*R[1][0] + y*R[1][1] + z*R[1][2]
    rz = x*R[2][0] + y*R[2][1] + z*R[2][2]
    return rx, ry, rz


def project_world_to_screen(world_pt, cam_loc, cam_rot,
                             cam_fov=125.0, width=IMG_WIDTH, height=IMG_HEIGHT):
    """Project a 3-D world point to 2-D pixel coordinates."""
    vx = world_pt[0] - cam_loc["x"]
    vy = world_pt[1] - cam_loc["y"]
    vz = world_pt[2] - cam_loc["z"]

    R = get_unreal_matrix(cam_rot["pitch"], cam_rot["yaw"], cam_rot["roll"])

    # Camera-space: forward = R[0], right = R[1], up = R[2]
    x_local = vx*R[0][0] + vy*R[1][0] + vz*R[2][0]
    y_local = vx*R[0][1] + vy*R[1][1] + vz*R[2][1]
    z_local = vx*R[0][2] + vy*R[1][2] + vz*R[2][2]

    if x_local <= 0:
        return -1.0, -1.0

    focal_length = (width / 2.0) / math.tan(math.radians(cam_fov / 2.0))
    u = (width  / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    return u, v


def compute_keypoints_from_json(data):
    """
    Compute 2-D keypoints from JSON telemetry.
    Priority:
      1. keypoints_3d world coords  (most accurate – directly from game)
      2. drone_location + drone_rotation + CAD offsets  (fallback)
    Returns dict {name: {"x": float, "y": float}}
    """
    cam_loc = data.get("camera_location")
    cam_rot = data.get("camera_rotation")
    cam_fov = float(data.get("camera_fov", 125.0))   # ← use JSON value, NOT 90

    if not (cam_loc and cam_rot):
        return {}

    kps_3d  = data.get("keypoints_3d", {})
    kps_out = {}

    for name in KEYPOINT_ORDER:
        if name in kps_3d:
            # Use ground-truth 3-D world position directly
            wp = kps_3d[name]
            u, v = project_world_to_screen(
                (wp["x"], wp["y"], wp["z"]), cam_loc, cam_rot, cam_fov)
        else:
            # Fallback: rotate local CAD offset into world space
            drone_loc = data.get("drone_location")
            drone_rot = data.get("drone_rotation")
            if not (drone_loc and drone_rot):
                continue
            cad = RAW_CAD_DATA.get(name)
            if cad is None:
                continue
            lx = cad["x"] * DRONE_SCALE
            ly = cad["y"] * DRONE_SCALE
            lz = cad["z"] * DRONE_SCALE
            rx, ry, rz = rotate_vector_ue(
                lx, ly, lz,
                drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"])
            u, v = project_world_to_screen(
                (drone_loc["x"]+rx, drone_loc["y"]+ry, drone_loc["z"]+rz),
                cam_loc, cam_rot, cam_fov)

        kps_out[name] = {"x": u, "y": v}

    return kps_out


# ──────────────────────────────────────────────────────────────────────────────
# MAIN EDITOR CLASS
# ──────────────────────────────────────────────────────────────────────────────
class KeypointEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Talon UAV — Keypoint Validator & Refinement Tool")
        self.root.geometry("1400x900")
        self.root.state("zoomed")

        self.frames_list     = []
        self.current_idx     = 0
        self.current_image   = None
        self.current_json_data = {}
        self.canvas_scale    = 1.0

        self.keypoints_2d = {}   # {name: [x, y]}  in original 1920×1080 coords
        self.dragged_kp   = None
        self.edited_frames = set()
        self.zoom_factor  = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.dot_radius   = 6

        # Viewport crop state (set by update_image_size)
        self.crop_x1 = 0; self.crop_y1 = 0
        self.crop_x2 = 1; self.crop_y2 = 1
        self.crop_w_scaled = 1; self.crop_h_scaled = 1
        self.draw_img_x = 0; self.draw_img_y = 0
        self.tk_img  = None
        self.pil_img = None

        self.create_widgets()
        self.load_dataset_files()

    # ──────────────────────────────────────────────────────────────────────────
    # DATASET LOADING
    # ──────────────────────────────────────────────────────────────────────────
    def load_dataset_files(self):
        if not os.path.exists(DATASET_DIR):
            messagebox.showerror("Error", f"Dataset directory not found:\n{DATASET_DIR}")
            return

        files = sorted(f for f in os.listdir(DATASET_DIR) if f.endswith(".png"))
        self.frames_list = files

        self.listbox.delete(0, tk.END)
        for f in files:
            prefix = self._get_prefix(f)
            self.listbox.insert(tk.END, f"{prefix}{f}")

        if files:
            self.listbox.selection_set(0)
            self.load_frame(0)

    def _get_prefix(self, filename):
        base   = os.path.splitext(filename)[0]
        # Check in edited dir first, then source dir
        for d in (EDITED_DIR, DATASET_DIR):
            p = os.path.join(d, base + ".json")
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as jf:
                        if json.load(jf).get("manually_edited"):
                            return "[✓] "
                except Exception:
                    pass
        return "    "

    # ──────────────────────────────────────────────────────────────────────────
    # WIDGET CREATION
    # ──────────────────────────────────────────────────────────────────────────
    def create_widgets(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg="#2A2D32", pady=8)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame,
                 text="TALON UAV  ·  KEYPOINT VALIDATOR & MANUAL REFINEMENT",
                 font=("Arial", 15, "bold"), fg="white", bg="#2A2D32").pack()
        tk.Label(title_frame,
                 text="LMB+Drag → move keypoint  |  Double-LMB → toggle visibility  |"
                      "  RMB+Drag → pan  |  Scroll → zoom",
                 font=("Arial", 9), fg="#A0A5B0", bg="#2A2D32").pack()

        # ── Main pane ────────────────────────────────────────────────────────
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Left panel
        left_frame = tk.Frame(main_pane, bg="#1E2022", width=260)
        left_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="Screenshot List",
                 font=("Arial", 11, "bold"), fg="white",
                 bg="#1E2022", pady=5).pack()

        # Legend at bottom
        leg = tk.LabelFrame(left_frame, text="Keypoint Legend",
                            bg="#1E2022", fg="white",
                            font=("Arial", 9, "bold"), padx=5, pady=5)
        leg.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        for name, col in KEYPOINT_COLORS.items():
            row = tk.Frame(leg, bg="#1E2022", pady=1)
            row.pack(fill=tk.X)
            tk.Canvas(row, width=12, height=12,
                      bg=col, highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(row, text=f"  {name.replace('_',' ').title()}",
                     fg="white", bg="#1E2022", font=("Arial", 8)).pack(side=tk.LEFT)

        # Listbox
        self.listbox = tk.Listbox(left_frame, bg="#2D3035", fg="white",
                                  selectbackground="#1E64FA", font=("Arial", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        sb = tk.Scrollbar(self.listbox)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)
        sb.config(command=self.listbox.yview)

        main_pane.add(left_frame)

        # Right area
        right_area = tk.Frame(main_pane, bg="#252729")
        right_area.pack(fill=tk.BOTH, expand=True)
        main_pane.add(right_area)

        # Canvas
        self.canvas = tk.Canvas(right_area, bg="#18191B", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.canvas.bind("<ButtonPress-1>",    self.on_canvas_click)
        self.canvas.bind("<B1-Motion>",        self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>",  self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>",  self.on_canvas_double_click)
        self.canvas.bind("<MouseWheel>",       self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-3>",    self.on_pan_start)
        self.canvas.bind("<B3-Motion>",        self.on_pan_drag)

        # ── Bottom bar ────────────────────────────────────────────────────────
        bottom_frame = tk.Frame(right_area, bg="#1E2022", pady=8)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btn_row = tk.Frame(bottom_frame, bg="#1E2022")
        btn_row.pack(anchor=tk.CENTER)

        def btn(parent, text, color, cmd, w=None):
            kw = dict(bg=color, fg="white", font=("Arial", 10, "bold"),
                      command=cmd, relief=tk.FLAT, cursor="hand2", padx=6, pady=4)
            if w: kw["width"] = w
            b = tk.Button(parent, text=text, **kw)
            b.pack(side=tk.LEFT, padx=4, pady=4)
            return b

        btn(btn_row, "<< Previous",       "#3D4045", self.prev_frame, 11)
        btn(btn_row, "Next >>",           "#3D4045", self.next_frame, 11)
        btn(btn_row, "Zoom In",           "#3D4045", self.zoom_in,     8)
        btn(btn_row, "Zoom Out",          "#3D4045", self.zoom_out,    8)
        btn(btn_row, "✔ Save Frame",      "#1E64FA", self.save_current_frame, 14)
        btn(btn_row, "Reset to Auto",     "#E05020", self.reset_to_auto, 13)
        btn(btn_row, "📦 Export ZIP",     "#8B4FA0", self.export_zip,   13)
        btn(btn_row, "Run 3-D Optim.",    "#00C850", self.run_3d_optimization, 15)

        # Dot-size slider
        sf = tk.Frame(btn_row, bg="#1E2022")
        sf.pack(side=tk.LEFT, padx=10)
        tk.Label(sf, text="Dot Size:", fg="white", bg="#1E2022",
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        self.size_slider = tk.Scale(sf, from_=1, to=20, orient=tk.HORIZONTAL,
                                    bg="#1E2022", fg="white", highlightthickness=0,
                                    length=80, command=self.on_size_change)
        self.size_slider.set(6)
        self.size_slider.pack(side=tk.LEFT, padx=2)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(bottom_frame, textvariable=self.status_var,
                 fg="#A0A5B0", bg="#1E2022", font=("Arial", 9)).pack(pady=2)

    # ──────────────────────────────────────────────────────────────────────────
    # FRAME LOADING
    # ──────────────────────────────────────────────────────────────────────────
    def on_listbox_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self.load_frame(sel[0])

    def on_size_change(self, val):
        self.dot_radius = int(val)
        if self.pil_img:
            self.render_canvas()

    def load_frame(self, index):
        if index < 0 or index >= len(self.frames_list):
            return

        self.current_idx = index
        filename  = self.frames_list[index]
        base_name = os.path.splitext(filename)[0]

        img_path  = os.path.join(DATASET_DIR, filename)
        json_path = os.path.join(DATASET_DIR, base_name + ".json")
        # Also check edited dir for an already-saved version
        edited_json = os.path.join(EDITED_DIR, base_name + ".json")

        self.zoom_factor = 1.0
        self.pan_x = self.pan_y = 0
        self.pil_img = None

        # Load JSON: prefer edited copy if it has manually_edited flag
        src_json = json_path
        if os.path.exists(edited_json):
            try:
                with open(edited_json, "r", encoding="utf-8") as jf:
                    tmp = json.load(jf)
                if tmp.get("manually_edited"):
                    src_json = edited_json
            except Exception:
                pass

        try:
            with open(src_json, "r", encoding="utf-8") as jf:
                self.current_json_data = json.load(jf)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read JSON:\n{src_json}\n{e}")
            return

        is_manual = self.current_json_data.get("manually_edited", False)

        if is_manual:
            kps_raw = self.current_json_data.get("keypoints_2d", {})
            kps = {k.lower(): v for k, v in kps_raw.items()}
            saved_r = self.current_json_data.get("dot_radius", 6)
            self.dot_radius = saved_r
            self.size_slider.set(saved_r)
        else:
            kps_raw = self.current_json_data.get("keypoints_2d")
            if not kps_raw:
                kps_raw = compute_keypoints_from_json(self.current_json_data)
            kps = {k.lower(): v for k, v in kps_raw.items()}
            self.dot_radius = 6
            self.size_slider.set(6)

        # Normalise: accept both {x,y} dicts and [x,y] lists
        self.keypoints_2d = {}
        for name in KEYPOINT_ORDER:
            pt = kps.get(name, {"x": -1.0, "y": -1.0})
            if isinstance(pt, (list, tuple)):
                self.keypoints_2d[name] = [float(pt[0]), float(pt[1])]
            else:
                self.keypoints_2d[name] = [float(pt.get("x", -1.0)),
                                            float(pt.get("y", -1.0))]

        fov = self.current_json_data.get("camera_fov", 125.0)
        self.status_var.set(
            f"{filename}  |  FOV={fov}°  |  "
            f"{'[MANUALLY EDITED]' if is_manual else '[AUTO-PROJECTED]'}")

        self.pil_img = Image.open(img_path)
        self.render_canvas()

    def _default_keypoints(self):
        """Recompute auto-projected keypoints from current JSON."""
        kps_raw = self.current_json_data.get("keypoints_2d")
        if not kps_raw:
            kps_raw = compute_keypoints_from_json(self.current_json_data)
        return {k.lower(): v for k, v in kps_raw.items()}

    # ──────────────────────────────────────────────────────────────────────────
    # ZOOM / PAN
    # ──────────────────────────────────────────────────────────────────────────
    def on_pan_start(self, e):
        self.drag_start_x, self.drag_start_y = e.x, e.y

    def on_pan_drag(self, e):
        self.pan_x += e.x - self.drag_start_x
        self.pan_y += e.y - self.drag_start_y
        self.drag_start_x, self.drag_start_y = e.x, e.y
        self.render_canvas()

    def on_mouse_wheel(self, e):
        step = 1.15
        old  = self.zoom_factor
        if e.delta > 0:
            self.zoom_factor = min(15.0, self.zoom_factor * step)
        else:
            self.zoom_factor = max(0.5, self.zoom_factor / step)
        m = self.zoom_factor / old
        self.pan_x = int(e.x - (e.x - self.pan_x) * m)
        self.pan_y = int(e.y - (e.y - self.pan_y) * m)
        self.render_canvas()

    def zoom_in(self):
        class FE:
            def __init__(self, x, y, d): self.x=x; self.y=y; self.delta=d
        self.on_mouse_wheel(FE(self.canvas.winfo_width()//2,
                               self.canvas.winfo_height()//2, 120))

    def zoom_out(self):
        class FE:
            def __init__(self, x, y, d): self.x=x; self.y=y; self.delta=d
        self.on_mouse_wheel(FE(self.canvas.winfo_width()//2,
                               self.canvas.winfo_height()//2, -120))

    # ──────────────────────────────────────────────────────────────────────────
    # CANVAS RENDERING
    # ──────────────────────────────────────────────────────────────────────────
    def update_image_size(self):
        if not self.pil_img:
            return
        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        iw, ih = self.pil_img.size

        base_scale    = min(cw / iw, ch / ih)
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
            self.crop_w_scaled = max(1, int((x2 - x1) * self.canvas_scale))
            self.crop_h_scaled = max(1, int((y2 - y1) * self.canvas_scale))
            cropped = self.pil_img.crop((self.crop_x1, self.crop_y1,
                                         self.crop_x2, self.crop_y2))
            resized = cropped.resize((self.crop_w_scaled, self.crop_h_scaled),
                                     Image.Resampling.BILINEAR)
            self.tk_img = ImageTk.PhotoImage(resized)
            self.draw_img_x = int(self.pan_x + x1 * self.canvas_scale)
            self.draw_img_y = int(self.pan_y + y1 * self.canvas_scale)
        else:
            self.tk_img = None

    def canvas_to_image(self, cx, cy):
        if not self.tk_img:
            return cx, cy
        rx = (cx - self.draw_img_x) / self.crop_w_scaled
        ry = (cy - self.draw_img_y) / self.crop_h_scaled
        ow = self.crop_x2 - self.crop_x1
        oh = self.crop_y2 - self.crop_y1
        return self.crop_x1 + rx * ow, self.crop_y1 + ry * oh

    def image_to_canvas(self, mx, my):
        if not self.tk_img:
            return mx, my
        ow = self.crop_x2 - self.crop_x1
        oh = self.crop_y2 - self.crop_y1
        if ow == 0 or oh == 0:
            return mx, my
        rx = (mx - self.crop_x1) / ow
        ry = (my - self.crop_y1) / oh
        return self.draw_img_x + rx * self.crop_w_scaled, \
               self.draw_img_y + ry * self.crop_h_scaled

    def render_canvas(self):
        self.update_image_size()
        self.canvas.delete("all")

        if self.tk_img:
            self.canvas.create_image(self.draw_img_x, self.draw_img_y,
                                     image=self.tk_img, anchor=tk.NW)
        self._draw_skeleton()
        self._draw_keypoints()

    def _draw_skeleton(self):
        pairs = [("nose", "left_wingtip"), ("nose", "right_wingtip"),
                 ("left_wingtip", "tail"), ("right_wingtip", "tail"),
                 ("tail", "left_tail_fin"), ("tail", "right_tail_fin")]
        for p1, p2 in pairs:
            pt1 = self.keypoints_2d.get(p1)
            pt2 = self.keypoints_2d.get(p2)
            if pt1 and pt2 and pt1[0] >= 0 and pt2[0] >= 0:
                cx1, cy1 = self.image_to_canvas(pt1[0], pt1[1])
                cx2, cy2 = self.image_to_canvas(pt2[0], pt2[1])
                self.canvas.create_line(cx1, cy1, cx2, cy2,
                                        fill="#606060", width=1.5, tags="line")

    def _draw_keypoints(self):
        def_kps = None
        for name, pt in self.keypoints_2d.items():
            color = KEYPOINT_COLORS[name]
            if pt[0] >= 0:
                cx, cy = self.image_to_canvas(pt[0], pt[1])
                ro = self.dot_radius + (1 if self.dot_radius > 1 else 0)
                ri = self.dot_radius
                if ro > ri:
                    self.canvas.create_oval(cx-ro, cy-ro, cx+ro, cy+ro,
                                            fill="white", outline="", tags=f"kp_{name}")
                self.canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                                        fill=color, outline="", tags=f"kp_{name}")
            else:
                # Show ghost at default position
                if def_kps is None:
                    def_kps = self._default_keypoints()
                dp = def_kps.get(name, {"x": -1.0, "y": -1.0})
                dpx = dp["x"] if isinstance(dp, dict) else dp[0]
                dpy = dp["y"] if isinstance(dp, dict) else dp[1]
                if dpx >= 0:
                    cx, cy = self.image_to_canvas(dpx, dpy)
                    ro = self.dot_radius + 4
                    ri = max(2, self.dot_radius // 2)
                    self.canvas.create_oval(cx-ro, cy-ro, cx+ro, cy+ro,
                                            fill="", outline="#FF3030",
                                            width=1.5, dash=(4,4),
                                            tags=f"kp_{name}")
                    self.canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                                            fill="#FF3030", outline="",
                                            tags=f"kp_{name}")

    # ──────────────────────────────────────────────────────────────────────────
    # MOUSE INTERACTIONS
    # ──────────────────────────────────────────────────────────────────────────
    def _find_nearest_kp(self, ex, ey, threshold=22.0):
        best_d, best_name = threshold, None
        for name, pt in self.keypoints_2d.items():
            if pt[0] >= 0:
                cx, cy = self.image_to_canvas(pt[0], pt[1])
            else:
                # Ghost location
                def_kps = self._default_keypoints()
                dp = def_kps.get(name, {"x": -1.0, "y": -1.0})
                dpx = dp["x"] if isinstance(dp, dict) else dp[0]
                dpy = dp["y"] if isinstance(dp, dict) else dp[1]
                if dpx < 0:
                    continue
                cx, cy = self.image_to_canvas(dpx, dpy)
            d = math.hypot(cx - ex, cy - ey)
            if d < best_d:
                best_d, best_name = d, name
        return best_name

    def on_canvas_click(self, e):
        self.dragged_kp = None
        # Only drag active (visible) keypoints
        best_d, best_name = 22.0, None
        for name, pt in self.keypoints_2d.items():
            if pt[0] < 0:
                continue
            cx, cy = self.image_to_canvas(pt[0], pt[1])
            d = math.hypot(cx - e.x, cy - e.y)
            if d < best_d:
                best_d, best_name = d, name
        self.dragged_kp = best_name

    def on_canvas_drag(self, e):
        if self.dragged_kp:
            mx, my = self.canvas_to_image(e.x, e.y)
            mx = max(0.0, min(float(IMG_WIDTH),  mx))
            my = max(0.0, min(float(IMG_HEIGHT), my))
            self.keypoints_2d[self.dragged_kp] = [mx, my]
            self.render_canvas()

    def on_canvas_release(self, e):
        self.dragged_kp = None

    def on_canvas_double_click(self, e):
        clicked = self._find_nearest_kp(e.x, e.y)
        if not clicked:
            return
        pt = self.keypoints_2d[clicked]
        if pt[0] >= 0:
            self.keypoints_2d[clicked] = [-1.0, -1.0]
        else:
            # Restore to default projected position
            def_kps = self._default_keypoints()
            dp = def_kps.get(clicked, {"x": -1.0, "y": -1.0})
            dpx = dp["x"] if isinstance(dp, dict) else dp[0]
            dpy = dp["y"] if isinstance(dp, dict) else dp[1]
            self.keypoints_2d[clicked] = [dpx, dpy]
        self.render_canvas()

    # ──────────────────────────────────────────────────────────────────────────
    # SAVE
    # ──────────────────────────────────────────────────────────────────────────
    def save_current_frame(self):
        filename  = self.frames_list[self.current_idx]
        base_name = os.path.splitext(filename)[0]

        # Build keypoints_2d dict (rounded integers)
        kps_dict = {}
        for name, pt in self.keypoints_2d.items():
            kps_dict[name] = {"x": round(pt[0]), "y": round(pt[1])}

        # Update JSON data in memory
        data = dict(self.current_json_data)
        data["keypoints_2d"]  = kps_dict
        data["manually_edited"] = True
        data["dot_radius"]    = self.dot_radius
        data["edited_at"]     = datetime.datetime.now().isoformat(timespec="seconds")

        # Ensure edited dir exists
        os.makedirs(EDITED_DIR, exist_ok=True)

        # ── Write JSON to EDITED dir ──────────────────────────────────────────
        out_json = os.path.join(EDITED_DIR, base_name + ".json")
        try:
            with open(out_json, "w", encoding="utf-8") as jf:
                json.dump(data, jf, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write JSON:\n{e}")
            return

        # ── Write TXT summary alongside JSON ─────────────────────────────────
        out_txt = os.path.join(EDITED_DIR, base_name + ".txt")
        self._write_txt(out_txt, filename, data, kps_dict)

        # ── Copy PNG to EDITED dir ────────────────────────────────────────────
        src_png = os.path.join(DATASET_DIR, filename)
        dst_png = os.path.join(EDITED_DIR, filename)
        if not os.path.exists(dst_png):
            shutil.copy2(src_png, dst_png)

        # ── Also update the source JSON (so auto-projection sees manual flag) ─
        src_json = os.path.join(DATASET_DIR, base_name + ".json")
        try:
            with open(src_json, "w", encoding="utf-8") as jf:
                json.dump(data, jf, indent=4, ensure_ascii=False)
        except Exception:
            pass  # Not critical

        self.edited_frames.add(filename)
        self.current_json_data = data

        # Update listbox
        self.listbox.delete(self.current_idx)
        self.listbox.insert(self.current_idx, f"[✓] {filename}")
        self.listbox.selection_set(self.current_idx)
        self.status_var.set(f"✔ Saved → {out_json}")

        messagebox.showinfo("Saved",
            f"Frame saved to dataset_edited/\n\n"
            f"  JSON : {base_name}.json\n"
            f"  TXT  : {base_name}.txt\n"
            f"  PNG  : {filename}")

    def _write_txt(self, path, filename, data, kps_dict):
        """Write a human-readable text summary of the saved frame."""
        cam_fov = data.get("camera_fov", 125.0)
        edited_at = data.get("edited_at", "?")
        lines = [
            "=" * 60,
            f"TALON UAV KEYPOINT ANNOTATION",
            f"File     : {filename}",
            f"Saved at : {edited_at}",
            f"Camera FOV: {cam_fov}°",
            f"Image size: {IMG_WIDTH} x {IMG_HEIGHT}",
            "=" * 60,
            "",
            "KEYPOINTS 2D (pixel coordinates, origin top-left):",
            "-" * 40,
        ]
        for name in KEYPOINT_ORDER:
            pt = kps_dict.get(name, {"x": -1, "y": -1})
            vis = "VISIBLE" if pt["x"] >= 0 else "OCCLUDED"
            lines.append(f"  {name:<20} x={pt['x']:>6}  y={pt['y']:>6}  [{vis}]")

        lines += ["", "KEYPOINTS 3D (world coordinates, UE cm):"]
        lines += ["-" * 40]
        kps3d = data.get("keypoints_3d", {})
        for name in KEYPOINT_ORDER:
            if name in kps3d:
                w = kps3d[name]
                lines.append(
                    f"  {name:<20} x={w['x']:>12.2f}  y={w['y']:>12.2f}  z={w['z']:>12.2f}")

        lines += ["", "CAMERA:"]
        lines += ["-" * 40]
        cl = data.get("camera_location", {})
        cr = data.get("camera_rotation", {})
        lines.append(f"  Location : x={cl.get('x',0):.2f}  y={cl.get('y',0):.2f}  z={cl.get('z',0):.2f}")
        lines.append(f"  Rotation : pitch={cr.get('pitch',0):.2f}  yaw={cr.get('yaw',0):.2f}  roll={cr.get('roll',0):.2f}")
        lines.append(f"  FOV      : {cam_fov}°")
        lines += ["", "DRONE:"]
        lines += ["-" * 40]
        dl = data.get("drone_location", {})
        dr = data.get("drone_rotation", {})
        lines.append(f"  Location : x={dl.get('x',0):.2f}  y={dl.get('y',0):.2f}  z={dl.get('z',0):.2f}")
        lines.append(f"  Rotation : pitch={dr.get('pitch',0):.2f}  yaw={dr.get('yaw',0):.2f}  roll={dr.get('roll',0):.2f}")
        lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # ──────────────────────────────────────────────────────────────────────────
    # RESET
    # ──────────────────────────────────────────────────────────────────────────
    def reset_to_auto(self):
        filename  = self.frames_list[self.current_idx]
        base_name = os.path.splitext(filename)[0]

        if "manually_edited" in self.current_json_data:
            del self.current_json_data["manually_edited"]

        kps = compute_keypoints_from_json(self.current_json_data)
        self.current_json_data["keypoints_2d"] = kps

        json_path = os.path.join(DATASET_DIR, base_name + ".json")
        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(self.current_json_data, jf, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write JSON:\n{e}")
            return

        if filename in self.edited_frames:
            self.edited_frames.discard(filename)

        self.listbox.delete(self.current_idx)
        self.listbox.insert(self.current_idx, f"    {filename}")
        self.listbox.selection_set(self.current_idx)
        messagebox.showinfo("Reset", "Frame reset to auto-projection.")
        self.load_frame(self.current_idx)

    # ──────────────────────────────────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────────────────────────────────
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

    # ──────────────────────────────────────────────────────────────────────────
    # ZIP EXPORT
    # ──────────────────────────────────────────────────────────────────────────
    def export_zip(self):
        if not os.path.exists(EDITED_DIR):
            messagebox.showwarning("No Edited Frames",
                "No edited frames found in dataset_edited/.\n"
                "Save at least one frame first.")
            return

        files = [f for f in os.listdir(EDITED_DIR)
                 if f.endswith((".json", ".png", ".txt"))]
        if not files:
            messagebox.showwarning("Empty", "dataset_edited/ contains no files.")
            return

        ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(WORKSPACE_DIR, f"talon_edited_export_{ts}.zip")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(files):
                    zf.write(os.path.join(EDITED_DIR, f),
                             arcname=os.path.join("dataset_edited", f))

            n = len([f for f in files if f.endswith(".json")])
            messagebox.showinfo("ZIP Created",
                f"Exported {n} annotated frames.\n\nZIP: {zip_path}")
            self.status_var.set(f"ZIP exported → {os.path.basename(zip_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"ZIP creation failed:\n{e}")

    # ──────────────────────────────────────────────────────────────────────────
    # 3-D OPTIMISATION
    # ──────────────────────────────────────────────────────────────────────────
    def run_3d_optimization(self):
        edited_files = []
        for fname in sorted(os.listdir(DATASET_DIR)):
            if not fname.endswith(".json"):
                continue
            jpath = os.path.join(DATASET_DIR, fname)
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("manually_edited"):
                    edited_files.append((fname, d))
            except Exception:
                pass

        if len(edited_files) < 2:
            messagebox.showwarning(
                "Not Enough Frames",
                f"Need ≥ 2 manually-edited frames. Found: {len(edited_files)}")
            return

        print(f"[3D-OPT] Running over {len(edited_files)} frames …")

        # ── Loss functions ───────────────────────────────────────────────────
        def loss_single(p, keyname, files):
            x, y, z = p
            tot, n = 0.0, 0
            for _, data in files:
                kps = data.get("keypoints_2d", {})
                if keyname not in kps:
                    continue
                t = kps[keyname]
                tx = t["x"] if isinstance(t, dict) else t[0]
                ty = t["y"] if isinstance(t, dict) else t[1]
                if tx < 0 or ty < 0:
                    continue
                dl = data["drone_location"]
                dr = data["drone_rotation"]
                cl = data["camera_location"]
                cr = data["camera_rotation"]
                fov = float(data.get("camera_fov", 125.0))
                rx, ry, rz = rotate_vector_ue(x, y, z,
                                               dr["pitch"], dr["yaw"], dr["roll"])
                u, v = project_world_to_screen(
                    (dl["x"]+rx, dl["y"]+ry, dl["z"]+rz), cl, cr, fov)
                tot += (u - tx)**2 + (v - ty)**2
                n   += 1
            return tot if n > 0 else 999999.0

        def loss_symm(p, left_key, right_key, files):
            x, y, z = p
            tot, n = 0.0, 0
            for _, data in files:
                dl = data["drone_location"]
                dr = data["drone_rotation"]
                cl = data["camera_location"]
                cr = data["camera_rotation"]
                fov = float(data.get("camera_fov", 125.0))
                kps = data.get("keypoints_2d", {})
                for key, sign in ((left_key, -1), (right_key, 1)):
                    if key not in kps:
                        continue
                    t = kps[key]
                    tx = t["x"] if isinstance(t, dict) else t[0]
                    ty = t["y"] if isinstance(t, dict) else t[1]
                    if tx < 0 or ty < 0:
                        continue
                    rx, ry, rz = rotate_vector_ue(x, sign*y, z,
                                                   dr["pitch"], dr["yaw"], dr["roll"])
                    u, v = project_world_to_screen(
                        (dl["x"]+rx, dl["y"]+ry, dl["z"]+rz), cl, cr, fov)
                    tot += (u - tx)**2 + (v - ty)**2
                    n   += 1
            return tot if n > 0 else 999999.0

        def optimise(func, start, args=(),
                     steps=(10.0, 5.0, 1.0, 0.1, 0.01, 0.001)):
            best = list(start)
            bl   = func(best, *args)
            for step in steps:
                improved = True
                while improved:
                    improved = False
                    for i in range(len(best)):
                        for d in (-step, step):
                            tp = list(best); tp[i] += d
                            l  = func(tp, *args)
                            if l < bl:
                                bl, best, improved = l, tp, True
            return best, bl

        # ── Run optimisation ─────────────────────────────────────────────────
        results = {}

        res_n, _ = optimise(
            lambda p, k, f: loss_single([p[0], 0.19, -2.77], k, f),
            [69.13], args=("nose", edited_files))
        results["nose"] = {"x": round(res_n[0], 3), "y": 0.19, "z": -2.77}

        res_t, _ = optimise(
            lambda p, k, f: loss_single([p[0], 0.10, 0.10], k, f),
            [-55.38], args=("tail", edited_files))
        results["tail"] = {"x": round(res_t[0], 3), "y": 0.10, "z": 0.10}

        res_w, _ = optimise(loss_symm, [1.65, 99.93, 5.81],
                            args=("left_wingtip", "right_wingtip", edited_files))
        results["left_wingtip"]  = {"x": round(res_w[0],3),
                                    "y": round(-res_w[1],3),
                                    "z": round(res_w[2],3)}
        results["right_wingtip"] = {"x": round(res_w[0],3),
                                    "y": round(res_w[1],3),
                                    "z": round(res_w[2],3)}

        res_f, _ = optimise(loss_symm, [-43.17, 28.25, 16.98],
                            args=("left_tail_fin", "right_tail_fin", edited_files))
        results["left_tail_fin"]  = {"x": round(res_f[0],3),
                                     "y": round(-res_f[1],3),
                                     "z": round(res_f[2],3)}
        results["right_tail_fin"] = {"x": round(res_f[0],3),
                                     "y": round(res_f[1],3),
                                     "z": round(res_f[2],3)}

        self._update_python_files(results)
        self._update_lua_files(results)

        summary = "\n".join(
            f"  {k:<20}: x={v['x']:.3f}  y={v['y']:.3f}  z={v['z']:.3f}"
            for k, v in results.items())
        messagebox.showinfo("3-D Optimisation Complete",
            f"Optimised using {len(edited_files)} frames.\n\n"
            f"KEYPOINTS_LOCAL (scaled UE cm):\n{summary}\n\n"
            f"Updated: draw_keypoints.py, capture_controller.py, special_capture.py, main.lua")
        self.load_frame(self.current_idx)

    # ── File updaters ─────────────────────────────────────────────────────────
    @staticmethod
    def _find_matching_brace(content, start):
        count = 0
        for i in range(start, len(content)):
            if content[i] == '{': count += 1
            elif content[i] == '}':
                count -= 1
                if count == 0:
                    return i
        return -1

    def _update_python_files(self, r):
        block = (
            f'KEYPOINTS_LOCAL = {{\n'
            f'    "nose":           {{"x": {r["nose"]["x"]:.3f}, "y": {r["nose"]["y"]:.3f}, "z": {r["nose"]["z"]:.3f}}},\n'
            f'    "left_wingtip":   {{"x": {r["left_wingtip"]["x"]:.3f}, "y": {r["left_wingtip"]["y"]:.3f}, "z": {r["left_wingtip"]["z"]:.3f}}},\n'
            f'    "right_wingtip":  {{"x": {r["right_wingtip"]["x"]:.3f}, "y": {r["right_wingtip"]["y"]:.3f}, "z": {r["right_wingtip"]["z"]:.3f}}},\n'
            f'    "tail":           {{"x": {r["tail"]["x"]:.3f}, "y": {r["tail"]["y"]:.3f}, "z": {r["tail"]["z"]:.3f}}},\n'
            f'    "left_tail_fin":  {{"x": {r["left_tail_fin"]["x"]:.3f}, "y": {r["left_tail_fin"]["y"]:.3f}, "z": {r["left_tail_fin"]["z"]:.3f}}},\n'
            f'    "right_tail_fin": {{"x": {r["right_tail_fin"]["x"]:.3f}, "y": {r["right_tail_fin"]["y"]:.3f}, "z": {r["right_tail_fin"]["z"]:.3f}}}\n'
            f'}}'
        )
        for key in ("draw_keypoints", "capture_controller", "capture_controller_yeni", "special_capture"):
            fp = TARGET_FILES.get(key)
            if fp and os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                idx = content.find("KEYPOINTS_LOCAL = {")
                if idx != -1:
                    bi  = idx + len("KEYPOINTS_LOCAL = ")
                    end = self._find_matching_brace(content, bi)
                    if end != -1:
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(content[:idx] + block + content[end+1:])
                        print(f"[3D-OPT] Updated {fp}")

    def _update_lua_files(self, r):
        sc = 0.86   # UE → game scale factor
        def us(v): return round(v / sc, 2)
        block = (
            f'local KEYPOINTS_LOCAL = {{\n'
            f'    Nose          = {{X = {us(r["nose"]["x"]):.2f}, Y = {us(r["nose"]["y"]):.2f}, Z = {us(r["nose"]["z"]):.2f}}},\n'
            f'    Left_Wingtip  = {{X = {us(r["left_wingtip"]["x"]):.2f}, Y = {us(-r["left_wingtip"]["y"]):.2f}, Z = {us(r["left_wingtip"]["z"]):.2f}}},\n'
            f'    Right_Wingtip = {{X = {us(r["right_wingtip"]["x"]):.2f}, Y = {us(-r["right_wingtip"]["y"]):.2f}, Z = {us(r["right_wingtip"]["z"]):.2f}}},\n'
            f'    Tail          = {{X = {us(r["tail"]["x"]):.2f}, Y = {us(r["tail"]["y"]):.2f}, Z = {us(r["tail"]["z"]):.2f}}},\n'
            f'    Left_Tail_Fin = {{X = {us(r["left_tail_fin"]["x"]):.2f}, Y = {us(-r["left_tail_fin"]["y"]):.2f}, Z = {us(r["left_tail_fin"]["z"]):.2f}}},\n'
            f'    Right_Tail_Fin= {{X = {us(r["right_tail_fin"]["x"]):.2f}, Y = {us(-r["right_tail_fin"]["y"]):.2f}, Z = {us(r["right_tail_fin"]["z"]):.2f}}}\n'
            f'}}'
        )
        for key in ("main_lua", "game_lua"):
            fp = TARGET_FILES.get(key)
            if fp and os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                idx = content.find("local KEYPOINTS_LOCAL = {")
                if idx != -1:
                    bi  = idx + len("local KEYPOINTS_LOCAL = ")
                    end = self._find_matching_brace(content, bi)
                    if end != -1:
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(content[:idx] + block + content[end+1:])
                        print(f"[3D-OPT] Updated Lua {fp}")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = KeypointEditor(root)
    root.update()
    app.render_canvas()
    root.mainloop()
