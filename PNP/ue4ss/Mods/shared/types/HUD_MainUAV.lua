---@meta

---@class AHUD_MainUAV_C : AHUD
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DefaultSceneRoot USceneComponent
---@field ['WBP Main Drone'] UWBP_MainUAV_C
---@field ['WBP Settings Menu'] UWBP_SettingsMenu_C
---@field ['WBP Spectator'] UWBP_Spectator_C
---@field ['WBP Global UI'] UWBP_GlobalUI_C
---@field ['WBP Completed Level'] UWBP_CompletedLevel_C
---@field ['WBP Score Board'] UWBP_ScoreBoard_C
---@field ['PC Spectator Drone Base'] APC_SpectatorDroneBase_C
local AHUD_MainUAV_C = {}

---@param Show boolean
function AHUD_MainUAV_C:SetShowHideMainDrone(Show) end
---@param Show boolean
function AHUD_MainUAV_C:SetShowHideSpectatorMenu(Show) end
---@param Show boolean
function AHUD_MainUAV_C:ShowHideSettingsMenu(Show) end
---@param isFail boolean
function AHUD_MainUAV_C:SetVisibilityCompletedLevel(isFail) end
function AHUD_MainUAV_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function AHUD_MainUAV_C:ExecuteUbergraph_HUD_MainUAV(EntryPoint) end


