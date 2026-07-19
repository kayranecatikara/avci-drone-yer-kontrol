-- ============================================================================
-- DRONE FINDER - UE4SS Lua Mod
-- Function: Dumps all pawns in the game to pawns.txt to find the drone.
-- ============================================================================

print("[DroneFinder] Scanning for all pawns/vehicles...")

local function DumpTarget()
    local PC = FindFirstOf("PlayerController")
    if PC and PC:IsValid() then
        local viewTarget = PC:GetViewTarget()
        local pawn = PC:K2_GetPawn()
        local vtName = "None"
        local pawnName = "None"
        
        if viewTarget and viewTarget:IsValid() then 
            vtName = viewTarget:GetClass():GetName() 
        end
        if pawn and pawn:IsValid() then 
            pawnName = pawn:GetClass():GetName() 
        end
        
        local file = io.open("c:\\Users\\Zeylo\\Desktop\\talon_dataset\\pawns.txt", "w")
        if file then
            file:write("Senin Kameranin Baktigi Sey (ViewTarget): " .. vtName .. "\n")
            file:write("Senin Kontrol Ettigin Sey (Pawn): " .. pawnName .. "\n")
            file:close()
        end
    end
end

LoopAsync(2000, function()
    DumpTarget()
end)


