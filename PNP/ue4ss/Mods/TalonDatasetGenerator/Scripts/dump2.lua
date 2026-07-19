local function SafeDump()
    local file = io.open('C:/Users/Zeylo/Desktop/talon_dataset/sim_vars.txt', 'w')
    if not file then return end
    
    local avci = FindFirstOf('BPP_AvciDrone_C')
    if avci and avci:IsValid() then
        file:write('--- AVCI PROPERTIES ---
')
        for k, v in pairs(avci) do
            local success, val = pcall(function() return tostring(avci[k]) end)
            if success then
                file:write(tostring(k) .. ' = ' .. tostring(val) .. '
')
            end
        end
    end
    
    file:write('--- MPCs ---
')
    local mpcs = FindAllOf('MaterialParameterCollection')
    if mpcs then
        for i, m in ipairs(mpcs) do
            if m and m:IsValid() then
                local success, name = pcall(function() return m:GetName() end)
                if success and name then
                    file:write('MPC: ' .. name .. '
')
                end
            end
        end
    end
    file:close()
end
SafeDump()

