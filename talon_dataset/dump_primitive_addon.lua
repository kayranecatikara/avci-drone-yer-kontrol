local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting PrimitiveDump\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local PrimClass = StaticFindObject("/Script/Engine.PrimitiveComponent")
    if not PrimClass then out:write("PrimClass not found!\n") else out:write("PrimClass OK\n") end
    
    pcall(function()
        local comps = talon:GetComponentsByClass(PrimClass)
        if comps then
            out:write("Primitive components count: " .. tostring(#comps) .. "\n")
            for i=1, #comps do
                local c = comps[i]
                if c and c:IsValid() then
                    local className = "UnknownClass"
                    pcall(function() className = c:GetClass():GetName() end)
                    out:write(" - " .. className .. " | Name: " .. c:GetFName():ToString() .. "\n")
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
        else
            out:write("comps is nil\n")
        end
    end)
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Primitive components dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
