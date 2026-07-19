local function DumpMeshBounds()
    local out = io.open("C:\\Users\\Zeylo\\Desktop\\TalonMeshBounds.txt", "w")
    if not out then return end
    
    local talon = FindFirstOf("BPP_AIDroneTalon_C")
    if not talon or not talon:IsValid() then
        out:write("Talon not found.\n")
        out:close()
        return
    end
    
    local root = talon.RootComponent
    if not root or not root:IsValid() then
        out:write("Root not found.\n")
        out:close()
        return
    end
    
    local mesh = root.StaticMesh
    if not mesh or not mesh:IsValid() then
        out:write("StaticMesh not found on RootComponent.\n")
        out:close()
        return
    end
    
    out:write("Found StaticMesh: " .. mesh:GetFName():ToString() .. "\n")
    
    -- In Unreal Engine, UStaticMesh has a 'ExtendedBounds' or 'PositiveBounds' property
    local props = mesh:GetProperties()
    for _, prop in ipairs(props) do
        out:write("Prop: " .. prop:GetName() .. "\n")
    end
    
    pcall(function()
        local bounds = mesh.ExtendedBounds
        if bounds then
            out:write("ExtendedBounds Origin: " .. tostring(bounds.Origin.X) .. ", " .. tostring(bounds.Origin.Y) .. ", " .. tostring(bounds.Origin.Z) .. "\n")
            out:write("ExtendedBounds BoxExtent: " .. tostring(bounds.BoxExtent.X) .. ", " .. tostring(bounds.BoxExtent.Y) .. ", " .. tostring(bounds.BoxExtent.Z) .. "\n")
        end
    end)
    pcall(function()
        local bounds = mesh.PositiveBounds
        if bounds then
            out:write("PositiveBounds Extent: " .. tostring(bounds.X) .. ", " .. tostring(bounds.Y) .. ", " .. tostring(bounds.Z) .. "\n")
        end
    end)
    
    out:write("DUMP COMPLETE!\n")
    out:close()
    print("[TalonDumper] Mesh bounds dumped!")
end

RegisterKeyBind(Key.F9, function()
    DumpMeshBounds()
end)
