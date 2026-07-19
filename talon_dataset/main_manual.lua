-- ============================================================================
-- TAM MANUEL CEKIM MODU (PYTHON KONTROLLU)
-- Sen oyunda ucarsin. '1' tusuna bastiginda Python dosyaya REQUEST_MANUAL yazar.
-- Lua bunu gorur, hesaplar, READY_MANUAL yazar. Python ekran resmini ceker.
-- ============================================================================

print("[TalonDataset] MANUEL MOD AKTIF! Cekim yapmak icin '1' tusuna bas.")
print("[TalonDataset] HILELER: F10 (Tam Arkaya Isinla), Numpad 4/6 (Yaw), 7/9 (Roll), 8/2 (Pitch)")

local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"

local KEYPOINTS = {
    {name="Nose",           x= 53.0, y=  0.0,  z=  0.0},
    {name="Left_Wingtip",   x= -4.0, y= 85.9,  z=  0.0},
    {name="Right_Wingtip",  x= -4.0, y=-85.9,  z=  0.0},
    {name="Tail",           x=-55.0, y=  0.0,  z=  0.0},
    {name="Left_Tail_Fin",  x=-75.0, y= 20.0,  z= 22.0},
    {name="Right_Tail_Fin", x=-75.0, y=-20.0,  z= 22.0},
}

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

local function BuildKeypointsJSON(PC, actor)
    local base = actor:K2_GetActorLocation()

    local fwd, rgt, up
    pcall(function() fwd = actor:GetActorForwardVector() end)
    pcall(function() rgt = actor:GetActorRightVector()   end)
    pcall(function() up  = actor:GetActorUpVector()       end)

    local function bad(v) return (not v) or v.X == nil end
    if bad(fwd) or bad(rgt) or bad(up) then
        local yaw = 0.0
        pcall(function() local r = actor:K2_GetActorRotation(); if r then yaw = r.Yaw end end)
        local y  = math.rad(yaw)
        local cy, sy = math.cos(y), math.sin(y)
        fwd = {X = cy,  Y = sy,  Z = 0.0}
        rgt = {X = -sy, Y = cy,  Z = 0.0}
        up  = {X = 0.0, Y = 0.0, Z = 1.0}
    end

    local function finite(n) return n == n and n ~= math.huge and n ~= -math.huge end

    local parts2d, parts3d = {}, {}
    for i = 1, #KEYPOINTS do
        local kp = KEYPOINTS[i]
        local wx = base.X + kp.x*fwd.X + kp.y*rgt.X + kp.z*up.X
        local wy = base.Y + kp.x*fwd.Y + kp.y*rgt.Y + kp.z*up.Y
        local wz = base.Z + kp.x*fwd.Z + kp.y*rgt.Z + kp.z*up.Z

        local sx, sy, on = 0.0, 0.0, false
        pcall(function()
            local screen = {X = 0.0, Y = 0.0}
            local r = PC:ProjectWorldLocationToScreen({X = wx, Y = wy, Z = wz}, screen, false)
            if type(r) == "boolean" then on = r end
            if screen and screen.X ~= nil then sx, sy = screen.X, screen.Y end
        end)
        if not (finite(sx) and finite(sy)) then sx, sy, on = 0.0, 0.0, false end

        parts3d[#parts3d+1] = string.format('"%s":{"x":%.2f,"y":%.2f,"z":%.2f}', kp.name, wx, wy, wz)
        parts2d[#parts2d+1] = string.format('"%s":{"x":%.2f,"y":%.2f,"on":%s}',   kp.name, sx, sy, tostring(on))
    end

    return "{" .. table.concat(parts2d, ",") .. "}", "{" .. table.concat(parts3d, ",") .. "}"
end

local function ReadStatus()
    local f = io.open(STATUS_FILE_PATH, "r")
    if f then 
        local s = f:read("*all")
        f:close()
        return s:gsub("%s+", "")
    end
    return nil
end

local function WriteStatus(s)
    local f = io.open(STATUS_FILE_PATH, "w")
    if f then f:write(s); f:close() end
end

local function Tick()
    local status = ReadStatus()
    
    if status and status:find('"status":"REQUEST_MANUAL"') then
        print("[TalonDataset] Python'dan cekim istegi geldi! Hesaplaniyor...")
        
        local talonActor = nil
        pcall(function() talonActor = FindFirstOf("BPP_AIDroneTalon_C") end)
        
        if not talonActor or not talonActor:IsValid() then
            print("[TalonDataset] Hata: Talon bulunamadi!")
            WriteStatus('{"status":"WAITING_START"}')
            return
        end

        local PC = GetActiveController()
        if not PC or not PC:IsValid() then
            print("[TalonDataset] Hata: PlayerController bulunamadi!")
            WriteStatus('{"status":"WAITING_START"}')
            return
        end

        local kp2d, kp3d = BuildKeypointsJSON(PC, talonActor)
        local dLoc = talonActor:K2_GetActorLocation()
        local dRot = talonActor:K2_GetActorRotation()

        local cLoc = {X=0, Y=0, Z=0}
        local cRot = {Pitch=0, Yaw=0, Roll=0}
        local fov = 90.0

        pcall(function()
            local cam = GetCameraActor(PC)
            if cam and cam:IsValid() then
                local cls = StaticFindObject("/Script/Engine.ActorComponent")
                if cls and cls:IsValid() then
                    local comps = cam:K2_GetComponentsByClass(cls)
                    if comps then
                        for i=1, #comps do
                            local c = comps[i]
                            if c and c:IsValid() and (c:GetClass():GetName():find("CameraComponent") or c:GetClass():GetName() == "CameraComponent") then
                                local l = c:K2_GetComponentLocation()
                                local r = c:K2_GetComponentRotation()
                                if l and r then
                                    cLoc = {X=l.X, Y=l.Y, Z=l.Z}
                                    cRot = {Pitch=r.Pitch, Yaw=r.Yaw, Roll=r.Roll}
                                    fov = c.FieldOfView or 90.0
                                end
                                break
                            end
                        end
                    end
                end
            end
        end)

        if cLoc.X == 0 and cLoc.Y == 0 and cLoc.Z == 0 then
            pcall(function()
                if PC.PlayerCameraManager and PC.PlayerCameraManager:IsValid() then
                    local pov = PC.PlayerCameraManager.CameraCachePrivate.POV
                    if pov then
                        cLoc = {X=pov.Location.X, Y=pov.Location.Y, Z=pov.Location.Z}
                        cRot = {Pitch=pov.Rotation.Pitch, Yaw=pov.Rotation.Yaw, Roll=pov.Rotation.Roll}
                        fov = pov.FOV
                    end
                end
            end)
        end

        local sig = string.format(
            [[{"status":"READY_MANUAL","drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f,"keypoints_2d":%s,"keypoints_3d":%s}]],
            dLoc.X, dLoc.Y, dLoc.Z,
            dRot.Pitch, dRot.Yaw, dRot.Roll,
            cLoc.X, cLoc.Y, cLoc.Z,
            cRot.Pitch, cRot.Yaw, cRot.Roll,
            fov, kp2d, kp3d
        )

        WriteStatus(sig)
        print("[TalonDataset] Hesaplama bitti, Python'a READY_MANUAL gonderildi!")
    end
end

LoopAsync(100, Tick)

-- ============================================================================
-- HILE KOMUTLARI (F10 ve Numpad)
-- ============================================================================

local function AdjustCameraRotation(dPitch, dYaw, dRoll)
    local PC = GetActiveController()
    if not PC or not PC:IsValid() then return end
    local cam = GetCameraActor(PC)
    if cam and cam:IsValid() then
        local r = cam:K2_GetActorRotation()
        local newRot = {Pitch = r.Pitch + dPitch, Yaw = r.Yaw + dYaw, Roll = r.Roll + dRoll}
        cam:K2_SetActorRotation(newRot, true)
        pcall(function() PC.ControlRotation = newRot end)
        print(string.format("[TalonDataset] Kamera Aci -> P:%.1f, Y:%.1f, R:%.1f", newRot.Pitch, newRot.Yaw, newRot.Roll))
    end
end

-- Kamerayi kendi ekseninde dondurme
RegisterKeyBind(Key.NUM_FOUR,  {}, function() AdjustCameraRotation(0, -5, 0) end)
RegisterKeyBind(Key.NUM_SIX,   {}, function() AdjustCameraRotation(0,  5, 0) end)
RegisterKeyBind(Key.NUM_SEVEN, {}, function() AdjustCameraRotation(0, 0, -5) end)
RegisterKeyBind(Key.NUM_NINE,  {}, function() AdjustCameraRotation(0, 0,  5) end)
RegisterKeyBind(Key.NUM_EIGHT, {}, function() AdjustCameraRotation(5,  0, 0) end)
RegisterKeyBind(Key.NUM_TWO,   {}, function() AdjustCameraRotation(-5, 0, 0) end)

-- F10: Kamerayi TAM ARKA YONE 30 Metre uzaga isinla (Mukkemmel acidan cekim icin hazirlik)
RegisterKeyBind(Key.F10, {}, function()
    local talonActor = nil
    pcall(function() talonActor = FindFirstOf("BPP_AIDroneTalon_C") end)
    if not talonActor or not talonActor:IsValid() then
        print("[TalonDataset] F10 HATA: Talon bulunamadi!")
        return
    end

    local PC = GetActiveController()
    if not PC or not PC:IsValid() then return end
    local cam = GetCameraActor(PC)
    if not cam or not cam:IsValid() then return end

    local dLoc = talonActor:K2_GetActorLocation()
    local dRot = talonActor:K2_GetActorRotation()
    
    local dist = 3000 -- 30 Metre
    
    -- Kamera drone'un yaw + 180 (tam arkasi)
    local camYaw = dRot.Yaw + 180.0
    if camYaw > 180 then camYaw = camYaw - 360 end
    
    local radYaw = math.rad(camYaw)
    -- Pitch 0 (tam yatay)
    
    local cx = dLoc.X + (dist * math.cos(radYaw))
    local cy = dLoc.Y + (dist * math.sin(radYaw))
    local cz = dLoc.Z
    
    local lookRot = {Pitch = 0.0, Yaw = camYaw, Roll = 0.0}
    
    pcall(function()
        cam:K2_SetActorLocation({X=cx, Y=cy, Z=cz}, false, {}, true)
        cam:K2_SetActorRotation(lookRot, true)
        PC.ControlRotation = lookRot
    end)
    
    -- Eger DebugCamera'da degilsek SpringArm'i sifirla
    pcall(function()
        local cls = StaticFindObject("/Script/Engine.ActorComponent")
        if cls and cls:IsValid() then
            local comps = cam:K2_GetComponentsByClass(cls)
            if comps then
                for i=1, #comps do
                    local c = comps[i]
                    if c and c:IsValid() then
                        local n = c:GetClass():GetName()
                        if n:find("SpringArm") or n:find("CameraBoom") then
                            c.TargetArmLength = 0
                            c.bDoCollisionTest = false
                        end
                    end
                end
            end
        end
    end)

    print("[TalonDataset] F10 HILESI: Kamera mukemmel arka aciya yerlestirildi! (Hazir, '1'e bas)")
end)
