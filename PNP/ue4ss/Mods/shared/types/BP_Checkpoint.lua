---@meta

---@class ABP_Checkpoint_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field COL_Interact UBoxComponent
---@field SM_Checkpoint UStaticMeshComponent
---@field DefaultSceneRoot USceneComponent
---@field ['GM UAV Base'] AGM_UAVBase_C
---@field isPassed boolean
local ABP_Checkpoint_C = {}

---@param isCheckpoint boolean
---@param is_Next boolean
function ABP_Checkpoint_C:ChangeSettings(isCheckpoint, is_Next) end
function ABP_Checkpoint_C:ReceiveBeginPlay() end
---@param OverlappedComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param OtherBodyIndex int32
---@param bFromSweep boolean
---@param SweepResult FHitResult
function ABP_Checkpoint_C:BndEvt__BP_Checkpoint_COL_Interact_K2Node_ComponentBoundEvent_0_ComponentBeginOverlapSignature__DelegateSignature(OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult) end
---@param EntryPoint int32
function ABP_Checkpoint_C:ExecuteUbergraph_BP_Checkpoint(EntryPoint) end


