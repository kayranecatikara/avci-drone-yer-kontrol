print("[TalonSimple] Loaded")

local function find_talon()
    local drones = FindAllOf("BPP_AIDroneTalon_C") or {}
    for i = 1, #drones do
        local d = drones[i]
        if d and d:IsValid() then
            local isDestroying = false
            pcall(function() isDestroying = d.bActorIsBeingDestroyed end)
            local name = ""
            pcall(function() name = d:GetName() end)
            
            if not isDestroying and not name:find("Default__") then
                return d
            end
        end
    end
    return nil
end

local function slomo(speed)
    pcall(function()
        local PC = FindFirstOf("PlayerController")
        if PC and PC:IsValid() then
            PC:ConsoleCommand("slomo " .. tostring(speed), true)
        end
    end)
end

local function move(dx,dy,dz)
    slomo(0.05) -- Use 0.05 so graphics update!
    local t=find_talon()
    if t==nil then return end

    local loc=t:K2_GetActorLocation()
    loc.X=loc.X+dx
    loc.Y=loc.Y+dy
    loc.Z=loc.Z+dz

    t:K2_SetActorLocation(loc,false,{},true)
end

local function rot(dp,dy,dr)
    slomo(0.05) -- Use 0.05 so graphics update!
    local t=find_talon()
    if t==nil then return end

    local r=t:K2_GetActorRotation()
    r.Pitch=r.Pitch+dp
    r.Yaw=r.Yaw+dy
    r.Roll=r.Roll+dr

    t:K2_SetActorRotation(r,true)
end

RegisterConsoleCommandHandler("talon_up",function(cmd,params) move(0,0,300); return true end)
RegisterConsoleCommandHandler("talon_down",function(cmd,params) move(0,0,-300); return true end)
RegisterConsoleCommandHandler("talon_left",function(cmd,params) move(0,-300,0); return true end)
RegisterConsoleCommandHandler("talon_right",function(cmd,params) move(0,300,0); return true end)
RegisterConsoleCommandHandler("talon_forward",function(cmd,params) move(300,0,0); return true end)
RegisterConsoleCommandHandler("talon_back",function(cmd,params) move(-300,0,0); return true end)

RegisterConsoleCommandHandler("talon_pitch",function(cmd,params) rot(15,0,0); return true end)
RegisterConsoleCommandHandler("talon_yaw",function(cmd,params) rot(0,15,0); return true end)
RegisterConsoleCommandHandler("talon_roll",function(cmd,params) rot(0,0,15); return true end)
RegisterConsoleCommandHandler("talon_reset_time",function(cmd,params) slomo(1); return true end)