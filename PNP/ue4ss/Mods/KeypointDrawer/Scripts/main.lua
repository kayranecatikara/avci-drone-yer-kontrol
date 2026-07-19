local targetClass = "BPP_AIDroneTalon_C"

RegisterHook("/Script/Engine.HUD:ReceiveDrawHUD", function(self, SizeX, SizeY)
    local drones = FindAllOf(targetClass)
    if drones and #drones > 0 then
        local target = drones[1]
        local droneLoc = target:K2_GetActorLocation()
        
        local PC = FindFirstOf("PlayerController")
        if not PC or not PC:IsValid() then return end
        
        local camManager = PC.PlayerCameraManager
        if not camManager or not camManager:IsValid() then return end
        
        local camLoc = camManager:GetCameraLocation()
        
        local dx = droneLoc.X - camLoc.X
        local dy = droneLoc.Y - camLoc.Y
        local dz = droneLoc.Z - camLoc.Z
        local dist_cm = math.sqrt(dx*dx + dy*dy + dz*dz)
        local dist_m = dist_cm / 100.0
        
        local hud = self:get()
        local text = string.format("HEDEF MESAFESI: %.2f Metre", dist_m)
        hud:DrawText(text, {R=0, G=1, B=0, A=1}, 50, 50, nil, 2.0, false)
    end
end)