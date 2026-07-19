local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting SafeDump All Components\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local ActorCompClass = StaticFindObject("/Script/Engine.ActorComponent")
    if not ActorCompClass then out:write("ActorCompClass not found!\n") else out:write("ActorCompClass OK\n") end
    
    pcall(function()
        local comps = talon:GetComponentsByClass(ActorCompClass)
        if comps then
            out:write("All components count: " .. tostring(#comps) .. "\n")
            for i=1, #comps do
                local c = comps[i]
                if c and c:IsValid() then
                    local className = "UnknownClass"
                    pcall(function() className = c:GetClass():GetName() end)
                    out:write(" - " .. className .. " | Name: " .. c:GetFName():ToString() .. "\n")
                end
            end
        else
            out:write("comps is nil\n")
        end
    end)
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] All components dumped to Desktop/TalonMeshInfo.txt!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
