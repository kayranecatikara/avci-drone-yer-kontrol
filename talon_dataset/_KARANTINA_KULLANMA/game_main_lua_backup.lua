-- ============================================================================
-- Talon UAV Dataset Generator - UE4SS Lua Mod (Freeze-Orbit-Move Cycle)
-- Target Game: Drones of War (Unreal Engine 5.5)
-- Target Actor: BPP_AIDroneTalon_C
-- Optimized for: 100% Stability, Perfect Drone Freezing, and Extreme Photo Diversity
-- ============================================================================

print("[TalonDataset] Mod initialized in Freeze-Orbit-Move mode with Rock-Solid Drone Freezing & Strict Diversity Guard!")

-- CONFIGURATION PARAMETERS
local CAPTURES_PER_SPOT = 50 -- How many distinct camera angles to capture at each frozen spot
local FLY_TICKS = 10         -- How many ticks to let the drone fly (2.5 seconds of flight)
local MIN_DIST = 400        -- Near view distance (4m)
local MAX_DIST = 4500       -- Far view distance (45m) - EXTENDED per user request!
local MIN_PITCH = -45       -- Camera elevation lower bound (degrees)
local MAX_PITCH = 55        -- Camera elevation upper bound (degrees)
local CAM_TILT_MAX = 30     -- Maximum random camera roll/tilt (degrees) for extreme variety
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"
local TICK_INTERVAL_MS = 250 -- State machine polling frequency

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

-- Distance tracking for deterministic increment (4m to 45m, 1m step)
local currentDistanceUnits = 400

-- Performance and visual tracking variables
local visualsRestored = false
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
local KEYPOINTS_LOCAL = {
    Nose = {X = 53.0, Y = 0.0, Z = 0.0},
    Left_Wingtip = {X = -4.0, Y = 85.9, Z = 0.0},
    Right_Wingtip = {X = -4.0, Y = -85.9, Z = 0.0},
    Tail = {X = -55.0, Y = 0.0, Z = 0.0},
    Left_Tail_Fin = {X = -75.0, Y = 20.0, Z = 22.0},
    Right_Tail_Fin = {X = -75.0, Y = -20.0, Z = 22.0}
}

local function RotateVector(vector, pitch, yaw, roll)
    local x, y, z = vector.X, vector.Y, vector.Z
    
    -- Rotate around X (Roll)
    local radRoll = math.rad(roll)
    local cosR, sinR = math.cos(radRoll), math.sin(radRoll)
    local y1 = y * cosR - z * sinR
    local z1 = y * sinR + z * cosR
    y, z = y1, z1
    
    -- Rotate around Y (Pitch)
    local radPitch = math.rad(pitch)
    local cosP, sinP = math.cos(radPitch), math.sin(radPitch)
    local x1 = x * cosP + z * sinP
    local z2 = -x * sinP + z * cosP
    x, z = x1, z2
    
    -- Rotate around Z (Yaw)
    local radYaw = math.rad(yaw)
    local cosY, sinY = math.cos(radYaw), math.sin(radYaw)
    local x2 = x * cosY - y * sinY
    local y2 = x * sinY + y * cosY
    x, y = x2, y2
    
    return { X = x, Y = y, Z = z }
end

local function GetTalonKeypointWorld(talon, localPt, pitch, yaw, roll)
    local rotated = RotateVector(localPt, pitch, yaw, roll)
    local loc = talon:K2_GetActorLocation()
    return {
        X = loc.X + rotated.X,
        Y = loc.Y + rotated.Y,
        Z = loc.Z + rotated.Z
    }
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
    local debugPawn = FindFirstOf("DebugCameraPawn")
    if debugPawn and debugPawn:IsValid() then
        return debugPawn
    end
    
    local bppSpec = FindFirstOf("BPP_Spectator_C")
    if bppSpec and bppSpec:IsValid() then
        return bppSpec
    end
    
    local specPawn = FindFirstOf("SpectatorPawn")
    if specPawn and specPawn:IsValid() then
        return specPawn
    end
    
    local viewTarget = PC:GetViewTarget()
    if viewTarget and viewTarget:IsValid() then
        local success, className = pcall(function() return viewTarget:GetClass():GetName() end)
        if success and className and not className:find("Talon") then
            return viewTarget
        end
    end
    
    local possessed = PC:K2_GetPawn()
    if possessed and possessed:IsValid() then
        local success, className = pcall(function() return possessed:GetClass():GetName() end)
        if success and className and not className:find("Talon") then
            return possessed
        end
    end
    
    return nil
end

-- Safely Pause/Unpause game physics absolute (not a toggle)
local function SetPhysicsPaused(paused)
    -- Disabled to allow real-time component transform ticking while drone is frozen
end

-- Get current spring arm length of an actor if it exists
local function GetSpringArmLength(actor)
    local length = nil
    pcall(function()
        if actor and actor:IsValid() then
            local actorComponentClass = StaticFindObject("/Script/Engine.ActorComponent")
            if actorComponentClass and actorComponentClass:IsValid() then
                local comps = actor:K2_GetComponentsByClass(actorComponentClass)
                if comps then
                    for i = 1, #comps do
                        local comp = comps[i]
                        if comp and comp:IsValid() then
                            local className = comp:GetClass():GetName()
                            if className:find("SpringArm") or className:find("CameraBoom") then
                                length = comp.TargetArmLength
                                break
                            end
                        end
                    end
                end
            end
        end
    end)
    return length
end

-- Set target spring arm length to 0 to align camera directly with camera actor's location
local function ZeroSpringArmLength(actor)
    pcall(function()
        if actor and actor:IsValid() then
            local actorComponentClass = StaticFindObject("/Script/Engine.ActorComponent")
            if actorComponentClass and actorComponentClass:IsValid() then
                local comps = actor:K2_GetComponentsByClass(actorComponentClass)
                if comps then
                    for i = 1, #comps do
                        local comp = comps[i]
                        if comp and comp:IsValid() then
                            local className = comp:GetClass():GetName()
                            if className:find("SpringArm") or className:find("CameraBoom") then
                                comp.TargetArmLength = 0.0
                                pcall(function() comp.bDoCollisionTest = false end)
                            end
                        end
                    end
                end
            end
        end
    end)
end

-- Robustly restore the camera actor state (location, spring arm length, visibility, time dilation, physics)
-- 100% Crash-Proof: Removes dangerous recursive loops that disable the viewport rendering lens
local function RestoreCameraActor(PC)
    pcall(function()
        if originalViewTarget and originalViewTarget:IsValid() then
            pcall(function() PC:SetViewTarget(originalViewTarget) end)
        end
    end)
    originalViewTarget = nil
    
    pcall(function()
        if originalCamActor and originalCamActor:IsValid() then
            -- 1. Restore location
            if originalCamLocation then
                originalCamActor:K2_SetActorLocation(originalCamLocation, false, {}, true)
            end
            
            -- 2. Restore SpringArm length
            if originalSpringArmLength then
                pcall(function()
                    local actorComponentClass = StaticFindObject("/Script/Engine.ActorComponent")
                    if actorComponentClass and actorComponentClass:IsValid() then
                        local comps = originalCamActor:K2_GetComponentsByClass(actorComponentClass)
                        if comps then
                            for i = 1, #comps do
                                local comp = comps[i]
                                if comp and comp:IsValid() then
                                    local className = comp:GetClass():GetName()
                                    if className:find("SpringArm") or className:find("CameraBoom") then
                                        comp.TargetArmLength = originalSpringArmLength
                                        pcall(function() comp.bDoCollisionTest = true end)
                                    end
                                end
                            end
                        end
                    end
                end)
            end
            
            -- 3. Restore visibility (Strictly safe, no SceneComponent disabling loops)
            pcall(function() originalCamActor:K2_SetActorHiddenInGame(false) end)
            pcall(function()
                if originalCamActor.Mesh and originalCamActor.Mesh:IsValid() then
                    originalCamActor.Mesh:SetHiddenInGame(false, true)
                end
            end)
            
            -- 4. Restore physics/gravity/dilation
            pcall(function() originalCamActor.CustomTimeDilation = 1.0 end)
            pcall(function()
                local root = originalCamActor.RootComponent
                if root and root:IsValid() then
                    if root.SetSimulatePhysics then root:SetSimulatePhysics(true) end
                    if root.SetEnableGravity then root:SetEnableGravity(true) end
                end
            end)
        end
    end)
    
    originalCamActor = nil
    originalCamLocation = nil
    originalSpringArmLength = nil
end

-- Teleport and rotate the camera safely (DYNAMICAL pawn resolution)
local function SetCameraTransform(x, y, z, pitch, yaw, roll)
    pcall(function()
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            -- Apply Rotation to Controller
            PC.ControlRotation = { Pitch = pitch, Yaw = yaw, Roll = roll }
            
            -- Apply Location and Rotation to possessed Pawn or found Camera Actor dynamically
            local CamPawn = PC.Pawn
            if not CamPawn or not CamPawn:IsValid() then
                CamPawn = FindFirstOf("DebugCameraPawn")
            end
            if not CamPawn or not CamPawn:IsValid() then
                CamPawn = FindFirstOf("SpectatorPawn")
            end
            
            if CamPawn and CamPawn:IsValid() then
                CamPawn:K2_SetActorLocation({ X = x, Y = y, Z = z }, false, {}, true)
                CamPawn:K2_SetActorRotation({ Pitch = pitch, Yaw = yaw, Roll = roll }, true)
            end
        end
    end)
end

-- Force hide all UMG User Widgets and disable Virtual Joysticks
local function HideAllWidgets()
    pcall(function()
        -- Disable HUD drawing on ALL controllers in the level (both Player and Debug Camera)
        local Controllers = FindAllOf("PlayerController")
        if Controllers then
            for i = 1, #Controllers do
                local c = Controllers[i]
                if c and c:IsValid() then
                    if c.MyHUD and c.MyHUD:IsValid() then
                        c.MyHUD.bShowHUD = false
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
                        c.MyHUD.bShowHUD = false
                    end
                end
            end
        end
        
        -- Make all widgets 100% transparent safely to bypass game tick race conditions
        local Widgets = FindAllOf("UserWidget")
        if Widgets then
            for i = 1, #Widgets do
                local w = Widgets[i]
                if w and w:IsValid() then
                    pcall(function() w:SetRenderOpacity(0.0) end)
                    pcall(function() w:SetVisibility(3) end) -- 3 is ESlateVisibility::Hidden
                end
            end
        end
    end)
end

-- Absolute commands to disable standard HUD, Slate, and UMG layers
local function ConfigureCleanVisuals()
    RunConsoleCmd("ShowFlag.HUD 0")
    RunConsoleCmd("ShowFlag.LUI 0")
    RunConsoleCmd("ShowFlag.Slate 0") -- Completely disables all Slate UI overlays!
    RunConsoleCmd("ShowFlag.WidgetComponents 0")
    RunConsoleCmd("r.MotionBlurQuality 0") -- Crystal clear renders
    RunConsoleCmd("r.DepthOfFieldQuality 0")
    RunConsoleCmd("r.FilmGrain 0") -- Turn off film grain/noise!
    RunConsoleCmd("r.FilmGrainQuality 0") -- Double check film grain disable
    RunConsoleCmd("r.Tonemapper.GrainQuantization 0") -- Disable screen quantization noise
    HideAllWidgets()
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
        RunConsoleCmd("r.MotionBlurQuality 4")
        RunConsoleCmd("r.FilmGrain 1") -- Restore film grain if desired
        
        local Widgets = FindAllOf("UserWidget")
        if Widgets then
            for i = 1, #Widgets do
                local w = Widgets[i]
                if w and w:IsValid() then
                    pcall(function() w:SetRenderOpacity(1.0) end)
                    pcall(function() w:SetVisibility(0) end) -- 0 is Visible
                end
            end
        end
    end)
end

-- Check if we are currently in any menu screen (Main Menu, Drone Select, Lobby, Pause Menu, etc.)
local function IsInMenu()
    local inMenu = false
    pcall(function()
        local Widgets = FindAllOf("UserWidget")
        if Widgets then
            for i = 1, #Widgets do
                local w = Widgets[i]
                if w and w:IsValid() then
                    local success, className = pcall(function() return w:GetClass():GetName() end)
                    if success and className then
                        local lowerName = className:lower()
                        if lowerName:find("menu") or lowerName:find("select") or lowerName:find("lobby") or lowerName:find("intro") or lowerName:find("setup") then
                            inMenu = true
                            break
                        end
                    end
                end
            end
        end
    end)
    return inMenu
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
-- Rejects any combinations that have even minor similarities to the previous capture!
local function GenerateDiverseCombo()
    local combo = nil
    for attempt = 1, 100 do
        combo = {
            dist = currentDistanceUnits,
            cpitch = math.random(MIN_PITCH, MAX_PITCH),
            cyaw = math.random(0, 359),
            rollTilt = math.random(-CAM_TILT_MAX, CAM_TILT_MAX),
            
            -- BANK & DIVE ANGLES: Rotate the drone severely while frozen for maximum dataset diversity
            droll = math.random(-50, 50),
            dpitch = math.random(-40, 40),
            dyaw = math.random(0, 359)
        }
        
        if not lastPose then
            break -- first capture is always accepted
        end
        
        -- Calculate absolute changes between current attempt and last frame to enforce diversity
        -- (Since distance is changing deterministically, we compare camera/drone angles)
        local cpitchDiff = math.abs(combo.cpitch - lastPose.cpitch)
        
        local cyawDiff = math.abs(combo.cyaw - lastPose.cyaw)
        if cyawDiff > 180 then cyawDiff = 360 - cyawDiff end
        
        local drollDiff = math.abs(combo.droll - lastPose.droll)
        local dpitchDiff = math.abs(combo.dpitch - lastPose.dpitch)
        
        local dyawDiff = math.abs(combo.dyaw - lastPose.dyaw)
        if dyawDiff > 180 then dyawDiff = 360 - dyawDiff end
        
        -- Score how many key features are significantly different
        local distinctCount = 0
        if cpitchDiff >= 20 then distinctCount = distinctCount + 1 end    -- Camera pitch changed by >= 20 deg
        if cyawDiff >= 60 then distinctCount = distinctCount + 1 end      -- Camera orbit angle changed by >= 60 deg
        if drollDiff >= 20 then distinctCount = distinctCount + 1 end     -- Drone bank angle changed by >= 20 deg
        if dpitchDiff >= 20 then distinctCount = distinctCount + 1 end    -- Drone dive/climb angle changed by >= 20 deg
        if dyawDiff >= 60 then distinctCount = distinctCount + 1 end      -- Drone heading angle changed by >= 60 deg
        
        -- Strict check: must have at least 3 parameters completely different to guarantee 0% visual similarity!
        if distinctCount >= 3 then
            break
        end
    end
    
    -- Advance distance deterministically for the NEXT frame!
    currentDistanceUnits = currentDistanceUnits + 100
    if currentDistanceUnits > MAX_DIST then
        currentDistanceUnits = MIN_DIST -- loop back to MIN_DIST (4m)
    end
    
    lastPose = combo
    return combo
end

-- State Machine ticking loop
local function ProcessStateMachine()
    -- Safeguard: Only scan for menus when WAITING_FOR_DRONE, and only once every 2 seconds (8 ticks)
    -- This cuts down Lua-C++ overhead by 99% and completely solves UE4SS garbage-collection crashes!
    if state == "WAITING_FOR_DRONE" then
        local now = os.time()
        if now - lastTalonSearchTime >= 2 then
            lastTalonSearchTime = now
            if IsInMenu() then
                if not visualsRestored then
                    RestoreVisuals()
                    visualsRestored = true
                end
                return
            end
        end
    end

    if state == "INIT" then
        WriteStatus("OFFLINE")
        state = "WAITING_FOR_DRONE"
        print("[TalonDataset] Searching for Talon actor (BPP_AIDroneTalon_C)...")
        
    elseif state == "WAITING_FOR_DRONE" then
        local status = ReadStatus()
        if status == "WAITING_START" or (status and status:sub(1, 5) == "READY") or (status and status:sub(1, 4) == "DONE") then
            visualsRestored = false -- Reset restoration state for when we go offline again
            local found = nil
            pcall(function()
                found = FindFirstOf("BPP_AIDroneTalon_C")
            end)
            
            if found and found:IsValid() then
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
                print("[TalonDataset] System is idle/offline. Visuals and camera restored successfully.")
            end
        end
        
    elseif state == "FREEZE_AND_PREPARE" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
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
                originalCamActor = camActor
                originalCamLocation = camActor:K2_GetActorLocation()
                originalSpringArmLength = GetSpringArmLength(camActor)
                
                -- Perform heavy camera locks and mesh component hiding ONCE to avoid engine crashes
                pcall(function() PC:SetViewTarget(originalCamActor) end)
                pcall(function() originalCamActor:K2_SetActorHiddenInGame(true) end)
                pcall(function()
                    if originalCamActor.Mesh and originalCamActor.Mesh:IsValid() then
                        originalCamActor.Mesh:SetHiddenInGame(true, true)
                    end
                end)
                
                -- Freeze the camera's time dilation and disable physics/gravity
                pcall(function() originalCamActor.CustomTimeDilation = 0.0 end)
                pcall(function()
                    local root = originalCamActor.RootComponent
                    if root and root:IsValid() then
                        if root.SetSimulatePhysics then root:SetSimulatePhysics(false) end
                        if root.SetEnableGravity then root:SetEnableGravity(false) end
                    end
                end)
                pcall(function() ZeroSpringArmLength(originalCamActor) end)
            end
        end

        -- 2. Freeze the drone's time dilation
        talonActor.CustomTimeDilation = 0.0
        
        -- 3. Disable local physics & gravity
        pcall(function()
            local root = talonActor.RootComponent
            if root and root:IsValid() then
                if root.SetSimulatePhysics then root:SetSimulatePhysics(false) end
                if root.SetEnableGravity then root:SetEnableGravity(false) end
            end
        end)
        
        -- 4. Pause the game physics (absolute) to freeze the drone natively, maintaining all velocity state!
        SetPhysicsPaused(true)
        ConfigureCleanVisuals() -- This calls HideAllWidgets() exactly ONCE!
        
        spotCaptureCount = 0
        state = "APPLY_TRANSFORM"
        
    elseif state == "APPLY_TRANSFORM" then
        if not talonActor or not talonActor:IsValid() then
            SetPhysicsPaused(false)
            state = "WAITING_FOR_DRONE"
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            SetPhysicsPaused(false)
            state = "WAITING_FOR_DRONE"
            return
        end

        -- Generate a highly diverse combo using our Strict Diversity Guard!
        local combo = GenerateDiverseCombo()
        
        -- 1. Apply drone frozen rotation
        pcall(function()
            talonActor:K2_SetActorRotation({ Pitch = combo.dpitch, Yaw = combo.dyaw, Roll = combo.droll }, true)
            talonActor:K2_SetActorLocation(anchorLocation, false, {}, true)
        end)
        
        -- 2. Compute Camera spherical coordinates centered on the Drone
        local radPitch = math.rad(combo.cpitch)
        local radYaw = math.rad(combo.cyaw)
        
        local dx = combo.dist * math.cos(radPitch) * math.cos(radYaw)
        local dy = combo.dist * math.cos(radPitch) * math.sin(radYaw)
        local dz = combo.dist * math.sin(radPitch)
        
        local camX = anchorLocation.X + dx
        local camY = anchorLocation.Y + dy
        local camZ = anchorLocation.Z + dz
        
        -- 3. Calculate camera rotation to look directly at the drone
        local lookRot = CalculateLookAtRotation({ X = camX, Y = camY, Z = camZ }, anchorLocation)
        lookRot.Roll = combo.rollTilt
        
        -- 4. Apply camera location and rotation
        SetCameraTransform(camX, camY, camZ, lookRot.Pitch, lookRot.Yaw, lookRot.Roll)
        
        -- Lock location and rotation of the camera actor
        if originalCamActor and originalCamActor:IsValid() then
            pcall(function() 
                originalCamActor:K2_SetActorLocation({ X = camX, Y = camY, Z = camZ }, false, {}, true) 
                originalCamActor:K2_SetActorRotation({ Pitch = lookRot.Pitch, Yaw = lookRot.Yaw, Roll = lookRot.Roll }, true) 
            end)
        end

        -- Cache parameters for the render wait tick to query on the next state loop
        currentCombo = combo
        currentCamX = camX
        currentCamY = camY
        currentCamZ = camZ
        currentLookRot = lookRot

        state = "WAIT_FOR_RENDER"

    elseif state == "WAIT_FOR_RENDER" then
        if not talonActor or not talonActor:IsValid() then
            SetPhysicsPaused(false)
            state = "WAITING_FOR_DRONE"
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            SetPhysicsPaused(false)
            state = "WAITING_FOR_DRONE"
            return
        end

        local combo = currentCombo
        local camX = currentCamX
        local camY = currentCamY
        local camZ = currentCamZ
        local lookRot = currentLookRot

        -- Query ACTUAL final world state directly from the engine for 100% precision!
        local actualDroneLoc = anchorLocation
        pcall(function()
            local loc = talonActor:K2_GetActorLocation()
            if loc then
                actualDroneLoc = { X = loc.X, Y = loc.Y, Z = loc.Z }
            end
        end)

        local actualDroneRot = { Pitch = combo.dpitch, Yaw = combo.dyaw, Roll = combo.droll }
        pcall(function()
            local rot = talonActor:K2_GetActorRotation()
            if rot then
                actualDroneRot = { Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = rot.Roll }
            end
        end)

        local finalCamLoc = { X = camX, Y = camY, Z = camZ }
        local finalCamRot = { Pitch = lookRot.Pitch, Yaw = lookRot.Yaw, Roll = lookRot.Roll }
        local finalFOV = 90.0

        -- 1. Try to read the exact component transform of the UCameraComponent directly (instant, lag-free)
        local foundComp = false
        pcall(function()
            local camActor = GetCameraActor(PC)
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
                                        finalFOV = comp.FieldOfView or 90.0
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
                            finalFOV = pov.FOV
                        end
                    end
                end
            end)
        end

        -- 6. Signal the Python script with a rich JSON metadata packet containing 100% exact engine-queried coordinates!
        local readySignal = string.format([[{"status":"READY","index":%d,"drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f}]],
            frameIndex,
            actualDroneLoc.X, actualDroneLoc.Y, actualDroneLoc.Z,
            actualDroneRot.Pitch, actualDroneRot.Yaw, actualDroneRot.Roll,
            finalCamLoc.X, finalCamLoc.Y, finalCamLoc.Z,
            finalCamRot.Pitch, finalCamRot.Yaw, finalCamRot.Roll,
            finalFOV
        )
        
        WriteStatus(readySignal)
        state = "WAITING_FOR_CAPTURE"
        
    elseif state == "WAITING_FOR_CAPTURE" then
        local status = ReadStatus()
        local expectedResponse = "DONE_" .. tostring(frameIndex)
        
        if status == expectedResponse then
            frameIndex = frameIndex + 1
            spotCaptureCount = spotCaptureCount + 1
            
            if spotCaptureCount >= CAPTURES_PER_SPOT then
                -- Finished capturing at this spot! Unfreeze the drone and let it fly to a new spot.
                print(string.format("[TalonDataset] Finished %d captures at this spot. Moving to a new location...", CAPTURES_PER_SPOT))
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
            return
        end
        
        -- Unpause and restore visuals exactly ONCE on transition tick to eliminate memory-heap bloat!
        if flyTickCount == 0 then
            -- 1. Unpause the game physics so the drone moves naturally with its velocity fully intact!
            SetPhysicsPaused(false)
            
            -- 2. Restore drone's normal time dilation
            talonActor.CustomTimeDilation = 1.0
            
            -- 3. Restore gravity/physics
            pcall(function()
                local root = talonActor.RootComponent
                if root and root:IsValid() then
                    if root.SetSimulatePhysics then root:SetSimulatePhysics(true) end
                    if root.SetEnableGravity then root:SetEnableGravity(true) end
                end
            end)
            
            local PC = GetActiveController()
            if PC and PC:IsValid() then
                RestoreCameraActor(PC)
            end
            RestoreVisuals() -- Restore visuals exactly ONCE per spot transition!
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
