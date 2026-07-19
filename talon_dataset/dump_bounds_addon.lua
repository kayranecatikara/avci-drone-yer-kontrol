local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting Bounds Dump\n")
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
            local origin, extent, radius = root:K2_GetComponentBounds()
            out:write("World Bounds Extent: X=" .. tostring(extent.X) .. " Y=" .. tostring(extent.Y) .. " Z=" .. tostring(extent.Z) .. "\n")
            out:write("World Bounds Origin: X=" .. tostring(origin.X) .. " Y=" .. tostring(origin.Y) .. " Z=" .. tostring(origin.Z) .. "\n")
        end)
    end
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Bounds dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
