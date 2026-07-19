---@meta

---@class UBTTask_Attack_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
local UBTTask_Attack_C = {}

---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_Attack_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
function UBTTask_Attack_C:FinishedAttack() end
---@param EntryPoint int32
function UBTTask_Attack_C:ExecuteUbergraph_BTTask_Attack(EntryPoint) end


