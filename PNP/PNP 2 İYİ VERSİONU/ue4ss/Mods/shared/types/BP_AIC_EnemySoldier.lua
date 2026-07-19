---@meta

---@class ABP_AIC_EnemySoldier_C : AAIController
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AttackTargetKeyName FName
---@field StateKeyName FName
---@field SoldierState E_AI_EnemySoldierState::Type
local ABP_AIC_EnemySoldier_C = {}

function ABP_AIC_EnemySoldier_C:SetStateAsRunback() end
function ABP_AIC_EnemySoldier_C:SetStateAsDead() end
---@param AttackTarget AActor
function ABP_AIC_EnemySoldier_C:SetStateAsCombat(AttackTarget) end
function ABP_AIC_EnemySoldier_C:SetStateAsPassive() end
---@param PossessedPawn APawn
function ABP_AIC_EnemySoldier_C:ReceivePossess(PossessedPawn) end
---@param EntryPoint int32
function ABP_AIC_EnemySoldier_C:ExecuteUbergraph_BP_AIC_EnemySoldier(EntryPoint) end


