---@meta

---@class ABP_OPSoldier_C : ACharacter
---@field UberGraphFrame FPointerToUberGraphFrame
---@field COL_Interact UCapsuleComponent
---@field Arrow1 UArrowComponent
---@field SM_FPV_View UStaticMeshComponent
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field isDead boolean
---@field OPSoldierDead FBP_OPSoldier_COPSoldierDead
---@field ['GM UAV Base'] AGM_UAVBase_C
local ABP_OPSoldier_C = {}

function ABP_OPSoldier_C:ReceiveBeginPlay() end
---@param Object ABPP_UAV_C
function ABP_OPSoldier_C:InteractDrone(Object) end
---@param BPP_Drone_Base ABPP_UAV_C
function ABP_OPSoldier_C:Interact(BPP_Drone_Base) end
function ABP_OPSoldier_C:CalculateDistance() end
---@param EntryPoint int32
function ABP_OPSoldier_C:ExecuteUbergraph_BP_OPSoldier(EntryPoint) end
function ABP_OPSoldier_C:OPSoldierDead__DelegateSignature() end


