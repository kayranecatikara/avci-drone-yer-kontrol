-- ============================================================================
-- TalonRearShot  -  ZAMANI DURDUR + serbest kamerayi hedefin 5m ARKASINA koy + cek
-- ----------------------------------------------------------------------------
-- KULLANIM:
--   1) Oyunda "E" ile SERBEST/DEBUG kameraya gec (drone'a DOKUNMUYORUZ).
--   2) F7'ye bas. Sirayla:
--        a) ZAMANI DURDURUR (pause) -> arac da kamera da DONAR, hicbir sey dusmez.
--        b) Donmus aracin KENDI yonune gore 5m ARKASINA (kuyrugu arkasi), ayni
--           yukseklige serbest kamerayi koyar, araca dik (yere paralel) baktirir.
--        c) Goruntunun guncellenmesi icin ~1 kare ac/kapa yapar (fark edilmez).
--        d) GERCEK POV+FOV okuyup rearshot_status.txt'ye yazar; Python yakalar.
--        e) 6 sn sonra zamani geri baslatir.
-- ============================================================================

local STATUS  = "c:\\Users\\Zeylo\\Desktop\\talon_dataset\\rearshot_status.txt"
local BACK_CM = 500.0   -- 5 metre

local function writeStatus(s) local f = io.open(STATUS, "w"); if f then f:write(s); f:close() end end
local function runCmd(cmd) pcall(function() ExecuteConsoleCommand(cmd) end) end

local function getActiveController()
    local dbg = FindFirstOf("DebugCameraController")
    if dbg and dbg:IsValid() then return dbg, true end
    return FindFirstOf("PlayerController"), false
end

local function getViewActor(PC)
    if not PC or not PC:IsValid() then return nil end
    local vt = PC:GetViewTarget()
    if vt and vt:IsValid() then return vt end
    return PC:K2_GetPawn()
end

local function findTalon()
    local drones = FindAllOf("BPP_AIDroneTalon_C") or {}
    for i = 1, #drones do
        local d = drones[i]
        if d and d:IsValid() then
            local n = ""; pcall(function() n = d:GetName() end)
            if n and not n:find("Default__") then return d end
        end
    end
    return nil
end

local function setGamePaused(p)
    pcall(function()
        local PC = getActiveController()
        if not PC or not PC:IsValid() then return end
        local GS = StaticFindObject("/Script/Engine.Default__GameplayStatics")
        if GS and GS:IsValid() then GS:SetGamePaused(PC, p) else PC:SetPause(p) end
    end)
end

local function doRearShot()
    local talon = findTalon()
    if not talon then print("[RearShot] HATA: Talon bulunamadi."); return end

    local PC, isDebug = getActiveController()
    if not PC or not PC:IsValid() then print("[RearShot] HATA: kontrolcu yok."); return end
    if not isDebug then
        print("[RearShot] UYARI: Serbest/debug kamera AKTIF DEGIL! Once oyunda 'E'ye bas, sonra F7.")
    end

    runCmd("r.SetRes 1920x1080w")
    runCmd("ShowFlag.HUD 0"); runCmd("ShowFlag.Slate 0"); runCmd("ShowFlag.LUI 0")

    -- (a) ZAMANI DURDUR: arac ve kamera aninda donar, hicbir sey dusmez/kaymaz
    setGamePaused(true)

    -- Donmus aracin pozuna gore hedef kamera pozu (5m arkasi, ayni yukseklik, dik bakis)
    local L = talon:K2_GetActorLocation()
    local R = talon:K2_GetActorRotation()
    local yawRad = math.rad(R.Yaw)
    local pos = { X = L.X - BACK_CM * math.cos(yawRad), Y = L.Y - BACK_CM * math.sin(yawRad), Z = L.Z }
    local rot = { Pitch = 0.0, Yaw = R.Yaw, Roll = 0.0 }

    local function place()
        pcall(function() PC.ControlRotation = rot end)
        local cam = getViewActor(PC)
        if cam and cam:IsValid() then
            pcall(function() cam:K2_SetActorLocation(pos, false, {}, true) end)
            pcall(function() cam:K2_SetActorRotation(rot, true) end)
        end
        pcall(function() PC:K2_SetActorLocation(pos, false, {}, true) end)
    end

    -- (b) Kamerayi yerlestir (pause'dayken)
    place()
    print(string.format("[RearShot] Hedef kamera pos=(%.1f,%.1f,%.1f) yaw=%.1f (drone yaw=%.1f)", pos.X, pos.Y, pos.Z, rot.Yaw, R.Yaw))

    -- (c) Goruntu guncellensin diye ~1 kare ac/kapa (fark edilmez, dusme olmaz)
    ExecuteWithDelay(60, function()
        setGamePaused(false)
        place()
        ExecuteWithDelay(60, function()
            setGamePaused(true)
            place()

            -- (d) GERCEK POV+FOV oku, status yaz
            ExecuteWithDelay(150, function()
                local pc2 = getActiveController()
                local fov = -1.0
                local cl, cr = pos, rot
                pcall(function()
                    if pc2 and pc2.PlayerCameraManager and pc2.PlayerCameraManager:IsValid() then
                        local f = pc2.PlayerCameraManager:GetFOVAngle()
                        if f and f > 0 then fov = f end
                        local cache = pc2.PlayerCameraManager.CameraCachePrivate
                        if cache and cache.POV then
                            local pov = cache.POV
                            if pov.Location then cl = { X = pov.Location.X, Y = pov.Location.Y, Z = pov.Location.Z } end
                            if pov.Rotation then cr = { Pitch = pov.Rotation.Pitch, Yaw = pov.Rotation.Yaw, Roll = pov.Rotation.Roll } end
                            if (fov <= 0) and pov.FOV and pov.FOV > 0 then fov = pov.FOV end
                        end
                    end
                end)
                local dl = talon:K2_GetActorLocation()
                local dr = talon:K2_GetActorRotation()
                writeStatus(string.format(
                    [[{"status":"READY","index":1,"drone_location":{"x":%.2f,"y":%.2f,"z":%.2f},"drone_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_location":{"x":%.2f,"y":%.2f,"z":%.2f},"camera_rotation":{"pitch":%.2f,"yaw":%.2f,"roll":%.2f},"camera_fov":%.2f}]],
                    dl.X, dl.Y, dl.Z, dr.Pitch, dr.Yaw, dr.Roll,
                    cl.X, cl.Y, cl.Z, cr.Pitch, cr.Yaw, cr.Roll, fov))
                print(string.format("[RearShot] READY. POV pos=(%.1f,%.1f,%.1f) rot=(%.1f,%.1f,%.1f) fov=%.2f", cl.X, cl.Y, cl.Z, cr.Pitch, cr.Yaw, cr.Roll, fov))

                -- (e) 6 sn sonra zamani geri baslat
                ExecuteWithDelay(6000, function()
                    setGamePaused(false)
                    runCmd("ShowFlag.HUD 1"); runCmd("ShowFlag.Slate 1"); runCmd("ShowFlag.LUI 1")
                    print("[RearShot] Zaman geri baslatildi.")
                end)
            end)
        end)
    end)
end

RegisterKeyBind(Key.F7, doRearShot)
print("[RearShot] Hazir. Once 'E' ile SERBEST kameraya gec, hedefi gor, sonra F7.")
