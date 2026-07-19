---@meta

---@class UBTTask_SetMovementSpeed_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Speed E_AI_EnemySoldierMovementSpeed::Type
local UBTTask_SetMovementSpeed_C = {}

---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_SetMovementSpeed_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
---@param EntryPoint int32
function UBTTask_SetMovementSpeed_C:ExecuteUbergraph_BTTask_SetMovementSpeed(EntryPoint) end


