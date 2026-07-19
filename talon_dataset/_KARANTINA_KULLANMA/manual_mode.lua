local TICK_INTERVAL_MS = 10
local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"

local talonActor = nil
local currentIndex = 0
local globalIndex = 0
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
    RunConsoleCmd("fov 125") -- Render FOV'unu Python izdusumuyle (125) birebir esitle
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
            
            local targetGlobalCount = currentIndex + 1
            
            local debugF = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if debugF then debugF:write("Lua tick started. Status: " .. status .. "\n"); debugF:close() end
            
            -- Find Drone
            if not talonActor or not talonActor:IsValid() then
                talonActor = FindFirstOf("BPP_AIDroneTalon_C")
                if not talonActor then 
                    local df = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
                    if df then df:write("Waiting for BPP_AIDroneTalon_C...\n"); df:close() end
                    return 
                end
            end
            
            local df_step1 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_step1 then df_step1:write("Step 1: Drone found\n"); df_step1:close() end
            
            local PC = GetActiveController()
            if not PC or not PC:IsValid() then 
                local df = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
                if df then df:write("Waiting for Active Controller...\n"); df:close() end
                return 
            end
            
            local df_step2 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_step2 then df_step2:write("Step 2: PC found\n"); df_step2:close() end
            
            local camActor = PC:GetViewTarget()
            if not camActor or not camActor:IsValid() then 
                camActor = PC:K2_GetPawn()
                if not camActor or not camActor:IsValid() then 
                    local df = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
                    if df then df:write("Waiting for Camera Actor...\n"); df:close() end
                    return 
                end
            end
            
            local df_step3 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_step3 then df_step3:write("Step 3: Camera found\n"); df_step3:close() end
            
            pcall(function() ConfigureCleanVisuals() end)
            
            local df_step4 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_step4 then df_step4:write("Step 4: Visuals configured\n"); df_step4:close() end
            
            local talonLoc = {X=0, Y=0, Z=0}
            pcall(function() talonLoc = talonActor:K2_GetActorLocation() end)
            
            local df_step5 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_step5 then df_step5:write("Step 5: Got Actor Location\n"); df_step5:close() end
            
            local talonRot = {Pitch=0, Yaw=0, Roll=0}
            pcall(function() talonRot = talonActor:K2_GetActorRotation() end)
            
            local df_calc1 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_calc1 then df_calc1:write("Calculating distance...\n"); df_calc1:close() end
            
            local pitch_deg = math.random(-70, 85)
            local rPitch = math.rad(pitch_deg) 
            local rYaw = math.rad(math.random(0, 359)) 
            
            local distance = 1000
            if targetGlobalCount <= 3000 then
                distance = math.random(150, 1000)
            elseif targetGlobalCount <= 5160 then
                distance = math.random(1000, 2000)
            elseif targetGlobalCount <= 9000 then
                distance = math.random(2000, 3000)
            else
                distance = math.random(4000, 5000)
            end
            
            local df_calc2 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_calc2 then df_calc2:write("Setting location...\n"); df_calc2:close() end
            
            local lx = distance * math.cos(rPitch) * math.cos(rYaw)
            local ly = distance * math.cos(rPitch) * math.sin(rYaw)
            local lz = distance * math.sin(rPitch)
            local tx = talonLoc.X + lx
            local ty = talonLoc.Y + ly
            local tz = talonLoc.Z + lz
            
            pcall(function() camActor:K2_SetActorLocation({X=tx, Y=ty, Z=tz}, false, {}, true) end)
            
            local df_calc3 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_calc3 then df_calc3:write("Calculating rotation...\n"); df_calc3:close() end
            
            local dx = talonLoc.X - tx
            local dy = talonLoc.Y - ty
            local dz = talonLoc.Z - tz
            local dist_xy = math.sqrt(dx*dx + dy*dy)
            
            -- FIX FOR math.atan: Use math.atan2 if available, or just math.atan(y/x) safely
            local targetPitch = 0
            local targetYaw = 0
            pcall(function() 
                if math.atan2 then
                    targetPitch = math.deg(math.atan2(dz, dist_xy))
                    targetYaw = math.deg(math.atan2(dy, dx))
                else
                    targetPitch = math.deg(math.atan(dz, dist_xy))
                    targetYaw = math.deg(math.atan(dy, dx))
                end
            end)
            
            local df_calc4 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df_calc4 then df_calc4:write("Setting rotation...\n"); df_calc4:close() end
            
            -- Kameraya rastgele roll (tilt) ekleyerek inanilmaz bir cesitlilik sagla
            local targetRoll = math.random(-45, 45)
            
            local newRot = {Pitch=targetPitch, Yaw=targetYaw, Roll=targetRoll}
            pcall(function() PC:SetControlRotation(newRot) end)
            pcall(function() camActor:K2_SetActorRotation(newRot, true) end)
            pcall(function() camActor:K2_SetActorRotation(newRot, false) end)
            
            local df2 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df2 then df2:write("Setting up string format...\n"); df2:close() end
            
            -- FOV motorla 125'e sabitlendi.
            local fov = 125.0
            
            local jsonStr = string.format(
                '{\n  "status": "READY",\n  "index": %d,\n  "view": %d,\n  "drone_location": {"x": %.3f, "y": %.3f, "z": %.3f},\n  "drone_rotation": {"pitch": %.3f, "yaw": %.3f, "roll": %.3f},\n  "camera_location": {"x": %.3f, "y": %.3f, "z": %.3f},\n  "camera_rotation": {"pitch": %.3f, "yaw": %.3f, "roll": %.3f},\n  "camera_fov": %.3f\n}',
                currentIndex, viewStep,
                talonLoc.X or 0, talonLoc.Y or 0, talonLoc.Z or 0,
                talonRot.Pitch or 0, talonRot.Yaw or 0, talonRot.Roll or 0,
                tx or 0, ty or 0, tz or 0,
                targetPitch or 0, targetYaw or 0, targetRoll or 0,
                fov
            )
            
            local df3 = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\lua_debug.txt", "a")
            if df3 then df3:write("String format successful, writing to status.txt...\n"); df3:close() end
            
            WriteStatus(jsonStr)
        end
    end
end

LoopAsync(TICK_INTERVAL_MS, TelemetryLoop)
