---@meta

---@class FAnimBlueprintGeneratedConstantData : FAnimBlueprintConstantData
---@field __NameProperty_52 FName
---@field __NameProperty_53 FName
---@field __StructProperty_54 FAnimNodeFunctionRef
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystem_PropertyAccess
---@field AnimBlueprintExtension_Base FAnimSubsystem_Base
---@field AnimGraphNode_Root FAnimNodeExposedValueHandler_PropertyAccess
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
---@field AnimGraphNode_ComponentToLocalSpace FAnimNodeExposedValueHandler_PropertyAccess
local FAnimBlueprintGeneratedConstantData = {}



---@class UABP_East_Command_9S552_C : UAnimInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystemInstance
---@field AnimBlueprintExtension_Base FAnimSubsystemInstance
---@field AnimGraphNode_Root FAnimNode_Root
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
---@field AnimGraphNode_ComponentToLocalSpace FAnimNode_ConvertComponentToLocalSpace
---@field ['Front Wheel Rotation'] FRotator
---@field BackWheelRotation FRotator
---@field RotationWindowCleaner FRotator
---@field DoorRotation FRotator
---@field AntennaRotation FRotator
---@field FrontWheelRotation FRotator
---@field BSRotation FRotator
---@field HatchRotation FRotator
---@field WheelSpeedOffset double
---@field WheelSpeed double
---@field WheelAngle double
---@field HatchAngle double
---@field DoorAngle double
---@field BSDoorAngle double
---@field WindowCleanerRotation double
---@field AntennaRotationR double
local UABP_East_Command_9S552_C = {}

---@param AnimGraph FPoseLink
function UABP_East_Command_9S552_C:AnimGraph(AnimGraph) end
---@param DeltaTimeX float
function UABP_East_Command_9S552_C:BlueprintUpdateAnimation(DeltaTimeX) end
---@param Increment double
function UABP_East_Command_9S552_C:UpdateSpeedOffset(Increment) end
function UABP_East_Command_9S552_C:UpdateWheels() end
function UABP_East_Command_9S552_C:UpdateHatches() end
function UABP_East_Command_9S552_C:UpdateDoors() end
UABP_East_Command_9S552_C['Update Back and Side Door'] = function(self, ) end
UABP_East_Command_9S552_C['Update Window Cleaner'] = function(self, ) end
UABP_East_Command_9S552_C['Update Antenna'] = function(self, ) end
function UABP_East_Command_9S552_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_East_Command_9S552_AnimGraphNode_ModifyBone_E461B0544ECBE0AF1A752AB5F4158B59() end
---@param EntryPoint int32
function UABP_East_Command_9S552_C:ExecuteUbergraph_ABP_East_Command_9S552(EntryPoint) end


