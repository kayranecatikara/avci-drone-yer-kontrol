---@meta

---@class FAnimBlueprintGeneratedConstantData : FAnimBlueprintConstantData
---@field __NameProperty_148 FName
---@field __NameProperty_149 FName
---@field __NameProperty_150 FName
---@field __NameProperty_151 FName
---@field __IntProperty_152 int32
---@field __BoolProperty_153 boolean
---@field __FloatProperty_154 float
---@field __StructProperty_155 FInputScaleBiasClampConstants
---@field __FloatProperty_156 float
---@field __BoolProperty_157 boolean
---@field __EnumProperty_158 EAnimSyncMethod
---@field __ByteProperty_159 EAnimGroupRole::Type
---@field __NameProperty_160 FName
---@field __NameProperty_161 FName
---@field __IntProperty_162 int32
---@field __NameProperty_163 FName
---@field __IntProperty_164 int32
---@field __NameProperty_165 FName
---@field __NameProperty_166 FName
---@field __IntProperty_167 int32
---@field __StructProperty_168 FAnimNodeFunctionRef
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystem_PropertyAccess
---@field AnimBlueprintExtension_Base FAnimSubsystem_Base
---@field AnimGraphNode_Root FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_7 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_6 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_BlendSpacePlayer FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult_5 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_SequencePlayer_2 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult_4 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateMachine_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_SaveCachedPose FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_5 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_4 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_3 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_2 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_TransitionResult FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ApplyAdditive FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_UseCachedPose_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_SequencePlayer_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult_3 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_SequencePlayer FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult_2 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult_1 FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_UseCachedPose FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateResult FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_StateMachine FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ModifyBone FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_LocalToComponentSpace FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_ComponentToLocalSpace FAnimNodeExposedValueHandler_PropertyAccess
---@field AnimGraphNode_Slot FAnimNodeExposedValueHandler_PropertyAccess
local FAnimBlueprintGeneratedConstantData = {}



---@class FAnimBlueprintGeneratedMutableData : FAnimBlueprintMutableData
---@field __FloatProperty float
local FAnimBlueprintGeneratedMutableData = {}



---@class UABP_EnemySoldierRetarget_C : UAnimInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field __AnimBlueprintMutables FAnimBlueprintGeneratedMutableData
---@field AnimBlueprintExtension_PropertyAccess FAnimSubsystemInstance
---@field AnimBlueprintExtension_Base FAnimSubsystemInstance
---@field AnimGraphNode_Root FAnimNode_Root
---@field AnimGraphNode_TransitionResult_7 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult_6 FAnimNode_TransitionResult
---@field AnimGraphNode_BlendSpacePlayer FAnimNode_BlendSpacePlayer
---@field AnimGraphNode_StateResult_5 FAnimNode_StateResult
---@field AnimGraphNode_SequencePlayer_2 FAnimNode_SequencePlayer
---@field AnimGraphNode_StateResult_4 FAnimNode_StateResult
---@field AnimGraphNode_StateMachine_1 FAnimNode_StateMachine
---@field AnimGraphNode_SaveCachedPose FAnimNode_SaveCachedPose
---@field AnimGraphNode_TransitionResult_5 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult_4 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult_3 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult_2 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult_1 FAnimNode_TransitionResult
---@field AnimGraphNode_TransitionResult FAnimNode_TransitionResult
---@field AnimGraphNode_ApplyAdditive FAnimNode_ApplyAdditive
---@field AnimGraphNode_UseCachedPose_1 FAnimNode_UseCachedPose
---@field AnimGraphNode_SequencePlayer_1 FAnimNode_SequencePlayer
---@field AnimGraphNode_StateResult_3 FAnimNode_StateResult
---@field AnimGraphNode_SequencePlayer FAnimNode_SequencePlayer
---@field AnimGraphNode_StateResult_2 FAnimNode_StateResult
---@field AnimGraphNode_StateResult_1 FAnimNode_StateResult
---@field AnimGraphNode_UseCachedPose FAnimNode_UseCachedPose
---@field AnimGraphNode_StateResult FAnimNode_StateResult
---@field AnimGraphNode_StateMachine FAnimNode_StateMachine
---@field AnimGraphNode_ModifyBone FAnimNode_ModifyBone
---@field AnimGraphNode_LocalToComponentSpace FAnimNode_ConvertLocalToComponentSpace
---@field AnimGraphNode_ComponentToLocalSpace FAnimNode_ConvertComponentToLocalSpace
---@field AnimGraphNode_Slot FAnimNode_Slot
---@field Character ACharacter
---@field MovementComponent UCharacterMovementComponent
---@field Velocity FVector
---@field GroundSpeed double
---@field ShouldMove boolean
---@field IsFalling boolean
---@field MyCharacter APawn
---@field ['Return Value Y (Pitch)'] float
---@field ['As BP AI Enemy Soldier'] ABP_AI_EnemySoldier_C
local UABP_EnemySoldierRetarget_C = {}

---@param AnimGraph FPoseLink
function UABP_EnemySoldierRetarget_C:AnimGraph(AnimGraph) end
function UABP_EnemySoldierRetarget_C:EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_EnemySoldierRetarget_AnimGraphNode_TransitionResult_F89BC661488FB72F0EEE34AB0F862B30() end
---@param DeltaTimeX float
function UABP_EnemySoldierRetarget_C:BlueprintUpdateAnimation(DeltaTimeX) end
function UABP_EnemySoldierRetarget_C:BlueprintInitializeAnimation() end
---@param EntryPoint int32
function UABP_EnemySoldierRetarget_C:ExecuteUbergraph_ABP_EnemySoldierRetarget(EntryPoint) end


