---@meta

---@class AHUD_MainMenu_C : AHUD
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DefaultSceneRoot USceneComponent
---@field ['WBP Main Menu'] UWBP_MainMenu_C
---@field ['WBP Loading Screen'] UWBP_LoadingScreenSelf_C
---@field ['WBP Level Selection'] UWBP_LevelSelection_C
---@field ['WBP Drone Selection'] UWBP_UAVSelection_C
---@field ['WBP Control Menu'] UWBP_ControlMenu_C
---@field ['WBP Scoreboard Base'] UWBP_ScoreboardBase_C
---@field ['WBP Press Any Button'] UWBP_PressAnyButton_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['WBP Settings Menu'] UWBP_SettingsMenu_C
local AHUD_MainMenu_C = {}

---@param Show boolean
function AHUD_MainMenu_C:SetVisiblityLoadingScreen(Show) end
---@param Show boolean
function AHUD_MainMenu_C:SetVisibilityLevelSelection(Show) end
---@param Show boolean
function AHUD_MainMenu_C:SetVisibilityDroneSelection(Show) end
---@param Show boolean
function AHUD_MainMenu_C:SetVisibilityControlMenu(Show) end
---@param Show boolean
function AHUD_MainMenu_C:SetVisibilityMainMenu(Show) end
function AHUD_MainMenu_C:ReceiveBeginPlay() end
---@param Show boolean
function AHUD_MainMenu_C:SetShowHideScoreboardInformation(Show) end
---@param Show boolean
function AHUD_MainMenu_C:SetVisibilitySettingsMenu(Show) end
---@param EntryPoint int32
function AHUD_MainMenu_C:ExecuteUbergraph_HUD_MainMenu(EntryPoint) end


