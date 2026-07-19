---@meta

---@class UBTTask_MoveAlongToSplinePoint_C : UBTTask_BlueprintBase
---@field UberGraphFrame FPointerToUberGraphFrame
local UBTTask_MoveAlongToSplinePoint_C = {}

---@param MovementResult EPathFollowingResult::Type
function UBTTask_MoveAlongToSplinePoint_C:OnFail_6F30BE0248E9C2EDF23B7EAF480DBF56(MovementResult) end
---@param MovementResult EPathFollowingResult::Type
function UBTTask_MoveAlongToSplinePoint_C:OnSuccess_6F30BE0248E9C2EDF23B7EAF480DBF56(MovementResult) end
---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_MoveAlongToSplinePoint_C:ReceiveExecuteAI(OwnerController, ControlledPawn) end
---@param OwnerController AAIController
---@param ControlledPawn APawn
function UBTTask_MoveAlongToSplinePoint_C:ReceiveAbortAI(OwnerController, ControlledPawn) end
---@param EntryPoint int32
function UBTTask_MoveAlongToSplinePoint_C:ExecuteUbergraph_BTTask_MoveAlongToSplinePoint(EntryPoint) end


