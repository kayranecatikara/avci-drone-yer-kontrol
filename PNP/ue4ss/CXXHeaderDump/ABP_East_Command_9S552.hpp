#ifndef UE4SS_SDK_ABP_East_Command_9S552_HPP
#define UE4SS_SDK_ABP_East_Command_9S552_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_52;                                                          // 0x0004 (size: 0x8)
    FName __NameProperty_53;                                                          // 0x000C (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_54;                                         // 0x0018 (size: 0x20)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0038 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00B8 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x00D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_MeshRefPose;            // 0x0100 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_14;          // 0x0130 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_13;          // 0x0160 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_12;          // 0x0190 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_11;          // 0x01C0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_10;          // 0x01F0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_9;           // 0x0220 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_8;           // 0x0250 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_7;           // 0x0280 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_6;           // 0x02B0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_5;           // 0x02E0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_4;           // 0x0310 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_3;           // 0x0340 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_2;           // 0x0370 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_1;           // 0x03A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x03D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0400 (size: 0x30)

}; // Size: 0x430

class UABP_East_Command_9S552_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D0 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03D8 (size: 0x20)
    FAnimNode_MeshSpaceRefPose AnimGraphNode_MeshRefPose;                             // 0x03F8 (size: 0x10)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_14;                                 // 0x0408 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_13;                                 // 0x0530 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_12;                                 // 0x0658 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_11;                                 // 0x0780 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_10;                                 // 0x08A8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_9;                                  // 0x09D0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_8;                                  // 0x0AF8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_7;                                  // 0x0C20 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_6;                                  // 0x0D48 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_5;                                  // 0x0E70 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_4;                                  // 0x0F98 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_3;                                  // 0x10C0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_2;                                  // 0x11E8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_1;                                  // 0x1310 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x1438 (size: 0x128)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x1560 (size: 0x20)
    FRotator Front Wheel Rotation;                                                    // 0x1580 (size: 0x18)
    FRotator BackWheelRotation;                                                       // 0x1598 (size: 0x18)
    FRotator RotationWindowCleaner;                                                   // 0x15B0 (size: 0x18)
    FRotator DoorRotation;                                                            // 0x15C8 (size: 0x18)
    FRotator AntennaRotation;                                                         // 0x15E0 (size: 0x18)
    FRotator FrontWheelRotation;                                                      // 0x15F8 (size: 0x18)
    FRotator BSRotation;                                                              // 0x1610 (size: 0x18)
    FRotator HatchRotation;                                                           // 0x1628 (size: 0x18)
    double WheelSpeedOffset;                                                          // 0x1640 (size: 0x8)
    double WheelSpeed;                                                                // 0x1648 (size: 0x8)
    double WheelAngle;                                                                // 0x1650 (size: 0x8)
    double HatchAngle;                                                                // 0x1658 (size: 0x8)
    double DoorAngle;                                                                 // 0x1660 (size: 0x8)
    double BSDoorAngle;                                                               // 0x1668 (size: 0x8)
    double WindowCleanerRotation;                                                     // 0x1670 (size: 0x8)
    double AntennaRotationR;                                                          // 0x1678 (size: 0x8)

    void AnimGraph(FPoseLink& AnimGraph);
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void UpdateSpeedOffset(double Increment);
    void UpdateWheels();
    void UpdateHatches();
    void UpdateDoors();
    void Update Back and Side Door();
    void Update Window Cleaner();
    void Update Antenna();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_East_Command_9S552_AnimGraphNode_ModifyBone_E461B0544ECBE0AF1A752AB5F4158B59();
    void ExecuteUbergraph_ABP_East_Command_9S552(int32 EntryPoint);
}; // Size: 0x1680

#endif
