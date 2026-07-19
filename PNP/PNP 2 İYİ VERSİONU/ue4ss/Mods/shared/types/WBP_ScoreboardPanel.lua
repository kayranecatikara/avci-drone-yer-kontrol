---@meta

---@class UWBP_ScoreboardPanel_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ScrollBox UScrollBox
local UWBP_ScoreboardPanel_C = {}

---@param FailCrash FString
---@param SuccessCrash FString
---@param TotalCrash FString
---@param Date FString
---@param DateTime FString
---@param TotalTime FString
function UWBP_ScoreboardPanel_C:Notify_Scoreboard(FailCrash, SuccessCrash, TotalCrash, Date, DateTime, TotalTime) end
function UWBP_ScoreboardPanel_C:ClearChildItems() end
---@param Killer FString
---@param WhoDead FString
---@param isNet boolean
---@param isFail boolean
function UWBP_ScoreboardPanel_C:Notify_Killfeed(Killer, WhoDead, isNet, isFail) end
---@param EntryPoint int32
function UWBP_ScoreboardPanel_C:ExecuteUbergraph_WBP_ScoreboardPanel(EntryPoint) end


