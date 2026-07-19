local function DumpTalonMeshInfo()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshInfo.txt", "w")
    if not out then return end
    
    out:write("Starting Actor Bounds Dump\n")
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    out:write("Found Talon: " .. talon:GetFName():ToString() .. "\n")
    
    pcall(function()
        local origin, extent = talon:GetActorBounds(false)
        out:write("ActorBounds Origin: X=" .. tostring(origin.X) .. " Y=" .. tostring(origin.Y) .. " Z=" .. tostring(origin.Z) .. "\n")
        out:write("ActorBounds Extent: X=" .. tostring(extent.X) .. " Y=" .. tostring(extent.Y) .. " Z=" .. tostring(extent.Z) .. "\n")
    end)
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Actor bounds dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpTalonMeshInfo()
end)
