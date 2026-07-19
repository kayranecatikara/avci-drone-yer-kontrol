---@meta

---@class UBTTask_FocusToTarget_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AttackTargetKey FBlackboardKeySelector
local UBTTask_FocusToTarget_C = {}

---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_FocusToTarget_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
---@param EntryPoint int32
function UBTTask_FocusToTarget_C:ExecuteUbergraph_BTTask_FocusToTarget(EntryPoint) end


