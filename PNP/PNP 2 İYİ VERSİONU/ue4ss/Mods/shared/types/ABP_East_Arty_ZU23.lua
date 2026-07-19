---@meta

---@class FAnimBlueprintGeneratedConstantData : FAnimBlueprintConstantData
---@field __NameProperty_45 FName
---@field __FloatProperty_46 float
---@field __StructProperty_47 FInputScaleBiasClampConstants
---@field __FloatProperty_48 float
---@field __BoolProperty_49 boolean
---@field __EnumProperty_50 EAnimSyncMethod
---@field __NameProperty_51 FName
---@field __StructProperty_52 FAnimNodeFunctionRef
---@field __ByteProperty_53 ERefPoseType
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystem_PropertyAccess
---@field AnimBlueprintExtension_Base FAnimSubsystem_Base
---@field AnimGraphNode_ComponentToLocalSpace FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_7 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_6 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_Root FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_5 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_4 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_3 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_2 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_LocalToComponentSpace FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_SequencePlayer FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ApplyAdditive FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_LocalRefPose FAnimNodeExposedValueHandler_PropertyAccess
local FAnimBlueprintGeneratedConstantData = {}



---@class UABP_East_Arty_ZU23_C : UAnimInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystemInstance
---@field AnimBlueprintExtension_Base FAnimSubsystemInstance
---@field AnimGraphNode_ComponentToLocalSpace FAnimNode_ConvertComponentToLocalSpace
---@field AnimGraphNode_ModifyBone_7 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_6 FAnimNode_ModifyBone
---@field AnimGraphNode_Root FAnimNode_Root
---@field AnimGraphNode_ModifyBone_5 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_4 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_3 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_2 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone_1 FAnimNode_ModifyBone
---@field AnimGraphNode_ModifyBone FAnimNode_ModifyBone
---@field AnimGraphNode_LocalToComponentSpace FAnimNode_ConvertLocalToComponentSpace
---@field AnimGraphNode_SequencePlayer FAnimNode_SequencePlayer
---@field AnimGraphNode_ApplyAdditive FAnimNode_ApplyAdditive
---@field AnimGraphNode_LocalRefPose FAnimNode_RefPose
---@field ['Wheel Speed'] double
---@field ['Turret angle'] double
---@field ['Gun Angle'] double
---@field ['Suspension angle'] double
---@field ['Holders Position'] double
---@field WheelRotation FRotator
---@field TurretRotation FRotator
---@field GunRotattion FRotator
---@field Suspension_Angle FRotator
---@field Holders_Position FVector
---@field WheelSpeedOffset double
---@field SuspensionLeft FRotator
---@field SuspensinRight FRotator
---@field OffsetSuspensionRight double
---@field OffsetSuspensionLeft double
---@field HolderPosition FVector
local UABP_East_Arty_ZU23_C = {}

---@param AnimGraph FPoseLink
function UABP_East_Arty_ZU23_C:AnimGraph(AnimGraph) end
function UABP_East_Arty_ZU23_C:UpdateWeaponVerAngle() end
function UABP_East_Arty_ZU23_C:UpdateWeaponHorAngle() end
function UABP_East_Arty_ZU23_C:UpdateHatches() end
function UABP_East_Arty_ZU23_C:UpdateTracksMaterial() end
function UABP_East_Arty_ZU23_C:UpdateTurret() end
function UABP_East_Arty_ZU23_C:UpdateWheels() end
---@param Increment double
function UABP_East_Arty_ZU23_C:UpdateSpeedOffset(Increment) end
---@param DeltaTimeX float
function UABP_East_Arty_ZU23_C:BlueprintUpdateAnimation(DeltaTimeX) end
---@param Increment double
UABP_East_Arty_ZU23_C['Update Speed Offset'] = function(self, Increment) end
UABP_East_Arty_ZU23_C['Update Turent and Gun angle'] = function(self, ) end
UABP_East_Arty_ZU23_C['Update Suspension Angle'] = function(self, ) end
UABP_East_Arty_ZU23_C['Update Holders Position'] = function(self, ) end
UABP_East_Arty_ZU23_C['Update Wheels'] = function(self, ) end
---@param Angle double
function UABP_East_Arty_ZU23_C:TurretElevation(Angle) end
---@param EntryPoint int32
function UABP_East_Arty_ZU23_C:ExecuteUbergraph_ABP_East_Arty_ZU23(EntryPoint) end


