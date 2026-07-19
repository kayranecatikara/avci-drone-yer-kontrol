-- ============================================================================
-- AVCI DRONE GERCEK FOV OKUYUCU - UE4SS Lua Mod
-- Avci (oyuncu) dronun kamerasinin FOV'unu oyundan CANLI okur.
--
-- KULLANIM:
--   1) Bu dosyayi UE4SS Mods klasorune bir mod olarak koy (main.lua olarak).
--   2) Oyunu ac, avci droneu NORMAL ucus gorunumunde uc.
--      ONEMLI: "E" ile serbest/debug kameraya GECME! Debug kamera FOV'u (123)
--      avci dronun gercek kamerasi DEGILDIR.
--   3) F8'e bas. FOV degerleri hem UE4SS konsoluna yazilir hem de
--      c:\Users\Zeylo\Desktop\talon_dataset\avci_fov.txt dosyasina kaydedilir.
-- ============================================================================

local OUT = "c:\\Users\\Zeylo\\Desktop\\Drones of War Teknofest\\avci_fov.txt"

local function writeOut(s)
    local f = io.open(OUT, "w")
    if f then f:write(s); f:close() end
    print("[AvciFOV] " .. s)
end

local function getPC()
    local PC = FindFirstOf("PlayerController")
    return PC
end

local function safeOwnerAddr(comp)
    local a = nil
    pcall(function() a = comp:GetOwner():GetAddress() end)
    return a
end

local function readFOV()
    local PC = getPC()
    if not PC or not PC:IsValid() then
        writeOut("HATA: PlayerController bulunamadi.")
        return
    end

    -- 1) Kontrol edilen avci drone (pawn) ve sinif adi
    local pawn = PC:K2_GetPawn()
    local pawnName, pawnAddr = "?", nil
    if pawn and pawn:IsValid() then
        pcall(function() pawnName = pawn:GetClass():GetName() end)
        pawnAddr = pawn:GetAddress()
    end

    -- 2) Aktif kameranin EFEKTIF FOV'u (gercekten render edilen aci)
    local effFov = -1
    if PC.PlayerCameraManager and PC.PlayerCameraManager:IsValid() then
        pcall(function() effFov = PC.PlayerCameraManager:GetFOVAngle() end)
    end

    -- 3) View target (kameranin bagli oldugu actor)
    local vtName = "?"
    pcall(function()
        local vt = PC:GetViewTarget()
        if vt and vt:IsValid() then vtName = vt:GetClass():GetName() end
    end)

    -- 4) Avci dronun CameraComponent.FieldOfView (tasarim/blueprint degeri)
    local designFov, camName = -1, "?"
    local cams = FindAllOf("CameraComponent") or {}
    -- once pawn'a ait kamerayi ara
    for _, c in ipairs(cams) do
        if c and c:IsValid() then
            local oa = safeOwnerAddr(c)
            if pawnAddr and oa == pawnAddr then
                pcall(function() designFov = c.FieldOfView end)
                pcall(function() camName = c:GetName() end)
            end
        end
    end
    -- bulunamadiysa ilk gecerli kamerayi raporla (genelde tek kamera olur)
    if designFov < 0 then
        for _, c in ipairs(cams) do
            if c and c:IsValid() then
                local fv = -1
                pcall(function() fv = c.FieldOfView end)
                if fv and fv > 0 then
                    designFov = fv
                    pcall(function() camName = c:GetName() .. " (sahipsiz/ilk bulunan)" end)
                    break
                end
            end
        end
    end

    local msg = string.format(
        "=== AVCI DRONE FOV ===\n" ..
        "Pawn (avci drone sinifi) : %s\n" ..
        "View target              : %s\n" ..
        "Camera component         : %s\n" ..
        "--------------------------------------------\n" ..
        "EFEKTIF FOV (GetFOVAngle): %.4f derece   <-- DATASETTE BUNU KULLAN\n" ..
        "TASARIM FOV (FieldOfView): %.4f derece\n" ..
        "--------------------------------------------\n" ..
        "Ikisi farkliysa EFEKTIF olan gercek render edilen acidir.\n" ..
        "Bu FOV ile dataset cek: debug kamerada konsola 'FOV %.1f' yazarak\n" ..
        "serbest kamerayi ayni acya sabitleyebilirsin.",
        pawnName, vtName, camName, effFov, designFov, effFov
    )
    writeOut(msg)
end

-- F8'e bas -> oku
RegisterKeyBind(Key.F8, function()
    readFOV()
end)

print("[AvciFOV] Hazir. Avci droneu NORMAL gorunumde ucururken F8'e bas.")
print("[AvciFOV] Sonuc: " .. OUT)
