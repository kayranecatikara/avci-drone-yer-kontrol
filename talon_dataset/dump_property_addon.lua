local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting Property Dump\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local names = {"Mesh", "StaticMesh", "TalonMesh", "DroneMesh", "Body", "RootComponent", "DefaultSceneRoot", "PlaneMesh", "StaticMeshComponent", "SkeletalMeshComponent"}
    for _, n in ipairs(names) do
        local c = nil
        local ok, err = pcall(function() c = talon[n] end)
        if ok and c and type(c) == "userdata" and c.IsValid and c:IsValid() then
            out:write("Found Property: " .. n .. "\n")
            pcall(function()
                local sn = c:GetAllSocketNames()
                out:write("   Sockets: " .. tostring(#sn) .. "\n")
                for _, s in ipairs(sn) do
                    out:write("    " .. s:ToString() .. "\n")
                end
            end)
            pcall(function()
                local num = c:GetNumBones()
                out:write("   Bones: " .. tostring(num) .. "\n")
                for i=0, num-1 do
                    out:write("    " .. c:GetBoneName(i):ToString() .. "\n")
                end
            end)
        end
    end
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Properties dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
