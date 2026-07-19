local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting Hierarchy Dump\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local root = talon.RootComponent
    if not root or not root:IsValid() then
        out:write("RootComponent not found.\n")
        out:close()
        return
    end
    out:write("Root: " .. root:GetFName():ToString() .. "\n")
    
    local function dumpChildren(comp, indent)
        if not comp or not comp:IsValid() then return end
        pcall(function()
            local sn = comp:GetAllSocketNames()
            if #sn > 0 then
                out:write(indent .. " - Sockets: " .. tostring(#sn) .. "\n")
                for _, s in ipairs(sn) do
                    out:write(indent .. "   > " .. s:ToString() .. "\n")
                end
            end
        end)
        pcall(function()
            local num = comp:GetNumBones()
            if num > 0 then
                out:write(indent .. " - Bones: " .. tostring(num) .. "\n")
                for i=0, num-1 do
                    out:write(indent .. "   > " .. comp:GetBoneName(i):ToString() .. "\n")
                end
            end
        end)
        
        local children = nil
        pcall(function() children = comp:GetAttachChildren() end)
        if children then
            for i=1, #children do
                local child = children[i]
                if child and child:IsValid() then
                    local cname = "Unknown"
                    local clsname = "UnknownClass"
                    pcall(function() cname = child:GetFName():ToString() end)
                    pcall(function() clsname = child:GetClass():GetName() end)
                    out:write(indent .. "-> Child: " .. cname .. " [" .. clsname .. "]\n")
                    dumpChildren(child, indent .. "  ")
                end
            end
        end
    end
    
    dumpChildren(root, "  ")
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Hierarchy dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
