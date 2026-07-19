---@meta

---@class ABP_MainOPSoldier_C : ACharacter
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SM_Tripod UStaticMeshComponent
---@field SM_GroundControl1 UStaticMeshComponent
---@field SM_FPV_View UStaticMeshComponent
local ABP_MainOPSoldier_C = {}

function ABP_MainOPSoldier_C:ReceiveBeginPlay() end
---@param OverlappedComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param OtherBodyIndex int32
---@param bFromSweep boolean
---@param SweepResult FHitResult
function ABP_MainOPSoldier_C:BndEvt__BP_MainOPSoldier_CapsuleComponent_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult) end
---@param EntryPoint int32
function ABP_MainOPSoldier_C:ExecuteUbergraph_BP_MainOPSoldier(EntryPoint) end


