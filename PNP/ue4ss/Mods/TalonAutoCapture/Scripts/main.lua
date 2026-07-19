local TICK_INTERVAL_MS = 100
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"

local talonActor = nil
local currentIndex = 0
local viewStep = 0 -- 0=Front, 1=Back, 2=Top, 3=Bottom

local function ReadStatus()
    local f = io.open(STATUS_FILE_PATH, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

local function WriteStatus(str)
    local f = io.open(STATUS_FILE_PATH, "w")
    if f then
        f:write(str)
        f:close()
    end
end

local function ConfigureCleanVisuals()
    RunConsoleCmd("ShowFlag.HUD 0")
    RunConsoleCmd("ShowFlag.LUI 0")
    RunConsoleCmd("ShowFlag.Slate 0")
    RunConsoleCmd("ShowFlag.WidgetComponents 0")
    RunConsoleCmd("Slate.GameLayer.ViewportSlotVisible 0")
end

local function TelemetryLoop()
    local status = ReadStatus()
    if not status then return end
    
    if status == "WAITING_START" or status:find("DONE_") then
        local doneIndex = -1
        if status:find("DONE_") then
            doneIndex = tonumber(status:match("DONE_(%d+)"))
            if not doneIndex then doneIndex = -1 end
        end
        
        if status == "WAITING_START" or doneIndex == currentIndex then
            -- Time to move to the next capture!
            if status == "WAITING_START" then
                currentIndex = 0
                viewStep = 0
            else
                currentIndex = currentIndex + 1
                viewStep = (viewStep + 1) % 4
            end
            
            -- Find Drone
            if not talonActor or not talonActor:IsValid() then
                talonActor = FindFirstOf("BPP_AIDroneTalon_C")
                if not talonActor then return end
            end
            
            local PC = GetActiveController()
            if not PC or not PC:IsValid() then return end
            
            local camActor = PC:GetViewTarget()
            if not camActor or not camActor:IsValid() then 
                camActor = PC:K2_GetPawn()
                if not camActor or not camActor:IsValid() then return end
            end
            
            ConfigureCleanVisuals()
            
            local talonLoc = talonActor:K2_GetActorLocation()
            local talonRot = talonActor:K2_GetActorRotation()
            
            local distance = 600.0
            local yaw = math.rad(talonRot.Yaw)
            local fx = math.cos(yaw) * distance
            local fy = math.sin(yaw) * distance
            
            local tx, ty, tz = talonLoc.X, talonLoc.Y, talonLoc.Z
            if viewStep == 0 then -- FRONT
                tx, ty, tz = talonLoc.X + fx, talonLoc.Y + fy, talonLoc.Z
            elseif viewStep == 1 then -- BACK
                tx, ty, tz = talonLoc.X - fx, talonLoc.Y - fy, talonLoc.Z + 100
            elseif viewStep == 2 then -- TOP
                tx, ty, tz = talonLoc.X, talonLoc.Y, talonLoc.Z + distance
            elseif viewStep == 3 then -- BOTTOM
                tx, ty, tz = talonLoc.X, talonLoc.Y, talonLoc.Z - distance
            end
            
            camActor:K2_SetActorLocation({X=tx, Y=ty, Z=tz}, false, {}, true)
            
            local dx = talonLoc.X - tx
            local dy = talonLoc.Y - ty
            local dz = talonLoc.Z - tz
            local dist_xy = math.sqrt(dx*dx + dy*dy)
            local targetPitch = math.deg(math.atan(dz, dist_xy))
            local targetYaw = math.deg(math.atan(dy, dx))
            
            local newRot = {Pitch=targetPitch, Yaw=targetYaw, Roll=0}
            pcall(function() PC:SetControlRotation(newRot) end)
            pcall(function() camActor:K2_SetActorRotation(newRot, true) end)
            pcall(function() camActor:K2_SetActorRotation(newRot, false) end)
            
            local fov = 90.0
            if PC.PlayerCameraManager and PC.PlayerCameraManager:IsValid() then
                fov = PC.PlayerCameraManager:GetFOVAngle()
            end
            
            local jsonStr = string.format(
                '{\n  "status": "READY",\n  "index": %d,\n  "view": %d,\n  "drone_location": {"x": %.3f, "y": %.3f, "z": %.3f},\n  "drone_rotation": {"pitch": %.3f, "yaw": %.3f, "roll": %.3f},\n  "camera_location": {"x": %.3f, "y": %.3f, "z": %.3f},\n  "camera_rotation": {"pitch": %.3f, "yaw": %.3f, "roll": %.3f},\n  "camera_fov": %.3f\n}',
                currentIndex, viewStep,
                talonLoc.X, talonLoc.Y, talonLoc.Z,
                talonRot.Pitch, talonRot.Yaw, talonRot.Roll,
                tx, ty, tz,
                targetPitch, targetYaw, 0,
                fov
            )
            
            WriteStatus(jsonStr)
        end
    end
end

LoopAsync(TICK_INTERVAL_MS, TelemetryLoop)
