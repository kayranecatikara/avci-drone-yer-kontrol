#ifndef UE4SS_SDK_ABP_East_LUV_3151_HPP
#define UE4SS_SDK_ABP_East_LUV_3151_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_58;                                                          // 0x0004 (size: 0x8)
    FName __NameProperty_59;                                                          // 0x000C (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_60;                                         // 0x0018 (size: 0x20)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0038 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00B8 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x00D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_16;          // 0x0100 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_15;          // 0x0130 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_14;          // 0x0160 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_MeshRefPose;            // 0x0190 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_13;          // 0x01C0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_12;          // 0x01F0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_11;          // 0x0220 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_10;          // 0x0250 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_9;           // 0x0280 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_8;           // 0x02B0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_7;           // 0x02E0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_6;           // 0x0310 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_5;           // 0x0340 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_4;           // 0x0370 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_3;           // 0x03A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_2;           // 0x03D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_1;           // 0x0400 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x0430 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0460 (size: 0x30)

}; // Size: 0x490

class UABP_East_LUV_3151_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D0 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03D8 (size: 0x20)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_16;                                 // 0x03F8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_15;                                 // 0x0520 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_14;                                 // 0x0648 (size: 0x128)
    FAnimNode_MeshSpaceRefPose AnimGraphNode_MeshRefPose;                             // 0x0770 (size: 0x10)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_13;                                 // 0x0780 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_12;                                 // 0x08A8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_11;                                 // 0x09D0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_10;                                 // 0x0AF8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_9;                                  // 0x0C20 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_8;                                  // 0x0D48 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_7;                                  // 0x0E70 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_6;                                  // 0x0F98 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_5;                                  // 0x10C0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_4;                                  // 0x11E8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_3;                                  // 0x1310 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_2;                                  // 0x1438 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_1;                                  // 0x1560 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x1688 (size: 0x128)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x17B0 (size: 0x20)
    FRotator FRWheelRotation;                                                         // 0x17D0 (size: 0x18)
    FRotator BWheelRotation;                                                          // 0x17E8 (size: 0x18)
    FRotator RFDoorsRotation;                                                         // 0x1800 (size: 0x18)
    FRotator LMirrorsRotation;                                                        // 0x1818 (size: 0x18)
    FRotator LFDoorRotation;                                                          // 0x1830 (size: 0x18)
    FRotator LWindowCleanerRotation;                                                  // 0x1848 (size: 0x18)
    FRotator RWindowCleanerRotation;                                                  // 0x1860 (size: 0x18)
    FRotator KnobsRotation;                                                           // 0x1878 (size: 0x18)
    FRotator FrontLighHolder;                                                         // 0x1890 (size: 0x18)
    double WheelSpeedOffset;                                                          // 0x18A8 (size: 0x8)
    double WheelSpeed;                                                                // 0x18B0 (size: 0x8)
    double WheelAngle;                                                                // 0x18B8 (size: 0x8)
    double FrontDoorsAngle;                                                           // 0x18C0 (size: 0x8)
    double MirrorsAngle;                                                              // 0x18C8 (size: 0x8)
    double KnobsAngle;                                                                // 0x18D0 (size: 0x8)
    double FrontLightAngle;                                                           // 0x18D8 (size: 0x8)
    double WindowCleanerAngle;                                                        // 0x18E0 (size: 0x8)
    FRotator RMirrorsRotation_0;                                                      // 0x18E8 (size: 0x18)
    double BackDoorsAngle;                                                            // 0x1900 (size: 0x8)
    FRotator RBDoorsRotation;                                                         // 0x1908 (size: 0x18)
    FRotator LBDoorsRotation;                                                         // 0x1920 (size: 0x18)

    void AnimGraph(FPoseLink& AnimGraph);
    void UpdateSpeedOffset(double DetaTime);
    void UpdateWheelsRotation();
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void UpdateDoorsRotation();
    void UpdateMirrorRotation();
    void UpdateKnobsRotation();
    void UpdateFrontLight();
    void UpdateWindowCleaner();
    void ExecuteUbergraph_ABP_East_LUV_3151(int32 EntryPoint);
}; // Size: 0x1938

#endif
