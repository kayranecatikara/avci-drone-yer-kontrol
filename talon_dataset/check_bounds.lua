local actors = FindAllOf('BPP_AIDroneTalon_C')
if actors and #actors > 0 then
    for _, actor in ipairs(actors) do
        local comp = actor.SM_Talon_Body
        if comp then
            local mesh = comp.StaticMesh
            if mesh then
                print('Found Talon Mesh Bounds!')
                print('Actor Name: ' .. actor:GetFullName())
                print('Mesh Name: ' .. mesh:GetFullName())
            end
        end
    end
end
