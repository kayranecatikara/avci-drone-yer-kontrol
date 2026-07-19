local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting SafeDump v2\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local SkelClass = StaticFindObject("/Script/Engine.SkeletalMeshComponent")
    if not SkelClass then out:write("SkelClass not found!\n") else out:write("SkelClass OK\n") end
    
    local StaticClass = StaticFindObject("/Script/Engine.StaticMeshComponent")
    if not StaticClass then out:write("StaticClass not found!\n") else out:write("StaticClass OK\n") end
    
    pcall(function()
        local comps = talon:GetComponentsByClass(SkelClass)
        out:write("Skeletal components count: " .. tostring(#comps) .. "\n")
        for _, c in ipairs(comps) do
            out:write(" - " .. c:GetFName():ToString() .. "\n")
            pcall(function()
                local num = c:GetNumBones()
                out:write("   Bones: " .. tostring(num) .. "\n")
                for i=0, num-1 do
                    out:write("    " .. c:GetBoneName(i):ToString() .. "\n")
                end
            end)
            pcall(function()
                local sn = c:GetAllSocketNames()
                out:write("   Sockets: " .. tostring(#sn) .. "\n")
                for _, s in ipairs(sn) do
                    out:write("    " .. s:ToString() .. "\n")
                end
            end)
        end
    end)
    
    pcall(function()
        local comps = talon:GetComponentsByClass(StaticClass)
        out:write("Static components count: " .. tostring(#comps) .. "\n")
        for _, c in ipairs(comps) do
            out:write(" - " .. c:GetFName():ToString() .. "\n")
            pcall(function()
                local sn = c:GetAllSocketNames()
                out:write("   Sockets: " .. tostring(#sn) .. "\n")
                for _, s in ipairs(sn) do
                    out:write("    " .. s:ToString() .. "\n")
                end
            end)
        end
    end)
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Sockets and Bones dumped to Desktop/TalonMeshInfo.txt!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
