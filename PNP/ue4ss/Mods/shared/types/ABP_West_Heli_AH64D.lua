---@meta

---@class FAnimBlueprintGeneratedConstantData : FAnimBlueprintConstantData
---@field __NameProperty_52 FName
---@field __NameProperty_53 FName
---@field __StructProperty_54 FAnimNodeFunctionRef
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystem_PropertyAccess
---@field AnimBlueprintExtension_Base FAnimSubsystem_Base
---@field AnimGraphNode_Root FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ComponentToLocalSpace FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_MeshRefPose FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_14 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_13 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_12 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_11 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_10 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_9 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_8 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_7 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_6 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_5 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_4 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_3 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_2 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone FAnimNodeExposedValueHandler_PropertyAccess
local FAnimBlueprintGeneratedConstantData = {}



---@class UABP_West_Heli_AH64D_C : UAnimInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystemInstance
---@field AnimBlueprintExtension_Base FAnimSubsystemInstance
---@field AnimGraphNode_Root FAnimNode_Root
---@field AnimGraphNode_ComponentToLocalSpace FAnimNode_ConvertComponentToLocalSpace
---@field AnimGraphNode_MeshRefPose FAnimNode_MeshSpaceRefPose
---@field AnimGraphNode_ModifyBone_14 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_13 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_12 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_11 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_10 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_9 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_8 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_7 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_6 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_5 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_4 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_3 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_2 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_1 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone FAnimNode_ModifyBone
---@field DoorAngle double
---@field TurretAngle double
---@field GunElevation double
---@field MainRotorSpeed double
---@field MainRotorFlapsAngle double
---@field TailRotorSpeed double
---@field TailRotorFlapsAngle double
---@field TailStabilizerAngle double
---@field RotorSpeedOffset double
---@field MainRotorRotation FRotator
---@field TailRotorRotation FRotator
---@field MainRotorFlapsRotation FRotator
---@field TailRotorFlapsRotation FRotator
---@field DoorsRotation FRotator
---@field TurretRotation FRotator
---@field GunRotation FRotator
---@field TailStabilizerRotation FRotator
local UABP_West_Heli_AH64D_C = {}

---@param AnimGraph FPoseLink
function UABP_West_Heli_AH64D_C:AnimGraph(AnimGraph) end
function UABP_West_Heli_AH64D_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_EF77F2124AFCA26EC5C2EF86C32D9FB7() end
function UABP_West_Heli_AH64D_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_E8034E944B62D71795AADD9159CD1395() end
function UABP_West_Heli_AH64D_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_34DAF2C34C1D24338F0ACAB3312F1B33() end
function UABP_West_Heli_AH64D_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_F92F228E463D43DF0DDF0A8C60518E98() end
---@param DeltaTimeX float
function UABP_West_Heli_AH64D_C:BlueprintUpdateAnimation(DeltaTimeX) end
---@param Increment double
function UABP_West_Heli_AH64D_C:UpdateSpeedOffset(Increment) end
function UABP_West_Heli_AH64D_C:UpdateRotorSpeed() end
function UABP_West_Heli_AH64D_C:UpdateDoors() end
function UABP_West_Heli_AH64D_C:UpdateFlaps() end
function UABP_West_Heli_AH64D_C:UpdateTurret() end
function UABP_West_Heli_AH64D_C:UpdateTailStabilizer() end
---@param EntryPoint int32
function UABP_West_Heli_AH64D_C:ExecuteUbergraph_ABP_West_Heli_AH64D(EntryPoint) end


