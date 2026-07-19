RegisterKeyBind(Key.F9, function()
    local talons = FindAllOf("BPP_AIDroneTalon_C")
    if talons and #talons > 0 then
        local t = talons[1]
        print("====== DRONE EXACT COMPONENT LOCATIONS ======")
        
        local origLoc = t:K2_GetActorLocation()
        
        local tName = tostring(t:GetFName())
        local allMeshes = FindAllOf("StaticMeshComponent")
        if allMeshes then
            for i=1, #allMeshes do
                local c = allMeshes[i]
                if c and c:IsValid() then
                    local fullName = c:GetFullName()
                    if string.find(fullName, tName, 1, true) then
                        local compName = fullName:match("%.([^%.]+)$")
                        
                        -- Just get RelativeLocation directly from the property
                        local relLoc = nil
                        pcall(function() relLoc = c.RelativeLocation end)
                        
                        -- Also get World Location and manually subtract (for unrotated)
                        local worldLoc = nil
                        pcall(function() worldLoc = c:K2_GetComponentLocation() end)
                        
                        if relLoc then
                            print(string.format("COMP: %s", compName))
                            print(string.format("  -> RelativeLocation Property: X=%.2f, Y=%.2f, Z=%.2f", relLoc.X, relLoc.Y, relLoc.Z))
                        elseif worldLoc then
                            local rx = worldLoc.X - origLoc.X
                            local ry = worldLoc.Y - origLoc.Y
                            local rz = worldLoc.Z - origLoc.Z
                            print(string.format("COMP: %s", compName))
                            print(string.format("  -> K2_Loc (World - Root): X=%.2f, Y=%.2f, Z=%.2f", rx, ry, rz))
                        else
                            print("COMP: " .. compName .. " (Location failed)")
                        end
                    end
                end
            end
        end
        print("========================================")
    end
end)
