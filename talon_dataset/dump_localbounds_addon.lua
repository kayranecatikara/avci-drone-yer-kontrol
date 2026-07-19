local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting Local Bounds Dump\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    local root = talon.RootComponent
    if root and root:IsValid() then
        out:write("Root: " .. root:GetFName():ToString() .. "\n")
        
        pcall(function()
            local minLoc, maxLoc = root:GetLocalBounds()
            out:write("LocalBounds Min: X=" .. tostring(minLoc.X) .. " Y=" .. tostring(minLoc.Y) .. " Z=" .. tostring(minLoc.Z) .. "\n")
            out:write("LocalBounds Max: X=" .. tostring(maxLoc.X) .. " Y=" .. tostring(maxLoc.Y) .. " Z=" .. tostring(maxLoc.Z) .. "\n")
        end)
    end
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Local bounds dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
