#ifndef UE4SS_SDK_ABP_West_MLRS_M270_HPP
#define UE4SS_SDK_ABP_West_MLRS_M270_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_96;                                                          // 0x0004 (size: 0x8)
    float __FloatProperty_97;                                                         // 0x000C (size: 0x4)
    FInputScaleBiasClampConstants __StructProperty_98;                                // 0x0010 (size: 0x2C)
    float __FloatProperty_99;                                                         // 0x003C (size: 0x4)
    bool __BoolProperty_100;                                                          // 0x0040 (size: 0x1)
    EAnimSyncMethod __EnumProperty_101;                                               // 0x0041 (size: 0x1)
    TEnumAsByte<EAnimGroupRole::Type> __ByteProperty_102;                             // 0x0042 (size: 0x1)
    FName __NameProperty_103;                                                         // 0x0044 (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_104;                                        // 0x0050 (size: 0x20)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0070 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00F0 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x0108 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_24;          // 0x0138 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0168 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_23;          // 0x0198 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_22;          // 0x01C8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_21;          // 0x01F8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_20;          // 0x0228 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_19;          // 0x0258 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_18;          // 0x0288 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_17;          // 0x02B8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_16;          // 0x02E8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_15;          // 0x0318 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_14;          // 0x0348 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_13;          // 0x0378 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_12;          // 0x03A8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_11;          // 0x03D8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_10;          // 0x0408 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_9;           // 0x0438 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ApplyAdditive;          // 0x0468 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_8;           // 0x0498 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_LocalToComponentSpace;  // 0x04C8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_LocalRefPose;           // 0x04F8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer;         // 0x0528 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_7;           // 0x0558 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_6;           // 0x0588 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_5;           // 0x05B8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_4;           // 0x05E8 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_3;           // 0x0618 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_2;           // 0x0648 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_1;           // 0x0678 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x06A8 (size: 0x30)

}; // Size: 0x6D8

class UABP_West_MLRS_M270_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D0 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03D8 (size: 0x20)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_24;                                 // 0x03F8 (size: 0x128)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x0520 (size: 0x20)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_23;                                 // 0x0540 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_22;                                 // 0x0668 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_21;                                 // 0x0790 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_20;                                 // 0x08B8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_19;                                 // 0x09E0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_18;                                 // 0x0B08 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_17;                                 // 0x0C30 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_16;                                 // 0x0D58 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_15;                                 // 0x0E80 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_14;                                 // 0x0FA8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_13;                                 // 0x10D0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_12;                                 // 0x11F8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_11;                                 // 0x1320 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_10;                                 // 0x1448 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_9;                                  // 0x1570 (size: 0x128)
    FAnimNode_ApplyAdditive AnimGraphNode_ApplyAdditive;                              // 0x1698 (size: 0xC8)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_8;                                  // 0x1760 (size: 0x128)
    FAnimNode_ConvertLocalToComponentSpace AnimGraphNode_LocalToComponentSpace;       // 0x1888 (size: 0x20)
    FAnimNode_RefPose AnimGraphNode_LocalRefPose;                                     // 0x18A8 (size: 0x10)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer;                            // 0x18B8 (size: 0x48)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_7;                                  // 0x1900 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_6;                                  // 0x1A28 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_5;                                  // 0x1B50 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_4;                                  // 0x1C78 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_3;                                  // 0x1DA0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_2;                                  // 0x1EC8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_1;                                  // 0x1FF0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x2118 (size: 0x128)
    FRotator RocketLauncherBaseRotation;                                              // 0x2240 (size: 0x18)
    double RocketLauncherHorizontalRotation;                                          // 0x2258 (size: 0x8)
    double RocketLauncherElevation;                                                   // 0x2260 (size: 0x8)
    double DoorsAngle;                                                                // 0x2268 (size: 0x8)
    FRotator DoorRotation;                                                            // 0x2270 (size: 0x18)
    FRotator WheelRotation;                                                           // 0x2288 (size: 0x18)
    double WheelSpeed;                                                                // 0x22A0 (size: 0x8)
    double WheelSpeedOffset;                                                          // 0x22A8 (size: 0x8)
    class UMaterialInstanceDynamic* TracksMID;                                        // 0x22B0 (size: 0x8)
    double DoorHatchesAngle;                                                          // 0x22B8 (size: 0x8)
    double FrontHatchesAngle;                                                         // 0x22C0 (size: 0x8)
    double RoofHatchAngle;                                                            // 0x22C8 (size: 0x8)
    FRotator DoorHatchesRotation;                                                     // 0x22D0 (size: 0x18)
    FRotator FrontHatchesRotation;                                                    // 0x22E8 (size: 0x18)
    FRotator RoofHatchRotation;                                                       // 0x2300 (size: 0x18)

    void AnimGraph(FPoseLink& AnimGraph);
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_MLRS_M270_AnimGraphNode_ModifyBone_8EF8429D48BEA16540C3D28DD2C063F0();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_MLRS_M270_AnimGraphNode_ModifyBone_0E518E4D468BB2CAD1878C8D8753FD2F();
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void UpdateSpeedOffset(double DetaTime);
    void UpdateWheelsRotation();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_MLRS_M270_AnimGraphNode_ModifyBone_BD5F2BC7418A0886865E64B5351B0CF9();
    void UpdateDoorsRotation();
    void UpdateRocketLauncher();
    void UpdateTracksMaterial();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_MLRS_M270_AnimGraphNode_ModifyBone_0E2748AC4CE5A76AB0CEA5A31E9CEE41();
    void BlueprintInitializeAnimation();
    void SaveTracksMID();
    void UpdateFrontHatches();
    void UpdateDoorHatches();
    void UpdateRoofHatch();
    void ExecuteUbergraph_ABP_West_MLRS_M270(int32 EntryPoint);
}; // Size: 0x2318

#endif
