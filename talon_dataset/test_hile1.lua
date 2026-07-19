-- ============================================================================
-- HILE 1 TEST - ProjectWorldLocationToScreen Signature Testi
-- Bu scripti UE4SS Lua konsoluna yapistir ve calistir
-- ============================================================================

local function TestProjection()
    local PC = FindFirstOf("PlayerController")
    if not PC or not PC:IsValid() then
        print("[HILE1 TEST] PlayerController bulunamadi!")
        return
    end
    print("[HILE1 TEST] PlayerController bulundu: " .. tostring(PC:GetClass():GetName()))

    -- Test dunya konumu: mevcut avcinin bulundugu yer
    local testLoc = {X = 0, Y = 0, Z = 0}
    pcall(function()
        local pawn = PC:K2_GetPawn()
        if pawn and pawn:IsValid() then
            testLoc = pawn:K2_GetActorLocation()
            print(string.format("[HILE1 TEST] Pawn konumu: X=%.1f Y=%.1f Z=%.1f", testLoc.X, testLoc.Y, testLoc.Z))
        end
    end)

    -- Signature 1: (FVector, bool) -> (FVector2D, bool)
    print("[HILE1 TEST] Signature 1 deneniyor...")
    local ok1 = false
    pcall(function()
        local screenPos, bOnScreen = PC:ProjectWorldLocationToScreen(
            { X = testLoc.X, Y = testLoc.Y, Z = testLoc.Z },
            false
        )
        if screenPos then
            local sx = screenPos.X or "?"
            local sy = screenPos.Y or "?"
            print(string.format("[HILE1 TEST] Signature 1 BASARILI! ScreenPos: x=%s y=%s onScreen=%s", tostring(sx), tostring(sy), tostring(bOnScreen)))
            ok1 = true
        else
            print("[HILE1 TEST] Signature 1: screenPos nil geldi")
        end
    end)

    if not ok1 then
        -- Signature 2: (float x, float y, float z, bool) -> (float sx, float sy, bool)
        print("[HILE1 TEST] Signature 2 deneniyor...")
        pcall(function()
            local sx, sy, bon = PC:ProjectWorldLocationToScreen(testLoc.X, testLoc.Y, testLoc.Z, false)
            print(string.format("[HILE1 TEST] Signature 2 sonuc: sx=%s sy=%s on=%s", tostring(sx), tostring(sy), tostring(bon)))
        end)
    end

    -- Ayrica PlayerCameraManager.ProjectWorldLocationToScreen dene
    print("[HILE1 TEST] PlayerCameraManager yolu deneniyor...")
    pcall(function()
        if PC.PlayerCameraManager and PC.PlayerCameraManager:IsValid() then
            local pcm = PC.PlayerCameraManager
            print("[HILE1 TEST] PlayerCameraManager bulundu: " .. tostring(pcm:GetClass():GetName()))
        else
            print("[HILE1 TEST] PlayerCameraManager yok!")
        end
    end)
end

TestProjection()
print("[HILE1 TEST] Test tamamlandi. UE4SS loguna bak.")
