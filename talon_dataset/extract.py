import json

longest_lua = ""

try:
    with open(r'C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if 'Talon UAV Dataset Generator - UE4SS Lua Mod' in line:
                data = json.loads(line)
                if 'tool_calls' in data:
                    for tc in data['tool_calls']:
                        if tc.get('name') == 'run_command':
                            cmd = tc.get('args', {}).get('CommandLine', '')
                            if 'Talon UAV Dataset Generator - UE4SS Lua Mod' in cmd:
                                parts = cmd.split('@\"')
                                if len(parts) >= 2:
                                    lua_code = parts[1].split('\"@')[0]
                                    if len(lua_code) > len(longest_lua):
                                        longest_lua = lua_code

    if longest_lua:
        # Apply user modifications
        longest_lua = longest_lua.replace('local MIN_DIST = 200', 'local MIN_DIST = 300')
        longest_lua = longest_lua.replace('local MAX_DIST = 1300', 'local MAX_DIST = 600')
        longest_lua = longest_lua.replace('local MIN_PITCH = -45', 'local MIN_PITCH = 60')
        longest_lua = longest_lua.replace('local MAX_PITCH = 55', 'local MAX_PITCH = 85')
        longest_lua = longest_lua.replace('local calcDist = math.random(1000, 3000)', 'local calcDist = math.random(300, 600)')
        
        with open(r'C:\Users\Zeylo\Desktop\Drones of War Teknofest\DronesOfWar\Binaries\Win64\ue4ss\Mods\TalonDatasetGenerator\Scripts\main.lua', 'w', encoding='utf-8') as out:
            out.write(longest_lua.strip())
        print(f"LUA EXTRACTED AND SAVED! Length: {len(longest_lua)}")
    else:
        print("Not found.")
except Exception as e:
    print(e)
