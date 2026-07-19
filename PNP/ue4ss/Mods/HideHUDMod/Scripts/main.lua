-- ============================================================================
-- HIDE HUD MOD FOR DRONES OF WAR (UE4SS Lua Script)
-- ============================================================================
print("[HideHUDMod] Loading mod...")

local is_hud_hidden = false

-- Function to hide all UI and HUD elements
local function hide_hud(pc)
    if not pc or not pc:IsValid() then return end

    -- 1) MyHUD.bShowHUD = false
    local pcs = FindAllOf("PlayerController")
    for _, controller in pairs(pcs) do
        if controller:IsValid() then
            local hud = controller.MyHUD
            if hud and hud:IsValid() then
                pcall(function() hud.bShowHUD = false end)
            end
        end
    end

    -- 2) Hide UMG UserWidgets
    local widgets = FindAllOf("UserWidget")
    for _, w in pairs(widgets) do
        if w:IsValid() then
            local name = tostring(w:GetName())
            if not string.find(name, "Default__") then
                pcall(function() w:SetVisibility(2) end) -- Hidden
                pcall(function() w:SetVisibility(3) end) -- Collapsed/Hidden fallback
                pcall(function() w:SetRenderOpacity(0.0) end)
            end
        end
    end

    -- 3) Execute Console Commands to hide HUD/LUI
    pcall(function() pc:ExecuteConsoleCommand("ShowFlag.HUD 0") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("ShowFlag.HUD 0", pc) end)
    pcall(function() pc:ExecuteConsoleCommand("ShowFlag.LUI 0") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("ShowFlag.LUI 0", pc) end)
    pcall(function() pc:ExecuteConsoleCommand("Slate.GameLayer.ViewportSlotVisible 0") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("Slate.GameLayer.ViewportSlotVisible 0", pc) end)
    
    if not is_hud_hidden then
        print("[HideHUDMod] HUD hidden successfully.")
        is_hud_hidden = true
    end
end

-- Function to restore HUD and UMG widgets
local function show_hud(pc)
    if not pc or not pc:IsValid() then return end

    -- 1) MyHUD.bShowHUD = true
    local pcs = FindAllOf("PlayerController")
    for _, controller in pairs(pcs) do
        if controller:IsValid() then
            local hud = controller.MyHUD
            if hud and hud:IsValid() then
                pcall(function() hud.bShowHUD = true end)
            end
        end
    end

    -- 2) Restore UMG UserWidgets
    local widgets = FindAllOf("UserWidget")
    for _, w in pairs(widgets) do
        if w:IsValid() then
            local name = tostring(w:GetName())
            if not string.find(name, "Default__") then
                pcall(function() w:SetVisibility(0) end) -- Visible
                pcall(function() w:SetRenderOpacity(1.0) end)
            end
        end
    end

    -- 3) Execute Console Commands to restore HUD/LUI
    pcall(function() pc:ExecuteConsoleCommand("ShowFlag.HUD 1") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("ShowFlag.HUD 1", pc) end)
    pcall(function() pc:ExecuteConsoleCommand("ShowFlag.LUI 1") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("ShowFlag.LUI 1", pc) end)
    pcall(function() pc:ExecuteConsoleCommand("Slate.GameLayer.ViewportSlotVisible 1") end)
    pcall(function() pc:K2_ExecuteConsoleCommand("Slate.GameLayer.ViewportSlotVisible 1", pc) end)

    if is_hud_hidden then
        print("[HideHUDMod] HUD restored successfully.")
        is_hud_hidden = false
    end
end

-- Periodic check and update function
local function check_and_update_hud()
    local pc = FindFirstOf("PlayerController")
    if not pc or not pc:IsValid() then return end

    local in_drone = false

    -- Check if Player is possessing a Drone Pawn
    local pawn = pc:K2_GetPawn()
    if pawn and pawn:IsValid() then
        local name = tostring(pawn:GetFullName())
        if string.find(string.lower(name), "talon") or string.find(string.lower(name), "aidrone") then
            in_drone = true
        end
    end

    -- Check if Player Camera is viewing the Drone Target
    if not in_drone then
        local cameraManager = pc.PlayerCameraManager
        if cameraManager and cameraManager:IsValid() then
            local viewTarget = cameraManager.ViewTarget
            if viewTarget and viewTarget.Target and viewTarget.Target:IsValid() then
                local name = tostring(viewTarget.Target:GetFullName())
                if string.find(string.lower(name), "talon") or string.find(string.lower(name), "aidrone") then
                    in_drone = true
                end
            end
        end
    end

    -- Handle HUD Visibility transitions
    if in_drone then
        hide_hud(pc)
    else
        if is_hud_hidden then
            show_hud(pc)
        end
    end
end

-- Start Asynchronous Loop (polling every 500ms)
LoopAsync(500, function()
    pcall(check_and_update_hud)
    return false -- Keep the loop running
end)

print("[HideHUDMod] Mod initialized successfully.")
