---@meta

---@class AGM_MainMenu_C : AGameModeBase
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DefaultSceneRoot USceneComponent
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['HUD Main Menu'] AHUD_MainMenu_C
local AGM_MainMenu_C = {}

function AGM_MainMenu_C:GetScoreBoardData() end
---@param Save_Game_Scoreboard UBP_SaveGame_ScoreBoard_C
function AGM_MainMenu_C:LoadGameScoreboard(Save_Game_Scoreboard) end
function AGM_MainMenu_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function AGM_MainMenu_C:ExecuteUbergraph_GM_MainMenu(EntryPoint) end


