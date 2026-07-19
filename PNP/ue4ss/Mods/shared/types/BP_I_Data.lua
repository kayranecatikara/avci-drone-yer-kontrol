---@meta

---@class IBP_I_Data_C : IInterface
local IBP_I_Data_C = {}

---@param FailCrash FString
---@param SuccessCrash FString
---@param TotalCrash FString
---@param Date FString
---@param DateTime FString
---@param TotalTime FString
function IBP_I_Data_C:Notify_Scoreboard(FailCrash, SuccessCrash, TotalCrash, Date, DateTime, TotalTime) end
---@param Killer FString
---@param WhoDead FString
---@param isNet boolean
---@param isFail boolean
function IBP_I_Data_C:Notify_Killfeed(Killer, WhoDead, isNet, isFail) end


