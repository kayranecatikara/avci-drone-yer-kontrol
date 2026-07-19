---@meta

---@class UWBP_KillFeedPanel_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field VerticalBox_KillFeed UVerticalBox
---@field ['BPP Main Drone'] ABPP_UAV_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['GM  UAV Base'] AGM_UAVBase_C
---@field DTMaps UDataTable
local UWBP_KillFeedPanel_C = {}

---@param Killer FString
---@param WhoDead FString
---@param isNet boolean
---@param isFail boolean
function UWBP_KillFeedPanel_C:Notify_Killfeed(Killer, WhoDead, isNet, isFail) end
function UWBP_KillFeedPanel_C:Construct() end
---@param FailCrash FString
---@param SuccessCrash FString
---@param TotalCrash FString
---@param Date FString
---@param DateTime FString
---@param TotalTime FString
function UWBP_KillFeedPanel_C:Notify_Scoreboard(FailCrash, SuccessCrash, TotalCrash, Date, DateTime, TotalTime) end
---@param EntryPoint int32
function UWBP_KillFeedPanel_C:ExecuteUbergraph_WBP_KillFeedPanel(EntryPoint) end


