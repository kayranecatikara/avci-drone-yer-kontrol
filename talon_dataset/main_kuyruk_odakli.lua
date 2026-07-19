-- ============================================================================
-- TAM ARKA CEKIM - Son ve kesin versiyon
-- Drone daima duz ucuyor, kamera her zaman tam arkasindan, 20-40m arasi
-- ============================================================================

print("[TalonDataset] TAM ARKA modu basladi. Drone duz, kamera sadece arkasindan!")

local CAPTURES_PER_SPOT = 2    -- Asla ayni arka plan olmamasi icin her noktada sadece 2 foto ceker, sonra ucar
local FLY_TICKS         = 10
local MIN_DIST          = 1500   -- 15m (kullanici istegi)
local MAX_DIST          = 2200   -- 22m (kullanici istegi)
local STATUS_FILE_PATH  = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"
local TICK_INTERVAL_MS  = 250

local state              = "INIT"
local talonActor         = nil
local anchorLocation     = nil
local originalCamActor   = nil
local originalCamLocation     = nil
local originalSpringArmLength = nil
local originalViewTarget = nil
local frameIndex         = 1
local lastTalonSearchTime= 0
local spotCaptureCount   = 0
local flyTickCount       = 0
local currentDist        = MIN_DIST

local visualsRestored    = false

local currentCamX, currentCamY, currentCamZ, currentLookRot = nil, nil, nil, nil
local currentDroneDyaw   = 0

math.randomseed(os.time())

local function CalculateLookAtRotation(s, t)
    local dx = t.X-s.X; local dy = t.Y-s.Y; local dz = t.Z-s.Z
    local d2 = math.sqrt(dx*dx+dy*dy)
    local yaw = math.deg(math.atan(dy,dx))
    local pitch = math.deg(math.atan(dz,d2))
    if yaw>180 then yaw=yaw-360 elseif yaw<-180 then yaw=yaw+360 end
    return {Pitch=pitch, Yaw=yaw, Roll=0.0}
end

local function RunConsoleCmd(cmd)
    pcall(function() ExecuteConsoleCommand(cmd) end)
end

local function GetActiveController()
    local PC = FindFirstOf("DebugCameraController")
    if not PC or not PC:IsValid() then
        local cs = FindAllOf("PlayerController") or {}
        for _,c in ipairs(cs) do
            if c:IsValid() then
                local ok,n = pcall(function() return c:GetClass():GetName() end)
                if ok and n and not n:find("Debug") then PC=c; break end
            end
        end
    end
    if not PC or not PC:IsValid() then PC=FindFirstOf("PlayerController") end
    return PC
end

local function GetCameraActor(PC)
    local a = FindFirstOf("DebugCameraPawn"); if a and a:IsValid() then return a end
    a = FindFirstOf("BPP_Spectator_C");       if a and a:IsValid() then return a end
    a = FindFirstOf("SpectatorPawn");          if a and a:IsValid() then return a end
    local vt = PC:GetViewTarget()
    if vt and vt:IsValid() then
        local ok,n=pcall(function() return vt:GetClass():GetName() end)
        if ok and n and not n:find("Talon") then return vt end
    end
    return nil
end

local function ZeroSpringArm(actor)
    pcall(function()
        if not actor or not actor:IsValid() then return end
        local cls = StaticFindObject("/Script/Engine.ActorComponent")
        if not cls or not cls:IsValid() then return end
        local comps = actor:K2_GetComponentsByClass(cls)
        if not comps then return end
        for i=1,#comps do
            local c=comps[i]
            if c and c:IsValid() then
                local n=c:GetClass():GetName()
                if n:find("SpringArm") or n:find("CameraBoom") then
                    c.TargetArmLength=0
                    pcall(function() c.bDoCollisionTest=false end)
                end
            end
        end
    end)
end

local function RestoreCameraActor(PC)
    pcall(function()
        if originalViewTarget and originalViewTarget:IsValid() then
            pcall(function() PC:SetViewTarget(originalViewTarget) end)
        end
        if originalCamActor and originalCamActor:IsValid() then
            if originalCamLocation then
                originalCamActor:K2_SetActorLocation(originalCamLocation,false,{},true)
            end
            if originalSpringArmLength then
                local cls=StaticFindObject("/Script/Engine.ActorComponent")
                if cls and cls:IsValid() then
                    local comps=originalCamActor:K2_GetComponentsByClass(cls)
                    if comps then
                        for i=1,#comps do
                            local c=comps[i]
                            if c and c:IsValid() then
                                local n=c:GetClass():GetName()
                                if n:find("SpringArm") or n:find("CameraBoom") then
                                    c.TargetArmLength=originalSpringArmLength
                                    pcall(function() c.bDoCollisionTest=true end)
                                end
                            end
                        end
                    end
                end
            end
            pcall(function() originalCamActor:K2_SetActorHiddenInGame(false) end)
            pcall(function() originalCamActor.CustomTimeDilation=1.0 end)
        end
    end)
    originalViewTarget=nil; originalCamActor=nil; originalCamLocation=nil; originalSpringArmLength=nil
end

local function SetCamTransform(x,y,z,pitch,yaw,roll)
    pcall(function()
        local PC=GetActiveController()
        if not PC or not PC:IsValid() then return end
        PC.ControlRotation={Pitch=pitch,Yaw=yaw,Roll=roll}
        local p=PC.Pawn
        if not p or not p:IsValid() then p=FindFirstOf("DebugCameraPawn") end
        if not p or not p:IsValid() then p=FindFirstOf("SpectatorPawn") end
        if p and p:IsValid() then
            p:K2_SetActorLocation({X=x,Y=y,Z=z},false,{},true)
            p:K2_SetActorRotation({Pitch=pitch,Yaw=yaw,Roll=roll},true)
        end
    end)
end

local function HideUI()
    RunConsoleCmd("ShowFlag.HUD 0"); RunConsoleCmd("ShowFlag.LUI 0")
    RunConsoleCmd("ShowFlag.Slate 0"); RunConsoleCmd("r.MotionBlurQuality 0")
    RunConsoleCmd("r.FilmGrain 0"); RunConsoleCmd("r.DepthOfFieldQuality 0")
    pcall(function()
        local ws=FindAllOf("UserWidget") or {}
        for _,w in ipairs(ws) do
            if w and w:IsValid() then
                pcall(function() w:SetRenderOpacity(0) end)
                pcall(function() w:SetVisibility(3) end)
            end
        end
        local cs=FindAllOf("PlayerController") or {}
        for _,c in ipairs(cs) do
            if c and c:IsValid() and c.MyHUD and c.MyHUD:IsValid() then
                c.MyHUD.bShowHUD=false
            end
        end
    end)
end

local function ShowUI()
    RunConsoleCmd("ShowFlag.HUD 1"); RunConsoleCmd("ShowFlag.LUI 1")
    RunConsoleCmd("ShowFlag.Slate 1"); RunConsoleCmd("r.MotionBlurQuality 4")
    RunConsoleCmd("r.FilmGrain 1")
    pcall(function()
        local ws=FindAllOf("UserWidget") or {}
        for _,w in ipairs(ws) do
            if w and w:IsValid() then
                pcall(function() w:SetRenderOpacity(1) end)
                pcall(function() w:SetVisibility(0) end)
            end
        end
        local cs=FindAllOf("PlayerController") or {}
        for _,c in ipairs(cs) do
            if c and c:IsValid() and c.MyHUD and c.MyHUD:IsValid() then
                c.MyHUD.bShowHUD=true
            end
        end
    end)
end

local function WriteStatus(s)
    local f=io.open(STATUS_FILE_PATH,"w")
    if f then f:write(s); f:close() end
end

local function ReadStatus()
    local f=io.open(STATUS_FILE_PATH,"r")
    if f then local s=f:read("*all"); f:close(); return s:gsub("%s+","") end
    return nil
end

-- ============================================================================
-- KALP: Her fotoğraf için kamera pozisyonu üret
-- ============================================================================
local function NextShot()
    -- 1) Drone rotasyonu (Hafif yamukluklar ekliyoruz ki drone statik ve sıkıcı durmasın)
    local droneYaw = math.random(0, 359)
    local dronePitch = math.random(-15, 15)  -- Drone hafif asagi/yukari bakabilir
    local droneRoll = math.random(-25, 25)   -- Drone yatis yapabilir

    -- 2) Mesafe: 15m - 22m arasi (kullanici istegi)
    local dist = math.random(MIN_DIST, MAX_DIST)
    
    -- 3) Kamera Acisi (YANLARDAN): Arkadan degil, sag veya sol capraz/yan.
    -- Offset: 45 derece ile 135 derece arasinda bir aci (Sag yan) veya tam tersi (Sol yan)
    local sideOffset = math.random(45, 135)
    if math.random() > 0.5 then sideOffset = -sideOffset end
    
    local camYaw = droneYaw + sideOffset
    if camYaw > 360 then camYaw = camYaw - 360 end
    if camYaw < 0 then camYaw = camYaw + 360 end

    -- 4) Kamera Yuksekligi (COK AZICIK ALCAKTAN):
    -- -5 ile -15 derece pitch kamerayi drone'un hafif altina konumlandirir (asagidan yukari bakar)
    local camPitch = math.random(-15, -5)

    return {
        droneYaw  = droneYaw,
        dronePitch= dronePitch,
        droneRoll = droneRoll,
        camYaw    = camYaw,
        camPitch  = camPitch,
        dist      = dist,
    }
end

-- State machine
local function Tick()
    if state == "INIT" then
        WriteStatus("OFFLINE")
        state = "FIND_DRONE"
        print("[TalonDataset] Talon aranıyor...")

    elseif state == "FIND_DRONE" then
        local status = ReadStatus()
        if status == "WAITING_START"
            or (status and status:sub(1,5) == "READY")
            or (status and status:sub(1,4) == "DONE") then

            local f=nil; pcall(function() f=FindFirstOf("BPP_AIDroneTalon_C") end)
            if f and f:IsValid() then
                talonActor = f
                print("[TalonDataset] Talon bulundu! Donduruyorum...")
                state = "FREEZE"
            end
        else
            if not visualsRestored then
                pcall(function()
                    local t=FindFirstOf("BPP_AIDroneTalon_C")
                    if t and t:IsValid() then t.CustomTimeDilation=1.0 end
                end)
                local PC=GetActiveController()
                if PC and PC:IsValid() then RestoreCameraActor(PC) end
                ShowUI(); talonActor=nil; visualsRestored=true
            end
        end

    elseif state == "FREEZE" then
        if not talonActor or not talonActor:IsValid() then state="FIND_DRONE"; return end

        anchorLocation = talonActor:K2_GetActorLocation()
        print(string.format("[TalonDataset] Donduruldu: X=%.0f Y=%.0f Z=%.0f",
            anchorLocation.X, anchorLocation.Y, anchorLocation.Z))

        -- Drone'u dondur
        talonActor.CustomTimeDilation = 0.0
        pcall(function()
            local r=talonActor.RootComponent
            if r and r:IsValid() then
                if r.SetSimulatePhysics then r:SetSimulatePhysics(false) end
                if r.SetEnableGravity   then r:SetEnableGravity(false)   end
            end
        end)

        -- Kamerayı hazırla
        local PC=GetActiveController()
        if PC and PC:IsValid() then
            originalViewTarget = PC:GetViewTarget()
            local cam = GetCameraActor(PC)
            if cam and cam:IsValid() then
                originalCamActor    = cam
                originalCamLocation = cam:K2_GetActorLocation()
                originalSpringArmLength = nil
                pcall(function()
                    local cls=StaticFindObject("/Script/Engine.ActorComponent")
                    if cls and cls:IsValid() then
                        local comps=cam:K2_GetComponentsByClass(cls)
                        if comps then
                            for i=1,#comps do
                                local c=comps[i]
                                if c and c:IsValid() then
                                    local n=c:GetClass():GetName()
                                    if n:find("SpringArm") or n:find("CameraBoom") then
                                        originalSpringArmLength=c.TargetArmLength; break
                                    end
                                end
                            end
                        end
                    end
                end)
                pcall(function() PC:SetViewTarget(cam) end)
                pcall(function() cam:K2_SetActorHiddenInGame(true) end)
                pcall(function() cam.CustomTimeDilation=0.0 end)
                ZeroSpringArm(cam)
            end
        end

        HideUI()
        spotCaptureCount = 0
        visualsRestored  = false
        state = "SHOOT"

    elseif state == "SHOOT" then
        if not talonActor or not talonActor:IsValid() then state="FIND_DRONE"; return end

        -- Bir sonraki çekim parametrelerini üret
        local shot = NextShot()
        currentDroneDyaw = shot.droneYaw

        -- Drone'u DÜZ UÇUŞ POZUNA al (pitch=0, roll=0, sadece yaw değişir)
        pcall(function()
            talonActor:K2_SetActorRotation(
                {Pitch=shot.dronePitch, Yaw=shot.droneYaw, Roll=shot.droneRoll}, true)
            talonActor:K2_SetActorLocation(anchorLocation, false, {}, true)
        end)

        -- Kamera pozisyonunu hesapla (drone YAW + 180, pitch=0)
        local radCamYaw   = math.rad(shot.camYaw)
        local radCamPitch = math.rad(shot.camPitch)
        local dx = shot.dist * math.cos(radCamPitch) * math.cos(radCamYaw)
        local dy = shot.dist * math.cos(radCamPitch) * math.sin(radCamYaw)
        local dz = shot.dist * math.sin(radCamPitch)

        local cx = anchorLocation.X + dx
        local cy = anchorLocation.Y + dy
        local cz = anchorLocation.Z + dz

        local lookRot = CalculateLookAtRotation({X=cx,Y=cy,Z=cz}, anchorLocation)
        lookRot.Roll  = 0

        SetCamTransform(cx, cy, cz, lookRot.Pitch, lookRot.Yaw, lookRot.Roll)
        if originalCamActor and originalCamActor:IsValid() then
            pcall(function()
                originalCamActor:K2_SetActorLocation({X=cx,Y=cy,Z=cz},false,{},true)
                originalCamActor:K2_SetActorRotation(
                    {Pitch=lookRot.Pitch,Yaw=lookRot.Yaw,Roll=0},true)
            end)
        end

        currentCamX=cx; currentCamY=cy; currentCamZ=cz; currentLookRot=lookRot

        state = "WAIT_RENDER"

    elseif state == "WAIT_RENDER" then
        if not talonActor or not talonActor:IsValid() then state="FIND_DRONE"; return end
        local PC=GetActiveController()
        if not PC or not PC:IsValid() then state="FIND_DRONE"; return end

        local dLoc={X=anchorLocation.X,Y=anchorLocation.Y,Z=anchorLocation.Z}
        pcall(function() local l=talonActor:K2_GetActorLocation(); if l then dLoc={X=l.X,Y=l.Y,Z=l.Z} end end)

        local dRot={Pitch=0,Yaw=currentDroneDyaw,Roll=0}
        pcall(function() local r=talonActor:K2_GetActorRotation(); if r then dRot={Pitch=r.Pitch,Yaw=r.Yaw,Roll=r.Roll} end end)

        local cLoc={X=currentCamX,Y=currentCamY,Z=currentCamZ}
        local cRot={Pitch=currentLookRot.Pitch,Yaw=currentLookRot.Yaw,Roll=0}
        local fov=90.0

        pcall(function()
            local cam=GetCameraActor(PC)
            if not cam or not cam:IsValid() then return end
            local cls=StaticFindObject("/Script/Engine.ActorComponent")
            if not cls or not cls:IsValid() then return end
            local comps=cam:K2_GetComponentsByClass(cls)
            if not comps then return end
            for i=1,#comps do
                local c=comps[i]
                if c and c:IsValid() and (c:GetClass():GetName():find("CameraComponent") or c:GetClass():GetName()=="CameraComponent") then
                    local l=c:K2_GetComponentLocation()
                    local r=c:K2_GetComponentRotation()
                    if l and r then
                        cLoc={X=l.X,Y=l.Y,Z=l.Z}
                        cRot={Pitch=r.Pitch,Yaw=r.Yaw,Roll=r.Roll}
                        fov=c.FieldOfView or 90.0
                    end
                    break
                end
            end
        end)

        local sig=string.format(
            [[{"status":"READY","index":%d,"drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f}]],
            frameIndex,
            dLoc.X,dLoc.Y,dLoc.Z,
            dRot.Pitch,dRot.Yaw,dRot.Roll,
            cLoc.X,cLoc.Y,cLoc.Z,
            cRot.Pitch,cRot.Yaw,cRot.Roll,
            fov)
        WriteStatus(sig)
        state = "WAIT_DONE"

    elseif state == "WAIT_DONE" then
        local s=ReadStatus()
        if s == "DONE_"..tostring(frameIndex) then
            frameIndex       = frameIndex+1
            spotCaptureCount = spotCaptureCount+1
            if spotCaptureCount >= CAPTURES_PER_SPOT then
                print("[TalonDataset] Bu noktada bitti, ucuyor...")
                state="FLY"; flyTickCount=0
            else
                state="SHOOT"
            end
        elseif s == "WAITING_START" then
            frameIndex=1; spotCaptureCount=0; state="SHOOT"
        end

    elseif state == "FLY" then
        if not talonActor or not talonActor:IsValid() then state="FIND_DRONE"; return end
        if flyTickCount==0 then
            talonActor.CustomTimeDilation=1.0
            pcall(function()
                local r=talonActor.RootComponent
                if r and r:IsValid() then
                    if r.SetSimulatePhysics then r:SetSimulatePhysics(true) end
                    if r.SetEnableGravity   then r:SetEnableGravity(true)   end
                end
            end)
            local PC=GetActiveController()
            if PC and PC:IsValid() then RestoreCameraActor(PC) end
            ShowUI()
        end
        flyTickCount=flyTickCount+1
        if flyTickCount>=FLY_TICKS then state="FREEZE" end
    end
end

LoopAsync(TICK_INTERVAL_MS, Tick)
