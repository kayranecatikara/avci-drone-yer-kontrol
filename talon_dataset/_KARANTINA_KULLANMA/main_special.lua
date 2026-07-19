-- ============================================================================
-- Special Temporary Mod Script for Back, Right, and Top Views (3m to 8m)
-- Target Game: Drones of War (Unreal Engine 5.5)
-- Target Actor: BPP_AIDroneTalon_C
-- Optimized for: 100% Perfect Camera Alignment using Engine POV Queries!
-- ============================================================================

print("[TalonSpecial] Loading robust temporary view capture script...")

-- CONFIGURATION PARAMETERS
local CAPTURES_PER_SPOT = 3 -- 3 distances per angle
local STATUS_FILE_PATH = "c:\\\\Users\\\\Zeylo\\\\Desktop\\\\talon_dataset\\\\status.txt"
local TICK_INTERVAL_MS = 250

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

-- Math Helper: Calculate look-at rotation in degrees from Start to Target
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

-- Safely run console commands on the engine console
local function RunConsoleCmd(cmd)
    pcall(function()
        ExecuteConsoleCommand(cmd)
    end)
end

-- Get the active player/camera controller dynamically
local function GetActiveController()
    local PC = FindFirstOf("DebugCameraController")
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
    local viewTarget = PC:GetViewTarget()
    if viewTarget and viewTarget:IsValid() then
        return viewTarget
    end
    return nil
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

-- Robustly restore the camera actor state
local function RestoreCameraActor(PC)
    pcall(function()
        if originalViewTarget and originalViewTarget:IsValid() then
            PC:SetViewTarget(originalViewTarget)
        end
    end)
    originalViewTarget = nil
    originalCamActor = nil
end

-- Teleport and rotate the camera safely
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

-- Force hide all UMG User Widgets
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

-- Absolute commands to disable standard HUD, Slate, and UMG layers
local function ConfigureCleanVisuals()
    RunConsoleCmd("ShowFlag.HUD 0")
    RunConsoleCmd("ShowFlag.LUI 0")
    RunConsoleCmd("ShowFlag.Slate 0")
    RunConsoleCmd("ShowFlag.WidgetComponents 0")
    HideAllWidgets()
end

-- Safe HUD restore function when mod is paused or stops
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

-- Write status file for Python handshake
local function WriteStatus(statusText)
    local file = io.open(STATUS_FILE_PATH, "w")
    if file then
        file:write(statusText)
        file:close()
    end
end

-- Read status file for Python handshake
local function ReadStatus()
    local file = io.open(STATUS_FILE_PATH, "r")
    if file then
        local content = file:read("*all")
        file:close()
        return content:gsub("%s+", "")
    end
    return nil
end

-- Special Generate Combo function (sequential)
local function GenerateDiverseCombo()
    local combo = specialCombos[frameIndex]
    return combo
end

-- State Machine ticking loop
local function ProcessStateMachine()
    if state == "INIT" then
        WriteStatus("OFFLINE")
        state = "WAITING_FOR_DRONE"
        print("[TalonSpecial] Searching for Talon actor...")
        
    elseif state == "WAITING_FOR_DRONE" then
        local status = ReadStatus()
        if status == "WAITING_START" then
            visualsRestored = false
            local found = FindFirstOf("BPP_AIDroneTalon_C")
            if found and found:IsValid() then
                talonActor = found
                print("[TalonSpecial] Found Talon drone successfully! Preparing freeze.")
                state = "FREEZE_AND_PREPARE"
            end
        end
        
    elseif state == "FREEZE_AND_PREPARE" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            return
        end
        
        -- 1. Grab current dynamic location as anchor
        anchorLocation = talonActor:K2_GetActorLocation()
        
        -- Save original viewpoint before snapping
        local PC = GetActiveController()
        if PC and PC:IsValid() then
            originalViewTarget = PC:GetViewTarget()
            local camActor = GetCameraActor(PC)
            if camActor and camActor:IsValid() then
                originalCamActor = camActor
                originalCamLocation = camActor:K2_GetActorLocation()
                originalSpringArmLength = camActor.TargetArmLength or 0.0
                
                pcall(function() PC:SetViewTarget(originalCamActor) end)
                pcall(function() originalCamActor:K2_SetActorHiddenInGame(true) end)
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
        
        ConfigureCleanVisuals()
        state = "APPLY_TRANSFORM"
        
    elseif state == "APPLY_TRANSFORM" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            state = "WAITING_FOR_DRONE"
            return
        end

        if frameIndex > #specialCombos then
            -- We are fully done! Signal finished!
            print("[TalonSpecial] Captured all 9 views successfully!")
            WriteStatus("FINISHED")
            state = "CLEANUP"
            return
        end

        local combo = GenerateDiverseCombo()
        
        -- 1. Apply drone frozen rotation (perfectly flat level!)
        pcall(function()
            talonActor:K2_SetActorRotation({ Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }, true)
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

        -- Cache parameters for the render wait tick
        currentCombo = combo
        currentCamX = camX
        currentCamY = camY
        currentCamZ = camZ
        currentLookRot = lookRot

        state = "WAIT_FOR_RENDER"

    elseif state == "WAIT_FOR_RENDER" then
        if not talonActor or not talonActor:IsValid() then
            state = "WAITING_FOR_DRONE"
            return
        end
        
        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
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

        local actualDroneRot = { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }

        local finalCamLoc = { X = camX, Y = camY, Z = camZ }
        local finalCamRot = { Pitch = lookRot.Pitch, Yaw = lookRot.Yaw, Roll = lookRot.Roll }
        local finalFOV = 90.0

        -- 1. Try to read the exact component transform of the UCameraComponent directly
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
        local readySignal = string.format([[{"status":"READY","index":%d,"view_name":"%s","drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":0,"yaw":0,"roll":0},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f}]],
            frameIndex,
            combo.name,
            actualDroneLoc.X, actualDroneLoc.Y, actualDroneLoc.Z,
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
            state = "APPLY_TRANSFORM"
        end
        
    elseif state == "CLEANUP" then
        if not visualsRestored then
            talonActor.CustomTimeDilation = 1.0
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
            RestoreVisuals()
            visualsRestored = true
            print("[TalonSpecial] Restored normal game state.")
        end
    end
end

LoopAsync(TICK_INTERVAL_MS, ProcessStateMachine)
