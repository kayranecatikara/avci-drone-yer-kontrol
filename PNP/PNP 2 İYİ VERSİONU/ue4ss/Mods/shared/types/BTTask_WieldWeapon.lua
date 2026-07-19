---@meta

---@class UBTTask_WieldWeapon_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
local UBTTask_WieldWeapon_C = {}

---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_WieldWeapon_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
---@param EntryPoint int32
function UBTTask_WieldWeapon_C:ExecuteUbergraph_BTTask_WieldWeapon(EntryPoint) end


