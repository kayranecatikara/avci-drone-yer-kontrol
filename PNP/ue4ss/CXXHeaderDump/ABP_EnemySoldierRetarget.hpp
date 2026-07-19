#ifndef UE4SS_SDK_ABP_EnemySoldierRetarget_HPP
#define UE4SS_SDK_ABP_EnemySoldierRetarget_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_148;                                                         // 0x0004 (size: 0x8)
    FName __NameProperty_149;                                                         // 0x000C (size: 0x8)
    FName __NameProperty_150;                                                         // 0x0014 (size: 0x8)
    FName __NameProperty_151;                                                         // 0x001C (size: 0x8)
    int32 __IntProperty_152;                                                          // 0x0024 (size: 0x4)
    bool __BoolProperty_153;                                                          // 0x0028 (size: 0x1)
    float __FloatProperty_154;                                                        // 0x002C (size: 0x4)
    FInputScaleBiasClampConstants __StructProperty_155;                               // 0x0030 (size: 0x2C)
    float __FloatProperty_156;                                                        // 0x005C (size: 0x4)
    bool __BoolProperty_157;                                                          // 0x0060 (size: 0x1)
    EAnimSyncMethod __EnumProperty_158;                                               // 0x0061 (size: 0x1)
    TEnumAsByte<EAnimGroupRole::Type> __ByteProperty_159;                             // 0x0062 (size: 0x1)
    FName __NameProperty_160;                                                         // 0x0064 (size: 0x8)
    FName __NameProperty_161;                                                         // 0x006C (size: 0x8)
    int32 __IntProperty_162;                                                          // 0x0074 (size: 0x4)
    FName __NameProperty_163;                                                         // 0x0078 (size: 0x8)
    int32 __IntProperty_164;                                                          // 0x0080 (size: 0x4)
    FName __NameProperty_165;                                                         // 0x0084 (size: 0x8)
    FName __NameProperty_166;                                                         // 0x008C (size: 0x8)
    int32 __IntProperty_167;                                                          // 0x0094 (size: 0x4)
    FAnimNodeFunctionRef __StructProperty_168;                                        // 0x0098 (size: 0x20)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x00B8 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x0138 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x0150 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_7;     // 0x0180 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_6;     // 0x01B0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_BlendSpacePlayer;       // 0x01E0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult_5;          // 0x0210 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer_2;       // 0x0240 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult_4;          // 0x0270 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateMachine_1;         // 0x02A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SaveCachedPose;         // 0x02D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_5;     // 0x0300 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_4;     // 0x0330 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_3;     // 0x0360 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_2;     // 0x0390 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult_1;     // 0x03C0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_TransitionResult;       // 0x03F0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ApplyAdditive;          // 0x0420 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_UseCachedPose_1;        // 0x0450 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer_1;       // 0x0480 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult_3;          // 0x04B0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer;         // 0x04E0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult_2;          // 0x0510 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult_1;          // 0x0540 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_UseCachedPose;          // 0x0570 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateResult;            // 0x05A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_StateMachine;           // 0x05D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x0600 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_LocalToComponentSpace;  // 0x0630 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0660 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Slot;                   // 0x0690 (size: 0x30)

}; // Size: 0x6C0

struct FAnimBlueprintGeneratedMutableData : public FAnimBlueprintMutableData
{
    float __FloatProperty;                                                            // 0x0004 (size: 0x4)

}; // Size: 0x8

class UABP_EnemySoldierRetarget_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimBlueprintGeneratedMutableData __AnimBlueprintMutables;                       // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03D0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D8 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03E0 (size: 0x20)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_7;                      // 0x0400 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_6;                      // 0x0428 (size: 0x28)
    FAnimNode_BlendSpacePlayer AnimGraphNode_BlendSpacePlayer;                        // 0x0450 (size: 0x70)
    FAnimNode_StateResult AnimGraphNode_StateResult_5;                                // 0x04C0 (size: 0x20)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer_2;                          // 0x04E0 (size: 0x48)
    FAnimNode_StateResult AnimGraphNode_StateResult_4;                                // 0x0528 (size: 0x20)
    FAnimNode_StateMachine AnimGraphNode_StateMachine_1;                              // 0x0548 (size: 0xC8)
    FAnimNode_SaveCachedPose AnimGraphNode_SaveCachedPose;                            // 0x0610 (size: 0x80)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_5;                      // 0x0690 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_4;                      // 0x06B8 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_3;                      // 0x06E0 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_2;                      // 0x0708 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult_1;                      // 0x0730 (size: 0x28)
    FAnimNode_TransitionResult AnimGraphNode_TransitionResult;                        // 0x0758 (size: 0x28)
    FAnimNode_ApplyAdditive AnimGraphNode_ApplyAdditive;                              // 0x0780 (size: 0xC8)
    FAnimNode_UseCachedPose AnimGraphNode_UseCachedPose_1;                            // 0x0848 (size: 0x28)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer_1;                          // 0x0870 (size: 0x48)
    FAnimNode_StateResult AnimGraphNode_StateResult_3;                                // 0x08B8 (size: 0x20)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer;                            // 0x08D8 (size: 0x48)
    FAnimNode_StateResult AnimGraphNode_StateResult_2;                                // 0x0920 (size: 0x20)
    FAnimNode_StateResult AnimGraphNode_StateResult_1;                                // 0x0940 (size: 0x20)
    FAnimNode_UseCachedPose AnimGraphNode_UseCachedPose;                              // 0x0960 (size: 0x28)
    FAnimNode_StateResult AnimGraphNode_StateResult;                                  // 0x0988 (size: 0x20)
    FAnimNode_StateMachine AnimGraphNode_StateMachine;                                // 0x09A8 (size: 0xC8)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x0A70 (size: 0x128)
    FAnimNode_ConvertLocalToComponentSpace AnimGraphNode_LocalToComponentSpace;       // 0x0B98 (size: 0x20)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x0BB8 (size: 0x20)
    FAnimNode_Slot AnimGraphNode_Slot;                                                // 0x0BD8 (size: 0x48)
    class ACharacter* Character;                                                      // 0x0C20 (size: 0x8)
    class UCharacterMovementComponent* MovementComponent;                             // 0x0C28 (size: 0x8)
    FVector Velocity;                                                                 // 0x0C30 (size: 0x18)
    double GroundSpeed;                                                               // 0x0C48 (size: 0x8)
    bool ShouldMove;                                                                  // 0x0C50 (size: 0x1)
    bool IsFalling;                                                                   // 0x0C51 (size: 0x1)
    class APawn* MyCharacter;                                                         // 0x0C58 (size: 0x8)
    float Return Value Y (Pitch);                                                     // 0x0C60 (size: 0x4)
    class ABP_AI_EnemySoldier_C* As BP AI Enemy Soldier;                              // 0x0C68 (size: 0x8)

    void AnimGraph(FPoseLink& AnimGraph);
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_EnemySoldierRetarget_AnimGraphNode_TransitionResult_F89BC661488FB72F0EEE34AB0F862B30();
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void BlueprintInitializeAnimation();
    void ExecuteUbergraph_ABP_EnemySoldierRetarget(int32 EntryPoint);
}; // Size: 0xC70

#endif
