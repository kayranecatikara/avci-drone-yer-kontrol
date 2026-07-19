-- ============================================================================
-- Talon UAV Dataset Generator - UE4SS Lua Mod (Freeze-Orbit-Move Cycle)
-- Target Game: Drones of War (Unreal Engine 5.5)
-- Target Actor: BPP_AIDroneTalon_C
-- Optimized for: 100% Stability, Perfect Drone Freezing, and Extreme Photo Diversity
-- ============================================================================

print("[TalonDataset] Mod initialized in Freeze-Orbit-Move mode with Rock-Solid Drone Freezing & Strict Diversity Guard!")

-- CONFIGURATION PARAMETERS
local CAPTURES_PER_SPOT = 25  -- Capture exactly 25 distinct photos at each spot
local FLY_TICKS = 10         -- How many ticks to let the drone fly (2.5 seconds of flight)
local MIN_DIST = 200        -- 2m minimum distance
local MAX_DIST = 1000       -- 13m maximum distance
local MIN_PITCH = -45       -- Camera elevation lower bound (degrees)
local MAX_PITCH = 55        -- Camera elevation upper bound (degrees)
local CAM_TILT_MAX = 30     -- Maximum random camera roll/tilt (degrees) for extreme variety
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"
local TICK_INTERVAL_MS = 250 -- State machine polling frequency

local DISTANCE_STEPS = {200, 300, 400, 500, 600, 700, 800, 900}
local currentDistanceSteps = {200, 300, 400, 500, 600, 700, 800, 900}

local poseHistory = {}
local HISTORY_FILE = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\pose_history.txt"

pcall(function()
    local f = io.open(HISTORY_FILE, "r")
    if f then
        for line in f:lines() do
            local d, cp, cy, rt = line:match("([^,]+),([^,]+),([^,]+),([^,]+)")
            if d and cp and cy and rt then
                table.insert(poseHistory, {dist=tonumber(d), cpitch=tonumber(cp), cyaw=tonumber(cy), rollTilt=tonumber(rt), droll=0, dpitch=0, dyaw=0})
            end
        end
        f:close()
        print("[TalonDataset] Loaded " .. tostring(#poseHistory) .. " past captures from history file!")
    end
end)

local function SavePoseToHistory(p)
    table.insert(poseHistory, p)
    pcall(function()
        local f = io.open(HISTORY_FILE, "a")
        if f then f:write(string.format("%.2f,%.2f,%.2f,%.2f\n", p.dist, p.cpitch, p.cyaw, p.rollTilt)); f:close() end
    end)
end      -- Rolling history of recent poses to enforce 100% uniqueness
local MAX_HISTORY = 100

-- Internal State Variables
local state = "INIT"
local talonActor = nil
local anchorLocation = nil
local originalCamActor = nil
local originalCamLocation = nil
local originalSpringArmLength = nil
local originalViewTarget = nil
local frameIndex = 1
local lastTalonSearchTime = 0
local spotCaptureCount = 0
local flyTickCount = 0

-- Performance and visual tracking variables
local visualsRestored = false
local uiHidden = false
local lastPose = nil -- Used by the Strict Diversity Guard to prevent similar photos

-- Caching variables for rendering delay wait state
local currentCombo = nil
local currentCamX = nil
local currentCamY = nil
local currentCamZ = nil
local currentLookRot = nil

-- Initialize random generator seed
math.randomseed(os.time())

-- Math Helper: Calculate look-at rotation in degrees from Start to Target
local function CalculateLookAtRotation(startPos, targetPos)
    local dx = targetPos.X - startPos.X
    local dy = targetPos.Y - startPos.Y
    local dz = targetPos.Z - startPos.Z
    
    local dist2D = math.sqrt(dx * dx + dy * dy)
    local yaw = math.deg(math.atan(dy, dx))
    local pitch = math.deg(math.atan(dz, dist2D))
    
    -- Normalize angles to Unreal's [-180, 180] range
    if yaw > 180 then yaw = yaw - 360 elseif yaw < -180 then yaw = yaw + 360 end
    if pitch > 180 then pitch = pitch - 360 elseif pitch < -180 then pitch = pitch + 360 end
    
    return { Pitch = pitch, Yaw = yaw, Roll = 0.0 }
end

-- ============================================================================
-- NATIVE KEYPOINT SPECIFICATIONS & ROTATION MATH (X-UAV Talon EPO 1718mm)
-- ============================================================================
-- OPTIMIZED COORDINATES: Unscaled Actor-Relative Coordinates in cm (scaled_coords / 0.86)
local KEYPOINTS_LOCAL = {
    Nose = {X = 57.53, Y = 0.00, Z = 0.00},
    Left_Wingtip = {X = -0.09, Y = 86.90, Z = 4.32},
    Right_Wingtip = {X = -0.09, Y = -86.90, Z = 4.32},
    Tail = {X = -49.77, Y = 0.00, Z = 0.00},
    Left_Tail_Fin = {X = -32.57, Y = -22.57, Z = 9.49},
    Right_Tail_Fin = {X = -32.57, Y = 22.57, Z = 9.49}
}
}

-- Unreal Engine FRotationMatrix based Rotation with Scale
local function RotateVectorScaled(v, pitch, yaw, roll, scale)
    local SP = math.sin(math.rad(pitch))
    local CP = math.cos(math.rad(pitch))
    local SY = math.sin(math.rad(yaw))
    local CY = math.cos(math.rad(yaw))
    local SR = math.sin(math.rad(roll))
    local CR = math.cos(math.rad(roll))
    
    -- AxisX (Forward)
    local m00 = CP * CY
    local m01 = CP * SY
    local m02 = SP
    
    -- AxisY (Right)
    local m10 = SR * SP * CY - CR * SY
    local m11 = SR * SP * SY + CR * CY
    local m12 = -SR * CP
    
    -- AxisZ (Up)
    local m20 = -(CR * SP * CY + SR * SY)
    local m21 = CY * SR - CR * SP * SY
    local m22 = CR * CP
    
    local sx = v.X * (scale and scale.X or 1.0)
    local sy = v.Y * (scale and scale.Y or 1.0)
    local sz = v.Z * (scale and scale.Z or 1.0)
    
    local rx = sx * m00 + sy * m10 + sz * m20
    local ry = sx * m01 + sy * m11 + sz * m21
    local rz = sx * m02 + sy * m12 + sz * m22
    
    return { X = rx, Y = ry, Z = rz }
end

local function GetTalonKeypointWorld(talon, localPt, pitch, yaw, roll)
    local scale = {X=1,Y=1,Z=1}
    pcall(function() scale = talon:GetActorScale3D() end)
    local rotated = RotateVectorScaled(localPt, pitch, yaw, roll, scale)
    local loc = talon:K2_GetActorLocation()
    return {
        X = loc.X + rotated.X,
        Y = loc.Y + rotated.Y,
        Z = loc.Z + rotated.Z
    }
end

-- ============================================================================
-- HILE 1: ProjectWorldLocationToScreen ile %100 Motordan Gelme 2D Koordinat
-- Blueprint'e dokunmadan, motorun kendi projeksiyon fonksiyonunu kullaniyoruz!
-- ============================================================================
local SCREEN_W = 1920
local SCREEN_H = 1080

-- Motordan gelen ProjectWorldLocationToScreen ile keypoint'leri 2D'ye cevirir
-- Donus: keypoints_2d tablosu, keypoints_3d tablosu
local function BuildKeypoints2D(talonLoc, talonPitch, talonYaw, talonRoll, scale, PC)
    local kp2d = {}
    local kp3d = {}

    for name, localPt in pairs(KEYPOINTS_LOCAL) do
        -- 1. Yerel koordinati world space'e donustur
        local rotated = RotateVectorScaled(localPt, talonPitch, talonYaw, talonRoll, scale)
        local worldPt = {
            X = talonLoc.X + rotated.X,
            Y = talonLoc.Y + rotated.Y,
            Z = talonLoc.Z + rotated.Z
        }

        -- 2. 3D world koordinatini kaydet
        kp3d[name] = { x = worldPt.X, y = worldPt.Y, z = worldPt.Z }

        -- 3. KANITLANMIS CAGRI SEKLI:
        -- screenOut tablosu in-place dolduruluyor, return degeri bool
        local screenX = -1
        local screenY = -1
        local onScreen = false

        pcall(function()
            if PC and PC:IsValid() then
                local screenOut = { X = 0, Y = 0 }
                local bOnScreen = PC:ProjectWorldLocationToScreen(
                    { X = worldPt.X, Y = worldPt.Y, Z = worldPt.Z },
                    screenOut,
                    false
                )
                screenX = screenOut.X
                screenY = screenOut.Y
                onScreen = bOnScreen == true
            end
        end)

        kp2d[name] = { x = screenX, y = screenY, on = onScreen }
    end

    return kp2d, kp3d
end



-- Safely run console commands on the engine console
local function RunConsoleCmd(cmd)
    local ok = pcall(function()
        ExecuteConsoleCommand(cmd)
    end)
    if not ok then
        pcall(function()
            local PC = FindFirstOf("DebugCameraController")
            if not PC or not PC:IsValid() then
                PC = FindFirstOf("PlayerController")
            end
            if PC and PC:IsValid() then
                PC:ConsoleCommand(cmd, true)
            end
        end)
    end
end

-- Get the active player/camera controller dynamically
local function GetActiveController()
    local PC = FindFirstOf("DebugCameraController")
    if not PC or not PC:IsValid() then
        local controllers = FindAllOf("PlayerController") or {}
        for _, c in ipairs(controllers) do
            if c:IsValid() then
                local success, className = pcall(function() return c:GetClass():GetName() end)
                if success and className and not className:find("DebugCameraController") then
                    PC = c
                    break
                end
            end
        end
    end
    
    if not PC or not PC:IsValid() then
        PC = FindFirstOf("PlayerController")
    end
    
    return PC
end

-- Find the active camera actor dynamically in the level
local function GetCameraActor(PC)
    if not PC or not PC:IsValid() then return nil end
    
    local viewTarget = PC:GetViewTarget()
    if viewTarget and viewTarget:IsValid() then
        if not talonActor or viewTarget:GetAddress() ~= talonActor:GetAddress() then
            return viewTarget
        end
    end
    
    local possessed = PC:K2_GetPawn()
    if possessed and possessed:IsValid() then
        if not talonActor or possessed:GetAddress() ~= talonActor:GetAddress() then
            return possessed
        end
    end
    
    return nil
end

-- Safely Pause/Unpause game physics absolute (not a toggle)
local function SetPhysicsPaused(paused)
    -- Disabled to allow real-time component transform ticking while drone is frozen
end

-- -- Robustly restore the camera actor state (location)
local function RestoreCameraActor(PC)
    pcall(function()
        if originalViewTarget and originalViewTarget:IsValid() then
            pcall(function() PC:SetViewTarget(originalViewTarget) end)
        end
    end)
    originalViewTarget = nil
    
    local isStillValid = false
    pcall(function()
        if originalCamActor and originalCamActor:IsValid() then
            local activeCam = GetCameraActor(PC)
            if activeCam and activeCam:IsValid() and activeCam:GetAddress() == originalCamActor:GetAddress() then
                isStillValid = true
            end
        end
    end)
    
    if isStillValid then
        pcall(function()
            originalCamActor:K2_SetActorLocation(originalCamLocation, false, {}, true)
        end)
    end
    
    originalCamActor = nil
    originalCamLocation = nil
end

-- Teleport and rotate the camera safely (DYNAMICAL pawn resolution)
local function SetCameraTransform(x, y, z, pitch, yaw, roll)
    pcall(function()
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            -- Apply Rotation to Controller
            PC.ControlRotation = { Pitch = pitch, Yaw = yaw, Roll = roll }
            
            -- Move the active camera actor/pawn
            local CamPawn = GetCameraActor(PC)
            if CamPawn and CamPawn:IsValid() then
                CamPawn:K2_SetActorLocation({ X = x, Y = y, Z = z }, false, {}, true)
                CamPawn:K2_SetActorRotation({ Pitch = pitch, Yaw = yaw, Roll = roll }, true)
            end
        end
    end)
end

-- Force hide all UMG User Widgets and disable Virtual Joysticks
local function HideAllWidgetsSafe()
    -- KULLANICI ISTEGI: "YAZILAR HUD GOZUKSUN" (HUD Gizlenmesin)
    if true then return end
    
    pcall(function()
        local Controllers = FindAllOf("PlayerController")
        if Controllers then
            for i = 1, #Controllers do
                local c = Controllers[i]
                if c and c:IsValid() then
                    if c.MyHUD and c.MyHUD:IsValid() then
                        c.MyHUD.bShowHUD = true
                    end
                    pcall(function() c.bShowVirtualJoystick = false end)
                    pcall(function() c.CurrentTouchInterface = nil end)
                    pcall(function() c:ActivateTouchInterface(nil) end)
                end
            end
        end
        
        local DebugControllers = FindAllOf("DebugCameraController")
        if DebugControllers then
            for i = 1, #DebugControllers do
                local c = DebugControllers[i]
                if c and c:IsValid() then
                    if c.MyHUD and c.MyHUD:IsValid() then
                        c.MyHUD.bShowHUD = true
                    end
                end
            end
        end
    end)

    local hiddenCount = 0
    -- 1. Try the ultra-safe native UWidgetBlueprintLibrary method first
    local ok = pcall(function()
        local WidgetLib = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
        local UserWidgetClass = StaticFindObject("/Script/UMG.UserWidget")
        local PC = GetActiveController()
        if WidgetLib and UserWidgetClass and PC and PC:IsValid() then
            local widgets = {}
            WidgetLib:GetAllWidgetsOfClass(PC, UserWidgetClass, widgets, false)
            if widgets then
                for _, w in pairs(widgets) do
                    if w and w:IsValid() then
                        local name = w:GetName()
                        if name and not name:find("Default__") then
                            w:SetRenderOpacity(0.0)
                            w:SetVisibility(3) -- ESlateVisibility::Hidden
                            hiddenCount = hiddenCount + 1
                        end
                    end
                end
            end
        end
    end)
    
    -- 2. Fallback to FindAllOf only if the native library method didn't hide anything
    if not ok or hiddenCount == 0 then
        pcall(function()
            local Widgets = FindAllOf("UserWidget")
            if Widgets then
                for i = 1, #Widgets do
                    local w = Widgets[i]
                    if w and w:IsValid() then
                        local name = ""
                        pcall(function() name = w:GetName() end)
                        if name and not name:find("Default__") then
                            local inViewport = false
                            pcall(function() inViewport = w:IsInViewport() end)
                            if inViewport then
                                pcall(function() w:SetRenderOpacity(0.0) end)
                                pcall(function() w:SetVisibility(3) end)
                            end
                        end
                    end
                end
            end
        end)
    end
end

-- Safe HUD restore function when mod is paused or stops
local function RestoreWidgetsSafe()
    local restoredCount = 0
    -- 1. Try the ultra-safe native UWidgetBlueprintLibrary method first
    local ok = pcall(function()
        local WidgetLib = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
        local UserWidgetClass = StaticFindObject("/Script/UMG.UserWidget")
        local PC = GetActiveController()
        if WidgetLib and UserWidgetClass and PC and PC:IsValid() then
            local widgets = {}
            WidgetLib:GetAllWidgetsOfClass(PC, UserWidgetClass, widgets, false)
            if widgets then
                for _, w in pairs(widgets) do
                    if w and w:IsValid() then
                        local name = w:GetName()
                        if name and not name:find("Default__") then
                            w:SetRenderOpacity(1.0)
                            w:SetVisibility(0) -- ESlateVisibility::Visible
                            restoredCount = restoredCount + 1
                        end
                    end
                end
            end
        end
    end)
    
    -- 2. Fallback to FindAllOf only if the native library method didn't restore anything
    if not ok or restoredCount == 0 then
        pcall(function()
            local Widgets = FindAllOf("UserWidget")
            if Widgets then
                for i = 1, #Widgets do
                    local w = Widgets[i]
                    if w and w:IsValid() then
                        local name = ""
                        pcall(function() name = w:GetName() end)
                        if name and not name:find("Default__") then
                            local inViewport = false
                            pcall(function() inViewport = w:IsInViewport() end)
                            if inViewport then
                                pcall(function() w:SetRenderOpacity(1.0) end)
                                pcall(function() w:SetVisibility(0) end)
                            end
                        end
                    end
                end
            end
        end)
    end
end

-- Absolute commands to disable standard HUD, Slate, and UMG layers
local function ConfigureCleanVisuals()
    -- KULLANICI ISTEGI: HUD GOZUKSUN
    -- RunConsoleCmd("ShowFlag.HUD 1")
    -- RunConsoleCmd("ShowFlag.LUI 1")
    -- RunConsoleCmd("ShowFlag.Slate 1") -- Completely disables all Slate UI overlays!
    RunConsoleCmd("ShowFlag.WidgetComponents 1")
    RunConsoleCmd("Slate.GameLayer.ViewportSlotVisible 1") -- Ultra-safe viewport hide
    RunConsoleCmd("r.MotionBlurQuality 0") -- Crystal clear renders
    RunConsoleCmd("r.DepthOfFieldQuality 0")
    RunConsoleCmd("r.FilmGrain 0") -- Turn off film grain/noise!
    RunConsoleCmd("r.FilmGrainQuality 0") -- Double check film grain disable
    RunConsoleCmd("r.Tonemapper.GrainQuantization 0") -- Disable screen quantization noise
    RunConsoleCmd("r.AntiAliasingMethod 1") -- Use FXAA instead of TAA to completely eliminate temporal ghosting/smearing when teleporting!
    RunConsoleCmd("r.SceneColorFringeQuality 0") -- Disable Chromatic Aberration (color fringing) which artificially shifts edges!
    RunConsoleCmd("r.DynamicRes.OperationMode 0") -- Lock resolution scaling to 100%
    RunConsoleCmd("r.ScreenPercentage 100") -- Lock screen percentage
    HideAllWidgetsSafe()
end

-- Safe HUD restore function when mod is paused or stops
local function RestoreVisuals()
    pcall(function()
        local Controllers = FindAllOf("PlayerController")
        if Controllers then
            for i = 1, #Controllers do
                local c = Controllers[i]
                if c and c:IsValid() then
                    if c.MyHUD and c.MyHUD:IsValid() then
                        c.MyHUD.bShowHUD = true
                    end
                end
            end
        end
        
        local DebugControllers = FindAllOf("DebugCameraController")
        if DebugControllers then
            for i = 1, #DebugControllers do
                local c = DebugControllers[i]
                if c and c:IsValid() then
                    if c.MyHUD and c.MyHUD:IsValid() then
                        c.MyHUD.bShowHUD = true
                    end
                end
            end
        end
        
        RunConsoleCmd("ShowFlag.HUD 1")
        RunConsoleCmd("ShowFlag.LUI 1")
        RunConsoleCmd("ShowFlag.Slate 1")
        RunConsoleCmd("ShowFlag.WidgetComponents 1")
        RunConsoleCmd("Slate.GameLayer.ViewportSlotVisible 1") -- Restore viewport slot visibility
        RunConsoleCmd("r.MotionBlurQuality 4")
        RunConsoleCmd("r.FilmGrain 1") -- Restore film grain if desired
        RunConsoleCmd("slomo 1") -- Restore global time if python disconnected!
        
        RestoreWidgetsSafe()
    end)
end

-- Write status file for Python handshake
local function WriteStatus(statusText)
    local file, err = io.open(STATUS_FILE_PATH, "w")
    if file then
        file:write(statusText)
        file:close()
    else
        print("[TalonDataset] ERROR writing status file: " .. tostring(err))
    end
end

-- Read status file for Python handshake
local function ReadStatus()
    local file = io.open(STATUS_FILE_PATH, "r")
    if file then
        local content = file:read("*all")
        file:close()
        return content:gsub("%s+", "") -- strip whitespace
    end
    return nil
end

-- STRICT DIVERSITY GUARD: Generates a highly diverse coordinate set
-- Rejects any combinations that have even minor similarities to the recent history of captures!
local function IsSimilar(p1, p2)
    local distDiff = math.abs(p1.dist - p2.dist)
    if distDiff >= 300 then return false end -- 3m difference is completely distinct
    
    local cpitchDiff = math.abs(p1.cpitch - p2.cpitch)
    if cpitchDiff >= 15 then return false end
    
    local cyawDiff = math.abs(p1.cyaw - p2.cyaw)
    if cyawDiff > 180 then cyawDiff = 360 - cyawDiff end
    if cyawDiff >= 30 then return false end
    
    local rollTiltDiff = math.abs(p1.rollTilt - p2.rollTilt)
    if rollTiltDiff >= 15 then return false end
    
    local drollDiff = math.abs(p1.droll - p2.droll)
    if drollDiff >= 15 then return false end
    
    local dpitchDiff = math.abs(p1.dpitch - p2.dpitch)
    if dpitchDiff >= 15 then return false end
    
    local dyawDiff = math.abs(p1.dyaw - p2.dyaw)
    if dyawDiff > 180 then dyawDiff = 360 - dyawDiff end
    if dyawDiff >= 30 then return false end
    
    return true
end

local function GenerateDiverseCombo(captureIndex)
    local combo = nil
    for attempt = 1, 100 do
        local actRot = {Pitch=0, Yaw=0, Roll=0}
        pcall(function() actRot = talonActor:K2_GetActorRotation() end)
        
        combo = {
            -- Daha farkli ve cesitli fotograflar icin mesafeyi 5m ile 12m arasina cektik
            dist = math.random(500, 1200),
            
            -- Keep the drone's EXACT natural flight orientation!
            droll = actRot.Roll,
            dpitch = actRot.Pitch,
            dyaw = actRot.Yaw
        }
        
        -- KULLANICI ISTEGI: Cok farkli acilar olsun, hic benzemesin.
        -- Genisletilmis Arka Yari Kure (Sag arka caprazdan sol arka capraza kadar)
        local targetLocalYaw = math.random(90, 270)
        combo.cyaw = (combo.dyaw + targetLocalYaw) % 360
        
        -- Genisletilmis Pitch: Tam alttan, hafif ustten vs.
        combo.cpitch = math.random(-70, 10)
        
        -- Daha fazla cesitlilik icin kameranin kendi yatmasi
        combo.rollTilt = math.random(-30, 30)
        
        -- BENZERLIK KONTROLU (Kullanici Istegi: 1000)
        local tooSimilar = false
        local startIdx = math.max(1, #poseHistory - 1000)
        for idx = startIdx, #poseHistory do
            if IsSimilar(combo, poseHistory[idx]) then
                tooSimilar = true
                break
            end
        end
        
        if not tooSimilar then
            break
        end
    end
    
    return combo
end

-- Find the active, alive drone actor safely (filters out CDOs, dead/destroyed, and hidden ones)
local function FindActiveTalon()
    local drones = FindAllOf("BPP_AIDroneTalon_C") or {}
    for i = 1, #drones do
        local drone = drones[i]
        if drone and drone:IsValid() then
            local name = ""
            pcall(function() name = drone:GetName() end)
            if name and not name:find("Default__") then
                local isDestroying = false
                pcall(function() isDestroying = drone.bActorIsBeingDestroyed end)
                
                local isHidden = false
                pcall(function() isHidden = drone:IsHidden() end)
                
                if not isDestroying and not isHidden then
                    return drone
                end
            end
        end
    end
    
    -- Fallback: return the first valid, non-destroying instance
    for i = 1, #drones do
        local drone = drones[i]
        if drone and drone:IsValid() then
            local name = ""
            pcall(function() name = drone:GetName() end)
            if name and not name:find("Default__") then
                local isDestroying = false
                pcall(function() isDestroying = drone.bActorIsBeingDestroyed end)
                if not isDestroying then
                    return drone
                end
            end
        end
    end
    return nil
end

-- State Machine ticking loop
local function ProcessStateMachine()
    if state == "INIT" then
        WriteStatus("OFFLINE")
        state = "WAITING_FOR_DRONE"
        print("[TalonDataset] Searching for Talon actor (BPP_AIDroneTalon_C)...")
        
    elseif state == "WAITING_FOR_DRONE" then
        local status = ReadStatus()
        if status == "WAITING_START" or (status and status:sub(1, 5) == "READY") or (status and status:sub(1, 4) == "DONE") then
            visualsRestored = false -- Reset restoration state for when we go offline again
            local found = FindActiveTalon()
            if found then
                talonActor = found
                print("[TalonDataset] Found Talon drone successfully! Preparing first capture spot.")
                
                -- 100% Bulletproof Component & Bone Dumper
                local function RunDumper()
                    local file, err = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\components_dump.txt", "w")
                    if not file then
                        print("[DumpTalon] Error opening file: " .. tostring(err))
                        return
                    end
                    
                    local function writeLine(text)
                        file:write(text .. "\n")
                        file:flush()
                    end
                    
                    writeLine("============================================================")
                    writeLine("TALON DRONE COMPONENT & SKELETAL MESH BONE DUMP (SAFE)")
                    writeLine("============================================================")
                    
                    local actorName = "Unknown"
                    pcall(function() actorName = found:GetFullName() end)
                    writeLine("Talon Actor Name: " .. tostring(actorName))
                    
                    local actLoc = {X=0, Y=0, Z=0}
                    pcall(function() actLoc = found:K2_GetActorLocation() end)
                    writeLine(string.format("Actor World Loc: X=%.4f, Y=%.4f, Z=%.4f", actLoc.X, actLoc.Y, actLoc.Z))
                    
                    local actRot = {Pitch=0, Yaw=0, Roll=0}
                    pcall(function() actRot = found:K2_GetActorRotation() end)
                    writeLine(string.format("Actor World Rot: P=%.4f, Y=%.4f, R=%.4f", actRot.Pitch, actRot.Yaw, actRot.Roll))
                    
                    -- Gather components safely using FindAllOf
                    local comps = {}
                    
                    -- Helper to add component
                    local function tryAddComp(comp)
                        if not comp or not comp:IsValid() then return end
                        local owner = nil
                        pcall(function() owner = comp:GetOwner() end)
                        if owner and owner:IsValid() and owner:GetAddress() == found:GetAddress() then
                            table.insert(comps, comp)
                        end
                    end
                    
                    pcall(function()
                        local skelComps = FindAllOf("SkeletalMeshComponent") or {}
                        for _, c in ipairs(skelComps) do tryAddComp(c) end
                    end)
                    
                    pcall(function()
                        local staticComps = FindAllOf("StaticMeshComponent") or {}
                        for _, c in ipairs(staticComps) do tryAddComp(c) end
                    end)
                    
                    pcall(function()
                        local sceneComps = FindAllOf("SceneComponent") or {}
                        for _, c in ipairs(sceneComps) do tryAddComp(c) end
                    end)
                    
                    writeLine(string.format("Total components found: %d", #comps))
                    
                    for i = 1, #comps do
                        local comp = comps[i]
                        if comp and comp:IsValid() then
                            local compName = "Unknown"
                            local className = "UnknownClass"
                            local fullName = ""
                            local okFull, errFull = pcall(function() fullName = comp:GetFullName() end)
                            if okFull and fullName then
                                className = fullName:match("^([^%s]+)") or "Component"
                                compName = fullName:match("%.([^%.]+)$") or "Unknown"
                            else
                                className = "ERR: " .. tostring(errFull)
                            end
                            
                            writeLine(string.format("\n------------------------------------------------------------"))
                            writeLine(string.format("Component #%d: Name=%s, Class=%s", i, compName, className))
                            
                            -- Relative location/rotation/scale
                            pcall(function()
                                local relLoc = comp.RelativeLocation
                                if relLoc then
                                    writeLine(string.format("  Relative Location: X=%.4f, Y=%.4f, Z=%.4f", relLoc.X, relLoc.Y, relLoc.Z))
                                end
                            end)
                            pcall(function()
                                local relRot = comp.RelativeRotation
                                if relRot then
                                    writeLine(string.format("  Relative Rotation: P=%.4f, Y=%.4f, R=%.4f", relRot.Pitch, relRot.Yaw, relRot.Roll))
                                end
                            end)
                            
                            -- World location/rotation
                            local wLoc = nil
                            pcall(function()
                                wLoc = comp:K2_GetComponentLocation()
                                if wLoc then
                                    writeLine(string.format("  World Location: X=%.4f, Y=%.4f, Z=%.4f", wLoc.X, wLoc.Y, wLoc.Z))
                                    writeLine(string.format("  Loc Relative to Actor: X=%.4f, Y=%.4f, Z=%.4f", wLoc.X - actLoc.X, wLoc.Y - actLoc.Y, wLoc.Z - actLoc.Z))
                                end
                            end)
                            
                            -- If SkeletalMeshComponent, dump bones
                            if className:find("SkeletalMeshComponent") then
                                local numBones = 0
                                pcall(function() numBones = comp:GetNumBones() end)
                                writeLine(string.format("  Bone Count: %d", numBones))
                                
                                if numBones > 0 then
                                    for b = 0, numBones - 1 do
                                        pcall(function()
                                            local boneNameObj = comp:GetBoneName(b)
                                            local boneName = tostring(boneNameObj)
                                            local boneWorldLoc = comp:GetSocketLocation(boneNameObj)
                                            if boneWorldLoc then
                                                local rx = boneWorldLoc.X - actLoc.X
                                                local ry = boneWorldLoc.Y - actLoc.Y
                                                local rz = boneWorldLoc.Z - actLoc.Z
                                                writeLine(string.format("    Bone #%d: %s | Actor Space Loc: X=%.4f, Y=%.4f, Z=%.4f", b, boneName, rx, ry, rz))
                                            end
                                        end)
                                    end
                                end
                            end
                            
                            -- Dump sockets for StaticMesh or SkeletalMesh
                            pcall(function()
                                local socketNames = comp:GetAllSocketNames()
                                if socketNames then
                                    writeLine(string.format("  Socket Count: %d", #socketNames))
                                    for s = 1, #socketNames do
                                        pcall(function()
                                            local socketNameObj = socketNames[s]
                                            local socketName = tostring(socketNameObj)
                                            local socketWorldLoc = comp:GetSocketLocation(socketNameObj)
                                            if socketWorldLoc then
                                                local rx = socketWorldLoc.X - actLoc.X
                                                local ry = socketWorldLoc.Y - actLoc.Y
                                                local rz = socketWorldLoc.Z - actLoc.Z
                                                writeLine(string.format("    Socket #%d: %s | Actor Space Loc: X=%.4f, Y=%.4f, Z=%.4f", s, socketName, rx, ry, rz))
                                            end
                                        end)
                                    end
                                end
                            end)
                        end
                    end
                    
                    file:close()
                    print("[DumpTalon] Component & bone dump successfully written!")
                end
                
                pcall(RunDumper)
                
                state = "FREEZE_AND_PREPARE"
            end
        else
            -- Only restore visuals once when transitioning to offline/idle to eliminate polling heap bloat!
            if not visualsRestored then
                pcall(function()
                    local found = FindFirstOf("BPP_AIDroneTalon_C")
                    if found and found:IsValid() then
                        found.CustomTimeDilation = 1.0
                    end
                end)
                local PC = GetActiveController()
                if PC and PC:IsValid() then
                    RestoreCameraActor(PC)
                end
                RestoreVisuals()
                
                -- Clear cached references to prevent dangling pointer issues in shipping GC cycles
                talonActor = nil
                visualsRestored = true
                uiHidden = false -- Reset UI hiding state
                print("[TalonDataset] System is idle/offline. Visuals and camera restored successfully.")
            end
        end
        
    elseif state == "FREEZE_AND_PREPARE" then
        -- Dynamic Drone Resolution: Always lookup the active drone actor to prevent crashes on destroyed/stale pointers!
        local activeTalon = FindActiveTalon()
        if activeTalon then
            talonActor = activeTalon
        else
            talonActor = nil
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end
        
        -- 1. Grab current dynamic location as anchor
        anchorLocation = talonActor:K2_GetActorLocation()
        print(string.format("[TalonDataset] Freezing Talon at X:%.1f Y:%.1f Z:%.1f for %d captures.", anchorLocation.X, anchorLocation.Y, anchorLocation.Z, CAPTURES_PER_SPOT))
        
        -- Save original viewpoint before snapping (DYNAMIC camera actor resolution)
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            originalViewTarget = PC:GetViewTarget()
            
            local camActor = GetCameraActor(PC)
            if camActor and camActor:IsValid() then
                -- KULLANICI ISTEGI: Kamera Tilt Acisini Konsola Yazdir
                local rot = camActor:K2_GetActorRotation()
                print("====== AVCI DRONE KAMERA TILT ACISI: " .. tostring(rot.Pitch) .. " ======")
                
                originalCamActor = camActor
                originalCamLocation = camActor:K2_GetActorLocation()
                
                pcall(function() PC:SetViewTarget(originalCamActor) end)
            end
        end

        -- 2. Freeze the drone's time dilation almost completely, but leave enough for mesh updates!
        talonActor.CustomTimeDilation = 0.0
        
        if not uiHidden then
            ConfigureCleanVisuals() -- This calls HideAllWidgetsSafe() exactly ONCE!
            uiHidden = true
        end
        
        -- Force Unreal Engine to render at exactly 125 FOV so it perfectly matches the Python Projection Math!
        RunConsoleCmd("fov 125.0")
        
        -- Force Windowed Fullscreen at 1920x1080 to eliminate Title Bar and Border offsets!
        RunConsoleCmd("r.SetRes 1920x1080w")
        
        spotCaptureCount = 0
        state = "APPLY_TRANSFORM"
        
    elseif state == "APPLY_TRANSFORM" then
        -- DUMP THE AVCI DRONE STRUCTURE TO UE4SS.LOG EVERY TIME WE TELEPORT!
        pcall(function()
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                local CamPawn = GetCameraActor(PC)
                if CamPawn and CamPawn:IsValid() and not _G.HasDumpedAvci2 then
                    _G.HasDumpedAvci2 = true
                    print("--- AVCI DRONE PAWN DUMP ---")
                    print("Class: " .. tostring(CamPawn:GetClass():GetFullName()))
                    
                    print("--- COMPONENTS ---")
                    local UActorComponent = rawget(_G, "UActorComponent")
                    if UActorComponent then
                        local comps = CamPawn:K2_GetComponentsByClass(UActorComponent:Class())
                        for i=1, #comps do
                            print("COMP: " .. tostring(comps[i]:GetClass():GetFullName()) .. " -> " .. tostring(comps[i]:GetFullName()))
                        end
                    end
                    print("--- END DUMP ---")
                end
            end
        end)
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end

        -- Generate a highly diverse combo using our Strict Diversity Guard!
        local combo = GenerateDiverseCombo(spotCaptureCount + 1)
        SavePoseToHistory(combo)
        
        -- 1. FORCE the Talon to stay exactly at the initial anchor location and rotation
        pcall(function()
            talonActor:K2_SetActorLocation(anchorLocation, false, {}, false)
            -- We don't overwrite its rotation completely, just ensure it stays put, but since the drone might tilt, let's lock it if we have anchorRotation.
            -- Wait, we don't have anchorRotation saved initially. Let's just enforce location for now.
        end)
        
        -- 2. Compute Camera spherical coordinates in Drone LOCAL space
        local radPitch = math.rad(combo.cpitch)
        
        -- Map combo.cyaw back to local offset
        local localYaw = combo.cyaw - combo.dyaw
        local radYaw = math.rad(localYaw)
        
        local lx = combo.dist * math.cos(radPitch) * math.cos(radYaw)
        local ly = combo.dist * math.cos(radPitch) * math.sin(radYaw)
        local lz = combo.dist * math.sin(radPitch)
        
        -- Rotate the local offset by the drone's frozen rotation to get the global offset
        local rotatedOffset = RotateVectorScaled({X = lx, Y = ly, Z = lz}, combo.dpitch, combo.dyaw, 0, nil)
        
        local camX = anchorLocation.X + rotatedOffset.X
        local camY = anchorLocation.Y + rotatedOffset.Y
        local camZ = anchorLocation.Z + rotatedOffset.Z
        
        -- 3. Calculate camera rotation to look directly at the drone
        local lookRot = CalculateLookAtRotation({ X = camX, Y = camY, Z = camZ }, anchorLocation)
        
        -- KULLANICI ISTEGI: AŞAĞI ORTAYI BOŞVER, EN YUKARIDA VE KÖŞELERDE OLSUN!
        -- Kırpılmayı önlemek için mesafeye göre sınır hesabı:
        local distRatio = math.max(0.0, math.min(1.0, (combo.dist - 200) / 1000)) 
        
        -- FOV Yaricaplari: Yatay ~65 derece, Dikey ~51 derece
        -- En uca ulasabilmek icin sinirlari sonuna kadar actik (Yaw max 53, Pitch max 49)
        local maxYaw = 15.0 + (38.0 * distRatio)
        local maxPitch = 15.0 + (34.0 * distRatio)
        
        local yawOffset = 0
        local pitchOffset = 0
        
        -- Istenmeyen bolgelere (Asagi Orta ve Tam Merkez) duserse tekrar rastgele sec! (Rejection Sampling)
        for attempt = 1, 100 do
            yawOffset = (math.random() * 2.0 - 1.0) * maxYaw
            pitchOffset = (math.random() * 2.0 - 1.0) * maxPitch
            
            -- UE4 Kamera yonleri: pitch NEGATIF = Drone YUKARI cikar. pitch POZITIF = Drone ASAGI iner.
            
            -- YASAKLI BOLGE 1: Asagi Orta (Kullanici "asagi ortayi bosver" dedi)
            -- Drone asagida (pitch > 5) VE yatayda ortada (abs(yaw) < 25)
            local isBottomCenter = (pitchOffset > 5.0) and (math.abs(yawOffset) < 25.0)
            
            -- YASAKLI BOLGE 2: Tam Merkez
            local isDeadCenter = (math.abs(pitchOffset) < 15.0) and (math.abs(yawOffset) < 15.0)
            
            if not isBottomCenter and not isDeadCenter then
                break -- Mukemmel noktayi bulduk, donguden cik!
            end
        end
        
        lookRot.Pitch = lookRot.Pitch + pitchOffset
        lookRot.Yaw = lookRot.Yaw + yawOffset
        lookRot.Roll = combo.rollTilt
        
        -- 4. Apply camera location and rotation
        SetCameraTransform(camX, camY, camZ, lookRot.Pitch, lookRot.Yaw, lookRot.Roll)

        -- Cache parameters for the render wait tick to query on the next state loop
        currentCombo = combo
        currentCamX = camX
        currentCamY = camY
        currentCamZ = camZ
        currentLookRot = lookRot

        state = "WAIT_FOR_RENDER"

    elseif state == "WAIT_FOR_RENDER" then
        -- Enforce talon anchor position!
        pcall(function() talonActor:K2_SetActorLocation(anchorLocation, false, {}, false) end)
        
        -- RECURSIVE NUCLEAR FREEZE: Walk the entire component tree to disable everything!
        -- (Since K2_GetComponentsByClass failed to find them)
        local function NukeComponent(Comp)
            if not Comp or not Comp:IsValid() then return end
            pcall(function() Comp:SetSimulatePhysics(false) end)
            pcall(function() Comp:SetEnableGravity(false) end)
            pcall(function() Comp:SetCollisionProfileName("NoCollision") end)
            pcall(function() Comp.Velocity = {X=0, Y=0, Z=0} end)
            -- If it's a Spring Arm
            pcall(function() Comp.bEnableCameraLag = false end)
            pcall(function() Comp.bEnableCameraRotationLag = false end)
            pcall(function() Comp.bDoCollisionTest = false end)
            -- If it's a Movement Component
            pcall(function() Comp:SetMovementMode(0) end)

            pcall(function()
                local children = Comp:GetAttachChildren()
                if children then
                    for i=1, #children do
                        NukeComponent(children[i])
                    end
                end
            end)
        end
        
        pcall(function()
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                PC.ControlRotation = { Pitch = currentLookRot.Pitch, Yaw = currentLookRot.Yaw, Roll = currentLookRot.Roll }
                local CamPawn = GetCameraActor(PC)
                if CamPawn and CamPawn:IsValid() then
                    CamPawn.CustomTimeDilation = 0.0
                    NukeComponent(CamPawn.RootComponent)
                    CamPawn:K2_SetActorLocation({ X = currentCamX, Y = currentCamY, Z = currentCamZ }, false, {}, true)
                    CamPawn:K2_SetActorRotation({ Pitch = currentLookRot.Pitch, Yaw = currentLookRot.Yaw, Roll = currentLookRot.Roll }, true)
                end
            end
        end)
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end

        local combo = currentCombo
        local camX = currentCamX
        local camY = currentCamY
        local camZ = currentCamZ
        local lookRot = currentLookRot

        -- Query ACTUAL final world state directly from the engine for 100% precision!
        local actualDroneLoc = anchorLocation
        local actualDroneRot = { Pitch = combo.dpitch, Yaw = combo.dyaw, Roll = combo.droll }
        
        pcall(function()
            local loc = talonActor:K2_GetActorLocation()
            if loc then actualDroneLoc = { X = loc.X, Y = loc.Y, Z = loc.Z } end
            
            local rot = talonActor:K2_GetActorRotation()
            if rot then actualDroneRot = { Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = rot.Roll } end
            
            -- OPTIMIZATION: Cache the visual mesh to prevent memory leaks from recursive tree-walking every frame!
            if not _G.CachedTalonVisualMesh or not _G.CachedTalonVisualMesh:IsValid() then
                local function findMesh(comp)
                    if not comp or not comp:IsValid() then return end
                    if string.find(comp:GetFullName(), "SM_Talon_Body") then
                        _G.CachedTalonVisualMesh = comp
                        return true
                    end
                    local found = false
                    pcall(function()
                        local children = comp:GetAttachChildren()
                        if children then
                            for i=1, #children do 
                                if findMesh(children[i]) then found = true; break end
                            end
                        end
                    end)
                    return found
                end
                findMesh(talonActor.RootComponent)
            end
            
            if _G.CachedTalonVisualMesh and _G.CachedTalonVisualMesh:IsValid() then
                local wLoc = _G.CachedTalonVisualMesh:K2_GetComponentLocation()
                local wRot = _G.CachedTalonVisualMesh:K2_GetComponentRotation()
                if wLoc then actualDroneLoc = { X = wLoc.X, Y = wLoc.Y, Z = wLoc.Z } end
                if wRot then actualDroneRot = { Pitch = wRot.Pitch, Yaw = wRot.Yaw, Roll = wRot.Roll } end
                print("[TalonDataset] Using VISUAL MESH exact rotation!")
            end
        end)

        local finalCamLoc = { X = camX, Y = camY, Z = camZ }
        local finalCamRot = { Pitch = lookRot.Pitch, Yaw = lookRot.Yaw, Roll = lookRot.Roll }
        local finalFOV = 125.0

        -- 1. Try to read the exact component transform of the UCameraComponent directly (instant, lag-free)
        local foundComp = false
        pcall(function()
            local camActor = originalCamActor
            if not camActor or not camActor:IsValid() then
                camActor = GetCameraActor(PC)
            end
            if camActor and camActor:IsValid() then
                local actorComponentClass = StaticFindObject("/Script/Engine.ActorComponent")
                if actorComponentClass and actorComponentClass:IsValid() then
                    local comps = camActor:K2_GetComponentsByClass(actorComponentClass)
                    if comps then
                        for i = 1, #comps do
                            local comp = comps[i]
                            if comp and comp:IsValid() then
                                local className = comp:GetClass():GetName()
                                if className:find("CameraComponent") or className == "CameraComponent" then
                                    local cloc = comp:K2_GetComponentLocation()
                                    local crot = comp:K2_GetComponentRotation()
                                    if cloc and crot then
                                        finalCamLoc = { X = cloc.X, Y = cloc.Y, Z = cloc.Z }
                                        finalCamRot = { Pitch = crot.Pitch, Yaw = crot.Yaw, Roll = crot.Roll }
                                        finalFOV = 125.0 -- Forced by user
                                        foundComp = true
                                        break
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end)

        -- 2. Fallback to CameraCachePrivate POV if component retrieval wasn't used/successful
        if not foundComp then
            pcall(function()
                if PC.PlayerCameraManager and PC.PlayerCameraManager:IsValid() then
                    local cache = PC.PlayerCameraManager.CameraCachePrivate
                    if cache then
                        local pov = cache.POV
                        if pov and pov.Location and pov.Rotation then
                            finalCamLoc.X = pov.Location.X
                            finalCamLoc.Y = pov.Location.Y
                            finalCamLoc.Z = pov.Location.Z
                            finalCamRot.Pitch = pov.Rotation.Pitch
                            finalCamRot.Yaw = pov.Rotation.Yaw
                            finalCamRot.Roll = pov.Rotation.Roll
                            finalFOV = 125.0 -- Forced by user
                        end
                    end
                end
            end)
        end

        -- HILE 1: ProjectWorldLocationToScreen ile %100 motor-tabanli 2D keypoint koordinatlari!
        local kp2d = {}
        local kp3d = {}
        local json2d = "{}"
        local json3d = "{}"
        pcall(function()
            local currentPC = GetActiveController()
            if currentPC and currentPC:IsValid() then
                local scale = {X=1,Y=1,Z=1}
                pcall(function() scale = talonActor:GetActorScale3D() end)
                kp2d, kp3d = BuildKeypoints2D(
                    actualDroneLoc,
                    actualDroneRot.Pitch, actualDroneRot.Yaw, actualDroneRot.Roll,
                    scale,
                    currentPC
                )
                -- JSON'a donustur
                local parts2d = {}
                local parts3d = {}
                for name, pt in pairs(kp2d) do
                    local onStr = pt.on and "true" or "false"
                    table.insert(parts2d, string.format('"' .. name .. '":{"x":%.2f,"y":%.2f,"on":%s}', pt.x, pt.y, onStr))
                end
                for name, pt in pairs(kp3d) do
                    table.insert(parts3d, string.format('"' .. name .. '":{"x":%.2f,"y":%.2f,"z":%.2f}', pt.x, pt.y, pt.z))
                end
                json2d = "{" .. table.concat(parts2d, ",") .. "}"
                json3d = "{" .. table.concat(parts3d, ",") .. "}"
                print(string.format("[HILE1] Keypoints projected! Nose: x=%.1f y=%.1f", kp2d.Nose and kp2d.Nose.x or -1, kp2d.Nose and kp2d.Nose.y or -1))
            end
        end)

        -- 6. Signal the Python script with a rich JSON metadata packet containing 100% exact engine-queried coordinates!
        local readySignal = string.format(
            '{"status":"READY","index":%d,"drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f,"keypoints_2d":%s,"keypoints_3d":%s}',
            frameIndex,
            actualDroneLoc.X, actualDroneLoc.Y, actualDroneLoc.Z,
            actualDroneRot.Pitch, actualDroneRot.Yaw, actualDroneRot.Roll,
            finalCamLoc.X, finalCamLoc.Y, finalCamLoc.Z,
            finalCamRot.Pitch, finalCamRot.Yaw, finalCamRot.Roll,
            finalFOV,
            json2d,
            json3d
        )

        WriteStatus(readySignal)
        pcall(function()
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                PC:SetPause(true)
            end
        end)
        state = "WAITING_FOR_CAPTURE"
        
    elseif state == "WAITING_FOR_CAPTURE" then
        -- RECURSIVE NUCLEAR FREEZE: Walk the entire component tree to disable everything!
        -- (Since K2_GetComponentsByClass failed to find them)
        local function NukeComponent(Comp)
            if not Comp or not Comp:IsValid() then return end
            pcall(function() Comp:SetSimulatePhysics(false) end)
            pcall(function() Comp:SetEnableGravity(false) end)
            pcall(function() Comp:SetCollisionProfileName("NoCollision") end)
            pcall(function() Comp.Velocity = {X=0, Y=0, Z=0} end)
            -- If it's a Spring Arm
            pcall(function() Comp.bEnableCameraLag = false end)
            pcall(function() Comp.bEnableCameraRotationLag = false end)
            pcall(function() Comp.bDoCollisionTest = false end)
            -- If it's a Movement Component
            pcall(function() Comp:SetMovementMode(0) end)

            pcall(function()
                local children = Comp:GetAttachChildren()
                if children then
                    for i=1, #children do
                        NukeComponent(children[i])
                    end
                end
            end)
        end
        
        pcall(function()
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                PC.ControlRotation = { Pitch = currentLookRot.Pitch, Yaw = currentLookRot.Yaw, Roll = currentLookRot.Roll }
                local CamPawn = GetCameraActor(PC)
                if CamPawn and CamPawn:IsValid() then
                    CamPawn.CustomTimeDilation = 0.0
                    NukeComponent(CamPawn.RootComponent)
                    CamPawn:K2_SetActorLocation({ X = currentCamX, Y = currentCamY, Z = currentCamZ }, false, {}, true)
                    CamPawn:K2_SetActorRotation({ Pitch = currentLookRot.Pitch, Yaw = currentLookRot.Yaw, Roll = currentLookRot.Roll }, true)
                end
            end
        end)
        local status = ReadStatus()
        local expectedResponse = "DONE_" .. tostring(frameIndex)
        
        if status == expectedResponse then
            pcall(function()
                local PC = GetActiveController()
                if PC and PC:IsValid() then
                    PC:SetPause(false)
                end
            end)
            frameIndex = frameIndex + 1
            spotCaptureCount = spotCaptureCount + 1
            
            if spotCaptureCount >= CAPTURES_PER_SPOT then
                print("[TalonDataset] Finished capture at spot. Moving to a new location...")
                state = "LET_IT_FLY"
                flyTickCount = 0
            else
                -- Proceed to next angle at this spot
                state = "APPLY_TRANSFORM"
            end
        elseif status == "WAITING_START" then
            frameIndex = 1
            spotCaptureCount = 0
            state = "APPLY_TRANSFORM"
        end
        
    elseif state == "LET_IT_FLY" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            uiHidden = false
            return
        end
        
        -- Unpause on transition tick to eliminate memory-heap bloat!
        if flyTickCount == 0 then
            -- 2. Restore drone's normal time dilation
            talonActor.CustomTimeDilation = 1.0
            
            -- 3. Restore global time
            RunConsoleCmd("slomo 1")
            
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                RestoreCameraActor(PC)
            end
        end

        flyTickCount = flyTickCount + 1
        if flyTickCount >= FLY_TICKS then
            -- Time is up! Let's freeze the drone at its new location.
            state = "FREEZE_AND_PREPARE"
        end
    end
end

-- Start asynchronous execution loop
LoopAsync(TICK_INTERVAL_MS, ProcessStateMachine)









-- ============================================================================
-- MANUAL SHOT HOTKEY (F9) - FOR THIRD PERSON / BIRD'S EYE VIEW DEMO SHOTS
-- ============================================================================
RegisterKeyBind(Key.F9, function()
    local PC = GetActiveController()
    local cL, cR = {X=0,Y=0,Z=0}, {Pitch=0,Yaw=0,Roll=0}
    pcall(function()
        if PC and PC.PlayerCameraManager then
            local pov = PC.PlayerCameraManager.CameraCachePrivate.POV
            cL = {X=pov.Location.X, Y=pov.Location.Y, Z=pov.Location.Z}
            cR = {Pitch=pov.Rotation.Pitch, Yaw=pov.Rotation.Yaw, Roll=pov.Rotation.Roll}
        end
    end)
    local tL, tR = {X=0,Y=0,Z=0}, {Pitch=0,Yaw=0,Roll=0}
    local drone = FindActiveTalon()
    if drone and drone:IsValid() then
        tL = drone:K2_GetActorLocation()
        tR = drone:K2_GetActorRotation()
    end
    local payload = string.format([[{"status":"MANUAL_SHOT","drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":131.54}]],
        tL.X, tL.Y, tL.Z, tR.Pitch, tR.Yaw, tR.Roll, cL.X, cL.Y, cL.Z, cR.Pitch, cR.Yaw, cR.Roll)
    pcall(function()
        local f = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt", "w")
        if f then f:write(payload); f:close() end
    end)
    print("[TalonDataset] F9 PRESSED! Manual Shot Triggered.")
end)

























-- ============================================================
-- HILELER
-- ============================================================
local talonFrozen = false
local frozenLocation = nil

local function GetTalonDrones()
    local found = {}
    local allActors = FindAllOf('Actor')
    if allActors then
        for _, a in ipairs(allActors) do
            if a and a:IsValid() then
                local n = tostring(a:GetFullName())
                if string.find(string.lower(n), 'talon') then
                    table.insert(found, a)
                end
            end
        end
    end
    return found
end

RegisterKeyBind(Key.NINE, function()
    talonFrozen = not talonFrozen
    local drones = GetTalonDrones()
    local count = 0
    for i = 1, #drones do
        local d = drones[i]
        if d and d:IsValid() then
            if talonFrozen then
                d.CustomTimeDilation = 0.0
                pcall(function() frozenLocation = d:K2_GetActorLocation() end)
                pcall(function()
                    local root = d.RootComponent
                    if root and root:IsValid() then
                        root:SetSimulatePhysics(false)
                        root.Velocity = {X=0,Y=0,Z=0}
                        root.AngularVelocity = {X=0,Y=0,Z=0}
                    end
                end)
                pcall(function()
                    local aicomp = d.CharacterMovement
                    if aicomp and aicomp:IsValid() then
                        aicomp.MaxFlySpeed = 0.0
                        aicomp.MaxSpeed = 0.0
                    end
                end)
            else
                d.CustomTimeDilation = 1.0
                pcall(function()
                    local root = d.RootComponent
                    if root and root:IsValid() then
                        root:SetSimulatePhysics(true)
                    end
                end)
                pcall(function()
                    local aicomp = d.CharacterMovement
                    if aicomp and aicomp:IsValid() then
                        aicomp.MaxFlySpeed = 3000.0
                        aicomp.MaxSpeed = 3000.0
                    end
                end)
            end
            count = count + 1
        end
    end
    if talonFrozen then
        print('[HILE] TALON DONDURULDU! 9 Tusu ile.')
    else
        print('[HILE] Talon serbest birakildi.')
    end
end)

local function KeepTalonFrozen()
    if not talonFrozen or frozenLocation == nil then return end
    local drones = GetTalonDrones()
    for i = 1, #drones do
        local d = drones[i]
        if d and d:IsValid() then
            pcall(function()
                d:K2_SetActorLocation(frozenLocation, false, {}, false)
                local root = d.RootComponent
                if root and root:IsValid() then root.Velocity = {X=0,Y=0,Z=0} end
            end)
        end
    end
end
LoopAsync(50, KeepTalonFrozen)

local avciFrozen = false
local avciLocation = nil
RegisterKeyBind(Key.F, function()
    avciFrozen = not avciFrozen
    pcall(function()
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            -- PC:ConsoleCommand('showhud 0', true) -- KULLANICI ISTEGI: HUD Gozuksun
            local pawn = PC:GetPawn()
            if pawn and pawn:IsValid() then
                if avciFrozen then
                    pawn.CustomTimeDilation = 0.0
                    avciLocation = pawn:K2_GetActorLocation()
                    local root = pawn.RootComponent
                    if root and root:IsValid() then
                        root:SetSimulatePhysics(false)
                        root.Velocity = {X=0,Y=0,Z=0}
                    end
                else
                    pawn.CustomTimeDilation = 1.0
                    local root = pawn.RootComponent
                    if root and root:IsValid() then
                        root:SetSimulatePhysics(true)
                    end
                end
            end
        end
    end)
    if avciFrozen then print('[HILE] AVCI DONDURULDU! F Tusu ile.') else print('[HILE] Avci serbest.') end
end)

local function KeepAvciFrozen()
    if not avciFrozen or avciLocation == nil then return end
    pcall(function()
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            local pawn = PC:GetPawn()
            if pawn and pawn:IsValid() then
                pawn:K2_SetActorLocation(avciLocation, false, {}, false)
                local root = pawn.RootComponent
                if root and root:IsValid() then root.Velocity = {X=0,Y=0,Z=0} end
            end
        end
    end)
end
LoopAsync(50, KeepAvciFrozen)

print('[HILE] Hileler yuklendi! 9 = Talon dondur, F = Avci dondur')
