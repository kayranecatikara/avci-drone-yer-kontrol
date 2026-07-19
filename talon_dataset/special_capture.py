import os
import time
import json
import ctypes
from ctypes import wintypes
import shutil
import glob
import math
from PIL import ImageGrab, Image, ImageDraw

# ============================================================================
# CONFIGURATION & PATHS
# ============================================================================
WORKSPACE_DIR = r"c:\Users\Zeylo\Desktop\talon_dataset"
GAME_MOD_SCRIPTS = r"C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64\ue4ss\Mods\TalonDatasetGenerator\Scripts"
GAME_MOD_LUA = os.path.join(GAME_MOD_SCRIPTS, "main.lua")
GAME_MOD_BACKUP = os.path.join(GAME_MOD_SCRIPTS, "main_backup_temp.lua")

STATUS_FILE = os.path.join(WORKSPACE_DIR, "status.txt")
SPECIAL_DATASET_DIR = os.path.join(WORKSPACE_DIR, "dataset_special")
SPECIAL_ANNOTATED_DIR = os.path.join(WORKSPACE_DIR, "dataset_special_annotated")

# Perfectly symmetric coordinates centered around (0,0,0) scaled once by 0.86
KEYPOINTS_LOCAL = {
    "nose":             {"x": 49.476, "y": 0.0, "z": 0.0},       # Nose-tip FPV Camera
    "left_wingtip":     {"x": -0.074, "y": 74.737, "z": 3.716},    # Left Wingtip
    "right_wingtip":    {"x": -0.074, "y": -74.737, "z": 3.716},   # Right Wingtip
    "tail":             {"x": -42.801, "y": 0.0, "z": 0.0},      # Rear Motor Shaft / Propeller Hub
    "left_tail_fin":    {"x": -28.011, "y": -19.411, "z": 8.164}, # Left V-Tail Tip
    "right_tail_fin":   {"x": -28.011, "y": 19.411, "z": 8.164}  # Right V-Tail Tip
},       # Nose-tip FPV Camera
    "left_wingtip":     {"x": 5.134, "y": 152.901, "z": 14.375},    # Left Wingtip
    "right_wingtip":    {"x": 5.134, "y": -152.901, "z": 14.375},   # Right Wingtip
    "tail":             {"x": -86.815, "y": 0.140, "z": 0.140},      # Rear Motor Shaft / Propeller Hub
    "left_tail_fin":    {"x": -70.587, "y": 45.093, "z": 28.404}, # Left V-Tail Tip
    "right_tail_fin":   {"x": -70.587, "y": -45.093, "z": 28.404}  # Right V-Tail Tip
}

KEYPOINT_COLORS = {
    "nose":             (30, 100, 250),   # Blue
    "left_wingtip":     (255, 30, 30),    # Red
    "right_wingtip":    (255, 100, 200),  # Pink
    "tail":             (255, 120, 0),    # Orange
    "left_tail_fin":    (255, 215, 0),    # Yellow
    "right_tail_fin":   (0, 200, 80)      # Green
}

# ============================================================================
# LUA SPECIAL CODE (Temporary script to capture 9 specific views)
# ============================================================================
LUA_SPECIAL_CONTENT = """-- ============================================================================
-- Special Temporary Mod Script for Back, Right, and Top Views (3m to 8m)
-- ============================================================================
print("[TalonSpecial] Loading temporary view capture script...")

local CAPTURES_PER_SPOT = 3 -- 3 distances per angle
local STATUS_FILE_PATH = "c:\\\\Users\\\\Zeylo\\\\Desktop\\\\talon_dataset\\\\status.txt"
local TICK_INTERVAL_MS = 250

local state = "INIT"
local talonActor = nil
local anchorLocation = nil
local originalCamActor = nil
local originalCamLocation = nil
local originalSpringArmLength = nil
local originalViewTarget = nil
local frameIndex = 1
local lastTalonSearchTime = 0
local visualsRestored = false

-- Hardcoded 9 specific combinations (3m, 5.5m, 8m) for Back, Right, and Top
local specialCombos = {
    -- 1. Tam Arkadan (Back Views: cyaw = 180)
    { dist = 300, cpitch = 0.0, cyaw = 180.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "arkadan_3m" },
    { dist = 550, cpitch = 0.0, cyaw = 180.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "arkadan_5.5m" },
    { dist = 800, cpitch = 0.0, cyaw = 180.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "arkadan_8m" },
    -- 2. Tam Sağdan (Right Views: cyaw = 270)
    { dist = 300, cpitch = 0.0, cyaw = 270.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "sagdan_3m" },
    { dist = 550, cpitch = 0.0, cyaw = 270.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "sagdan_5.5m" },
    { dist = 800, cpitch = 0.0, cyaw = 270.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "sagdan_8m" },
    -- 3. Tam Tepeden (Top Views: cpitch = 89.9)
    { dist = 300, cpitch = 89.9, cyaw = 0.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "tepeden_3m" },
    { dist = 550, cpitch = 89.9, cyaw = 0.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "tepeden_5.5m" },
    { dist = 800, cpitch = 89.9, cyaw = 0.0, rollTilt = 0.0, droll = 0.0, dpitch = 0.0, dyaw = 0.0, name = "tepeden_8m" },
}

local function CalculateLookAtRotation(startPos, targetPos)
    local dx = targetPos.X - startPos.X
    local dy = targetPos.Y - startPos.Y
    local dz = targetPos.Z - startPos.Z
    local dist2D = math.sqrt(dx * dx + dy * dy)
    local yaw = math.deg(math.atan(dy, dx))
    local pitch = math.deg(math.atan(dz, dist2D))
    if yaw > 180 then yaw = yaw - 360 elseif yaw < -180 then yaw = yaw + 360 end
    if pitch > 180 then pitch = pitch - 360 elseif pitch < -180 then pitch = pitch + 360 end
    return { Pitch = pitch, Yaw = yaw, Roll = 0.0 }
end

local function RunConsoleCmd(cmd)
    pcall(function() ExecuteConsoleCommand(cmd) end)
end

local function GetActiveController()
    local PC = FindFirstOf("DebugCameraController")
    if not PC or not PC:IsValid() then
        PC = FindFirstOf("PlayerController")
    end
    return PC
end

local function GetCameraActor(PC)
    local debugPawn = FindFirstOf("DebugCameraPawn")
    if debugPawn and debugPawn:IsValid() then return debugPawn end
    local viewTarget = PC:GetViewTarget()
    if viewTarget and viewTarget:IsValid() then return viewTarget end
    return nil
end

local function RestoreCameraActor(PC)
    pcall(function()
        if originalViewTarget and originalViewTarget:IsValid() then
            PC:SetViewTarget(originalViewTarget)
        end
    end)
    originalViewTarget = nil
    originalCamActor = nil
end

local function SetCameraTransform(x, y, z, pitch, yaw, roll)
    pcall(function()
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            PC.ControlRotation = { Pitch = pitch, Yaw = yaw, Roll = roll }
            local CamPawn = PC.Pawn or FindFirstOf("DebugCameraPawn")
            if CamPawn and CamPawn:IsValid() then
                CamPawn:K2_SetActorLocation({ X = x, Y = y, Z = z }, false, {}, true)
                CamPawn:K2_SetActorRotation({ Pitch = pitch, Yaw = yaw, Roll = roll }, true)
            end
        end
    end)
end

local function HideAllWidgets()
    pcall(function()
        local Controllers = FindAllOf("PlayerController")
        if Controllers then
            for i = 1, #Controllers do
                local c = Controllers[i]
                if c and c:IsValid() and c.MyHUD and c.MyHUD:IsValid() then
                    c.MyHUD.bShowHUD = false
                end
            end
        end
        local Widgets = FindAllOf("UserWidget")
        if Widgets then
            for i = 1, #Widgets do
                local w = Widgets[i]
                if w and w:IsValid() then
                    w:SetRenderOpacity(0.0)
                    w:SetVisibility(3)
                end
            end
        end
    end)
end

local function ConfigureCleanVisuals()
    RunConsoleCmd("ShowFlag.HUD 0")
    RunConsoleCmd("ShowFlag.LUI 0")
    RunConsoleCmd("ShowFlag.Slate 0")
    RunConsoleCmd("ShowFlag.WidgetComponents 0")
    HideAllWidgets()
end

local function RestoreVisuals()
    pcall(function()
        RunConsoleCmd("ShowFlag.HUD 1")
        RunConsoleCmd("ShowFlag.LUI 1")
        RunConsoleCmd("ShowFlag.Slate 1")
        RunConsoleCmd("ShowFlag.WidgetComponents 1")
        local Widgets = FindAllOf("UserWidget")
        if Widgets then
            for i = 1, #Widgets do
                local w = Widgets[i]
                if w and w:IsValid() then
                    w:SetRenderOpacity(1.0)
                    w:SetVisibility(0)
                end
            end
        end
    end)
end

local function WriteStatus(statusText)
    local file = io.open(STATUS_FILE_PATH, "w")
    if file then
        file:write(statusText)
        file:close()
    end
end

local function ReadStatus()
    local file = io.open(STATUS_FILE_PATH, "r")
    if file then
        local content = file:read("*all")
        file:close()
        return content:gsub("%s+", "")
    end
    return nil
end

local function ProcessStateMachine()
    if state == "INIT" then
        WriteStatus("OFFLINE")
        state = "WAITING_FOR_DRONE"
        print("[TalonSpecial] Searching for drone...")
        
    elseif state == "WAITING_FOR_DRONE" then
        local status = ReadStatus()
        if status == "WAITING_START" then
            visualsRestored = false
            local found = FindFirstOf("BPP_AIDroneTalon_C")
            if found and found:IsValid() then
                talonActor = found
                anchorLocation = found:K2_GetActorLocation()
                print("[TalonSpecial] Found drone! Snipping coordinates...")
                state = "FREEZE_AND_PREPARE"
            end
        end
        
    elseif state == "FREEZE_AND_PREPARE" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            return
        end
        
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            originalViewTarget = PC:GetViewTarget()
            originalCamActor = GetCameraActor(PC)
        end
        
        talonActor.CustomTimeDilation = 0.0
        ConfigureCleanVisuals()
        state = "APPLY_TRANSFORM"
        
    elseif state == "APPLY_TRANSFORM" then
        if frameIndex > #specialCombos then
            -- We are fully done! Signal finished!
            print("[TalonSpecial] Captured all 9 views successfully!")
            WriteStatus("FINISHED")
            state = "CLEANUP"
            return
        end
        
        local combo = specialCombos[frameIndex]
        print(string.format("[TalonSpecial] Applying view #%d: %s", frameIndex, combo.name))
        
        -- Lock drone perfectly flat
        pcall(function()
            talonActor:K2_SetActorRotation({ Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }, true)
            talonActor:K2_SetActorLocation(anchorLocation, false, {}, true)
        end)
        
        -- Compute Camera spherical coordinates centered on the Drone
        local radPitch = math.rad(combo.cpitch)
        local radYaw = math.rad(combo.cyaw)
        
        local dx = combo.dist * math.cos(radPitch) * math.cos(radYaw)
        local dy = combo.dist * math.cos(radPitch) * math.sin(radYaw)
        local dz = combo.dist * math.sin(radPitch)
        
        local camX = anchorLocation.X + dx
        local camY = anchorLocation.Y + dy
        local camZ = anchorLocation.Z + dz
        
        local lookRot = CalculateLookAtRotation({ X = camX, Y = camY, Z = camZ }, anchorLocation)
        lookRot.Roll = combo.rollTilt
        
        SetCameraTransform(camX, camY, camZ, lookRot.Pitch, lookRot.Yaw, lookRot.Roll)
        
        if originalCamActor and originalCamActor:IsValid() then
            pcall(function() 
                originalCamActor:K2_SetActorLocation({ X = camX, Y = camY, Z = camZ }, false, {}, true) 
                originalCamActor:K2_SetActorRotation({ Pitch = lookRot.Pitch, Yaw = lookRot.Yaw, Roll = lookRot.Roll }, true) 
            end)
        end
        
        -- Prepare json packet
        local readySignal = string.format([[{"status":"READY","index":%d,"view_name":"%s","drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":0,"yaw":0,"roll":0},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":90}]],
            frameIndex,
            combo.name,
            anchorLocation.X, anchorLocation.Y, anchorLocation.Z,
            camX, camY, camZ,
            lookRot.Pitch, lookRot.Yaw, lookRot.Roll
        )
        
        WriteStatus(readySignal)
        state = "WAITING_FOR_CAPTURE"
        
    elseif state == "WAITING_FOR_CAPTURE" then
        local status = ReadStatus()
        local expectedResponse = "DONE_" .. tostring(frameIndex)
        if status == expectedResponse then
            frameIndex = frameIndex + 1
            state = "APPLY_TRANSFORM"
        end
        
    elseif state == "CLEANUP" then
        if not visualsRestored then
            talonActor.CustomTimeDilation = 1.0
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                RestoreCameraActor(PC)
            end
            RestoreVisuals()
            visualsRestored = true
            print("[TalonSpecial] Restored normal game state.")
        end
    end
end

LoopAsync(TICK_INTERVAL_MS, ProcessStateMachine)
"""

# ============================================================================
# MATH PROJECTION FUNCTIONS
# ============================================================================
def rotate_vector_ue(x, y, z, pitch, yaw, roll):
    # Native Unreal Engine FRotator::RotateVector implementation
    rad_pitch = math.radians(pitch)
    rad_yaw = math.radians(yaw)
    rad_roll = math.radians(roll)
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    # AxisX (Forward)
    r00 = CP * CY
    r10 = CP * SY
    r20 = SP
    
    # AxisY (Right)
    r01 = SR * SP * CY - CR * SY
    r11 = SR * SP * SY + CR * CY
    r21 = -SR * CP
    
    # AxisZ (Up)
    r02 = CR * SP * CY + SR * SY
    r12 = CR * SP * SY - SR * CY
    r22 = CR * CP
    
    rx = x * r00 + y * r01 + z * r02
    ry = x * r10 + y * r11 + z * r12
    rz = x * r20 + y * r21 + z * r22
    return rx, ry, rz

def project_world_to_screen(world_pt, cam_loc, cam_rot, fov=90.0, width=1920, height=1080):
    vx = world_pt[0] - cam_loc['x']
    vy = world_pt[1] - cam_loc['y']
    vz = world_pt[2] - cam_loc['z']
    
    rad_pitch = math.radians(cam_rot['pitch'])
    rad_yaw = math.radians(-cam_rot['yaw'])
    rad_roll = math.radians(cam_rot['roll'])
    
    SP = math.sin(rad_pitch)
    CP = math.cos(rad_pitch)
    SY = math.sin(rad_yaw)
    CY = math.cos(rad_yaw)
    SR = math.sin(rad_roll)
    CR = math.cos(rad_roll)
    
    r00 = CP * CY
    r01 = -CP * SY
    r02 = SP
    
    r10 = SR * SP * CY + CR * SY
    r11 = -SR * SP * SY + CR * CY
    r12 = -SR * CP
    
    r20 = -CR * SP * CY + SR * SY
    r21 = CR * SP * SY + SR * CY
    r22 = CR * CP
    
    x_local = vx * r00 + vy * r01 + vz * r02
    y_local = vx * r10 + vy * r11 + vz * r12
    z_local = vx * r20 + vy * r21 + vz * r22
    
    if x_local <= 0:
        return -1.0, -1.0
        
    focal_length = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = (width / 2.0) + (y_local / x_local) * focal_length
    v = (height / 2.0) - (z_local / x_local) * focal_length
    return u, v

def calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov=90.0):
    kps_2d = {}
    for name, offset in KEYPOINTS_LOCAL.items():
        rx, ry, rz = rotate_vector_ue(
            offset["x"], offset["y"], offset["z"],
            drone_rot["pitch"], drone_rot["yaw"], drone_rot["roll"]
        )
        world_pt = (
            drone_loc["x"] + rx,
            drone_loc["y"] + ry,
            drone_loc["z"] + rz
        )
        u, v = project_world_to_screen(world_pt, cam_loc, cam_rot, fov=cam_fov)
        kps_2d[name] = {"x": u, "y": v}
    return kps_2d

# ============================================================================
# SCREENSHOT CAPTURE UTILS (WIN32 DPI AWARE)
# ============================================================================
user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_window_rect(hwnd):
    if user32.IsIconic(hwnd):
        return 0, 0, 0, 0
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if user32.IsZoomed(hwnd) or (rect.left <= 0 and rect.top <= 0 and rect.right >= user32.GetSystemMetrics(0) - 15):
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return 0, 0, w, h
    
    # Standard windowed mode client area capture
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    pt_topleft = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_topleft))
    pt_bottomright = POINT(client_rect.right, client_rect.bottom)
    user32.ClientToScreen(hwnd, ctypes.byref(pt_bottomright))
    return pt_topleft.x, pt_topleft.y, pt_bottomright.x, pt_bottomright.y

def find_game_window():
    titles = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_windows_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "DronesOfWar" in title or "Drones of War" in title or "Unreal" in title:
                    titles.append((hwnd, title))
        return True
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return titles

# ============================================================================
# MAIN AUTOMATED SPECIAL PIPELINE
# ============================================================================
def main():
    print("=== AUTOMATED SPECIAL CAPTURE PIPELINE ===")
    
    # 1. Verify and Backup mod script
    if not os.path.exists(GAME_MOD_LUA):
        print(f"[ERROR] Could not find game mod at: {GAME_MOD_LUA}")
        return
        
    print("[INFO] Creating temporary backup of game mod main.lua...")
    shutil.copy(GAME_MOD_LUA, GAME_MOD_BACKUP)
    
    try:
        # 2. Write special temporary main.lua into game folder
        print("[INFO] Overwriting game mod with temporary special lua script...")
        with open(GAME_MOD_LUA, "w", encoding="utf-8") as f:
            f.write(LUA_SPECIAL_CONTENT)
            
        print("[SUCCESS] Temporary mod script installed!")
        
        # 3. Locate active game window
        windows = find_game_window()
        if not windows:
            print("[ERROR] Drones of War window not found! Please start the game first.")
            return
            
        hwnd, title = windows[0]
        print(f"[INFO] Hooking game window: '{title}' (HWND: {hwnd})")
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        time.sleep(1.0)
        
        # 4. Clean folders
        if os.path.exists(SPECIAL_DATASET_DIR):
            shutil.rmtree(SPECIAL_DATASET_DIR)
        os.makedirs(SPECIAL_DATASET_DIR, exist_ok=True)
        
        if os.path.exists(SPECIAL_ANNOTATED_DIR):
            shutil.rmtree(SPECIAL_ANNOTATED_DIR)
        os.makedirs(SPECIAL_ANNOTATED_DIR, exist_ok=True)
        
        # 5. Handshake loop
        print("[INFO] Starting handshake loop. Waiting for UE4SS script...")
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            f.write("WAITING_START")
            
        last_processed = -1
        
        while True:
            if not os.path.exists(STATUS_FILE):
                time.sleep(0.1)
                continue
                
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except IOError:
                time.sleep(0.05)
                continue
                
            if content.startswith("{") and content.endswith("}"):
                try:
                    data = json.loads(content)
                except Exception:
                    time.sleep(0.05)
                    continue
                    
                if data.get("status") == "READY":
                    index = data.get("index", -1)
                    view_name = data.get("view_name", f"view_{index}")
                    
                    if index != last_processed:
                        print(f"📸 [CAPTURE] Processing view {index}: {view_name}... ", end="", flush=True)
                        time.sleep(0.1)
                        
                        rect = get_window_rect(hwnd)
                        left, top, right, bottom = rect
                        
                        if right > left and bottom > top:
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                            try:
                                resample_filter = Image.Resampling.LANCZOS
                            except AttributeError:
                                resample_filter = Image.LANCZOS
                            img = img.resize((1920, 1080), resample_filter)
                            
                            # Save png & json
                            filename = f"talon_{view_name}.png"
                            img_path = os.path.join(SPECIAL_DATASET_DIR, filename)
                            img.save(img_path, "PNG")
                            
                            drone_loc = data.get("drone_location")
                            drone_rot = data.get("drone_rotation")
                            cam_loc = data.get("camera_location")
                            cam_rot = data.get("camera_rotation")
                            cam_fov = data.get("camera_fov", 90.0)
                            
                            keypoints_2d = calculate_keypoints_2d(drone_loc, drone_rot, cam_loc, cam_rot, cam_fov)
                            
                            metadata = {
                                "drone_location": drone_loc,
                                "drone_rotation": drone_rot,
                                "camera_location": cam_loc,
                                "camera_rotation": cam_rot,
                                "camera_fov": cam_fov,
                                "keypoints_2d": keypoints_2d
                            }
                            
                            json_filename = f"talon_{view_name}.json"
                            json_path = os.path.join(SPECIAL_DATASET_DIR, json_filename)
                            with open(json_path, "w", encoding="utf-8") as jf:
                                json.dump(metadata, jf, indent=4)
                                
                            # 6. Render skeleton on the fly for verification!
                            img_ann = Image.open(img_path)
                            draw_ann = ImageDraw.Draw(img_ann)
                            
                            projected_points = {}
                            for kp_name, coords in keypoints_2d.items():
                                px = coords.get("x", -1)
                                py = coords.get("y", -1)
                                if px >= 0 and py >= 0 and px <= 1920 and py <= 1080:
                                    projected_points[kp_name] = (int(round(px)), int(round(py)))
                                    
                            def draw_line_safe(pt1_name, pt2_name, color=(128, 128, 128), width=3):
                                if pt1_name in projected_points and pt2_name in projected_points:
                                    draw_ann.line([projected_points[pt1_name], projected_points[pt2_name]], fill=color, width=width)
                                    
                            draw_line_safe("nose", "left_wingtip")
                            draw_line_safe("nose", "right_wingtip")
                            draw_line_safe("left_wingtip", "tail")
                            draw_line_safe("right_wingtip", "tail")
                            draw_line_safe("tail", "left_tail_fin")
                            draw_line_safe("tail", "right_tail_fin")
                            
                            for kp_name, coord in projected_points.items():
                                px, py = coord
                                color = KEYPOINT_COLORS[kp_name]
                                draw_ann.ellipse([px - 6, py - 6, px + 6, py + 6], fill=color, outline=(255, 255, 255), width=2)
                                
                            out_ann_path = os.path.join(SPECIAL_ANNOTATED_DIR, filename)
                            img_ann.save(out_ann_path)
                            
                            print("Saved Raw PNG/JSON & Beautifully Annotated Visual!")
                            last_processed = index
                            
                            # Signal UE mod to move to next combo
                            with open(STATUS_FILE, "w", encoding="utf-8") as out_f:
                                out_f.write(f"DONE_{index}")
                        else:
                            print("[ERROR] Window minimized or invalid size. Retrying...")
                            time.sleep(0.5)
                            
            elif content == "FINISHED":
                print("\n🎉 [SUCCESS] Finished capturing and drawing all 9 special views!")
                break
                
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("[INFO] Special capture stopped by user.")
    finally:
        # 7. ALWAYS RESTORE THE ORIGINAL LUA SCRIPT!
        if os.path.exists(GAME_MOD_BACKUP):
            print("\n[INFO] Restoring original game mod main.lua...")
            shutil.copy(GAME_MOD_BACKUP, GAME_MOD_LUA)
            os.remove(GAME_MOD_BACKUP)
            print("[SUCCESS] Original game mod main.lua successfully restored!")
            
    print(f"\n=== PROCESS COMPLETE ===")
    print(f"📁 9 Special views (Raw PNG/JSON) saved in: {SPECIAL_DATASET_DIR}")
    print(f"📁 9 Special views (Annotated skeleton) saved in: {SPECIAL_ANNOTATED_DIR}")
    print("You can open these folders and inspect the perfect Y and Z alignment abiciğim!")

if __name__ == "__main__":
    main()
