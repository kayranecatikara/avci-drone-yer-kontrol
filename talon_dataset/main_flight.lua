-- ============================================================================
-- Ozel Ucus ve Cekim Kontrolcusu (Python -> Lua)
-- Avci Drone'u Python tarafindan gonderilen komutlarla ucar, 1 ile cekim yapar.
-- ============================================================================

local STATUS_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\status.txt"
local CONTROL_FILE_PATH = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\control.json"

local KEYPOINTS = {
    {name="Nose",           x= 53.0, y=  0.0,  z=  0.0},
    {name="Left_Wingtip",   x= -4.0, y= 85.9,  z=  0.0},
    {name="Right_Wingtip",  x= -4.0, y=-85.9,  z=  0.0},
    {name="Tail",           x=-55.0, y=  0.0,  z=  0.0},
    {name="Left_Tail_Fin",  x=-75.0, y= 20.0,  z= 22.0},
    {name="Right_Tail_Fin", x=-75.0, y=-20.0,  z= 22.0},
}

local function GetActiveController()
    local PC = FindFirstOf("PlayerController")
    if PC and PC:IsValid() then return PC end
    return nil
end

local function GetCameraActor(PC)
    local vt = PC:GetViewTarget()
    if vt and vt:IsValid() then return vt end
    return PC.Pawn
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

local function ReadFile(path)
    local f = io.open(path, "r")
    if f then 
        local s = f:read("*all")
        f:close()
        return s
    end
    return nil
end

local function WriteFile(path, s)
    local f = io.open(path, "w")
    if f then f:write(s); f:close() end
end

local isFrozen = false

local function Tick()
    local PC = GetActiveController()
    if not PC or not PC:IsValid() then return end
    local avciPawn = PC.Pawn
    
    local controlData = ReadFile(CONTROL_FILE_PATH)
    local statusData = ReadFile(STATUS_FILE_PATH)

    local w, a, s_key, d, f, capture = false, false, false, false, false, false

    if controlData and controlData:find("{") then
        if controlData:find('"w": true') then w = true end
        if controlData:find('"a": true') then a = true end
        if controlData:find('"s": true') then s_key = true end
        if controlData:find('"d": true') then d = true end
        if controlData:find('"f": true') then f = true end
        if controlData:find('"capture": true') then capture = true end
    end

    -- ==========================================
    -- 1) CEKIM VE DONDURMA (CAPTURE FREEZE)
    -- ==========================================
    if capture and not isFrozen then
        print("[TalonDataset] Cekim basladi, oyun donduruluyor...")
        isFrozen = true
        
        -- Zamani dondur
        PC:SetPause(true)
        pcall(function() PC.CustomTimeDilation = 0.0 end)
        if avciPawn and avciPawn:IsValid() then avciPawn.CustomTimeDilation = 0.0 end
        
        local talonActor = nil
        pcall(function() talonActor = FindFirstOf("BPP_AIDroneTalon_C") end)
        
        if talonActor and talonActor:IsValid() then
            talonActor.CustomTimeDilation = 0.0
            
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

            if cLoc.X == 0 then
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
                [[{"status":"READY_CAPTURE","drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f,"keypoints_2d":%s,"keypoints_3d":%s}]],
                dLoc.X, dLoc.Y, dLoc.Z,
                dRot.Pitch, dRot.Yaw, dRot.Roll,
                cLoc.X, cLoc.Y, cLoc.Z,
                cRot.Pitch, cRot.Yaw, cRot.Roll,
                fov, kp2d, kp3d
            )

            WriteFile(STATUS_FILE_PATH, sig)
        else
            print("[TalonDataset] Hata: Talon bulunamadi!")
            WriteFile(STATUS_FILE_PATH, '{"status":"WAITING_START"}')
        end
        return
    end

    if isFrozen then
        -- Eger Python dosyayi WAITING_START yaptiysa (resim cekildiyse), coz.
        if statusData and statusData:find("WAITING_START") then
            print("[TalonDataset] Cekim bitti, oyun cozuluyor...")
            isFrozen = false
            PC:SetPause(false)
            pcall(function() PC.CustomTimeDilation = 1.0 end)
            if avciPawn and avciPawn:IsValid() then avciPawn.CustomTimeDilation = 1.0 end
            
            local talonActor = nil
            pcall(function() talonActor = FindFirstOf("BPP_AIDroneTalon_C") end)
            if talonActor and talonActor:IsValid() then talonActor.CustomTimeDilation = 1.0 end
        end
        return -- Donukken ucus kodunu calistirma
    end

    -- ==========================================
    -- 2) OZEL UCUS KONTROLLERI (AVCI DRONE)
    -- ==========================================
    if not avciPawn or not avciPawn:IsValid() then return end

    -- Hareket hizi ayari
    local moveSpeed = 50.0

    -- W: Yuksel (Z+)
    if w then
        local loc = avciPawn:K2_GetActorLocation()
        avciPawn:K2_SetActorLocation({X=loc.X, Y=loc.Y, Z=loc.Z + moveSpeed}, false, {}, true)
    end

    -- A: Sola Kay (Strafe)
    if a then
        local rgt = avciPawn:GetActorRightVector()
        local loc = avciPawn:K2_GetActorLocation()
        avciPawn:K2_SetActorLocation({
            X = loc.X - (rgt.X * moveSpeed),
            Y = loc.Y - (rgt.Y * moveSpeed),
            Z = loc.Z - (rgt.Z * moveSpeed)
        }, false, {}, true)
    end

    -- D: Saga Kay (Strafe)
    if d then
        local rgt = avciPawn:GetActorRightVector()
        local loc = avciPawn:K2_GetActorLocation()
        avciPawn:K2_SetActorLocation({
            X = loc.X + (rgt.X * moveSpeed),
            Y = loc.Y + (rgt.Y * moveSpeed),
            Z = loc.Z + (rgt.Z * moveSpeed)
        }, false, {}, true)
    end

    -- F: Irtifa Sabitle (Havada Asili Kal) - Yercekimi iptal
    if f then
        pcall(function()
            local root = avciPawn.RootComponent
            if root and root:IsValid() then
                root:SetSimulatePhysics(false)
                root:SetEnableGravity(false)
            end
        end)
    end

    -- S: Alcal (Z-)  ->  W'nin birebir tersi: her tick moveSpeed kadar asagi in.
    -- (Eski surum SetSimulatePhysics(true) kullaniyordu; Pawn/Character kok
    --  bileseninde cogu zaman etkisiz kaldigi icin drone "inmiyordu". Artik W ile
    --  ayni yontem (K2_SetActorLocation) kullaniliyor: W calisiyorsa S de calisir.)
    if s_key then
        local loc = avciPawn:K2_GetActorLocation()
        avciPawn:K2_SetActorLocation({X=loc.X, Y=loc.Y, Z=loc.Z - moveSpeed}, false, {}, true)
    end

end

LoopAsync(33, Tick) -- Saniyede ~30 kez (33ms) calisacak
