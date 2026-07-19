---@meta

---@class FAnimBlueprintGeneratedConstantData : FAnimBlueprintConstantData
---@field __NameProperty_58 FName
---@field __NameProperty_59 FName
---@field __StructProperty_60 FAnimNodeFunctionRef
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystem_PropertyAccess
---@field AnimBlueprintExtension_Base FAnimSubsystem_Base
---@field AnimGraphNode_Root FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_16 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_15 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_14 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_MeshRefPose FAnimNodeExposedValueHandler_PropertyAccess
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



---@class UABP_East_LUV_3151_C : UAnimInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystemInstance
---@field AnimBlueprintExtension_Base FAnimSubsystemInstance
---@field AnimGraphNode_Root FAnimNode_Root
---@field AnimGraphNode_ModifyBone_16 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_15 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_14 FAnimNode_ModifyBone
---@field AnimGraphNode_MeshRefPose FAnimNode_MeshSpaceRefPose
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
---@field FRWheelRotation FRotator
---@field BWheelRotation FRotator
---@field RFDoorsRotation FRotator
---@field LMirrorsRotation FRotator
---@field LFDoorRotation FRotator
---@field LWindowCleanerRotation FRotator
---@field RWindowCleanerRotation FRotator
---@field KnobsRotation FRotator
---@field FrontLighHolder FRotator
---@field WheelSpeedOffset double
---@field WheelSpeed double
---@field WheelAngle double
---@field FrontDoorsAngle double
---@field MirrorsAngle double
---@field KnobsAngle double
---@field FrontLightAngle double
---@field WindowCleanerAngle double
---@field RMirrorsRotation_0 FRotator
---@field BackDoorsAngle double
---@field RBDoorsRotation FRotator
---@field LBDoorsRotation FRotator
local UABP_East_LUV_3151_C = {}

---@param AnimGraph FPoseLink
function UABP_East_LUV_3151_C:AnimGraph(AnimGraph) end
---@param DetaTime double
function UABP_East_LUV_3151_C:UpdateSpeedOffset(DetaTime) end
function UABP_East_LUV_3151_C:UpdateWheelsRotation() end
---@param DeltaTimeX float
function UABP_East_LUV_3151_C:BlueprintUpdateAnimation(DeltaTimeX) end
function UABP_East_LUV_3151_C:UpdateDoorsRotation() end
function UABP_East_LUV_3151_C:UpdateMirrorRotation() end
function UABP_East_LUV_3151_C:UpdateKnobsRotation() end
function UABP_East_LUV_3151_C:UpdateFrontLight() end
function UABP_East_LUV_3151_C:UpdateWindowCleaner() end
---@param EntryPoint int32
function UABP_East_LUV_3151_C:ExecuteUbergraph_ABP_East_LUV_3151(EntryPoint) end


