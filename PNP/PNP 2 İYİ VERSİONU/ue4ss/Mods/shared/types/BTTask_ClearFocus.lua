---@meta

---@class UBTTask_ClearFocus_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
local UBTTask_ClearFocus_C = {}

---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_ClearFocus_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
---@param EntryPoint int32
function UBTTask_ClearFocus_C:ExecuteUbergraph_BTTask_ClearFocus(EntryPoint) end


