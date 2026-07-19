#ifndef UE4SS_SDK_ABP_OPSoldier_HPP
#define UE4SS_SDK_ABP_OPSoldier_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_7;                                                           // 0x0004 (size: 0x8)
    FName __NameProperty_8;                                                           // 0x000C (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_9;                                          // 0x0018 (size: 0x20)
    float __FloatProperty_10;                                                         // 0x0038 (size: 0x4)
    FInputScaleBiasClampConstants __StructProperty_11;                                // 0x003C (size: 0x2C)
    float __FloatProperty_12;                                                         // 0x0068 (size: 0x4)
    bool __BoolProperty_13;                                                           // 0x006C (size: 0x1)
    EAnimSyncMethod __EnumProperty_14;                                                // 0x006D (size: 0x1)
    TEnumAsByte<EAnimGroupRole::Type> __ByteProperty_15;                              // 0x006E (size: 0x1)
    FName __NameProperty_16;                                                          // 0x0070 (size: 0x8)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0078 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00F8 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x0110 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer;         // 0x0140 (size: 0x30)

}; // Size: 0x170

class UABP_OPSoldier_C : public UAnimInstance
{
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03C8 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03D0 (size: 0x20)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer;                            // 0x03F0 (size: 0x48)

    void AnimGraph(FPoseLink& AnimGraph);
}; // Size: 0x438

#endif
