#ifndef UE4SS_SDK_ABP_West_Heli_AH64D_HPP
#define UE4SS_SDK_ABP_West_Heli_AH64D_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_52;                                                          // 0x0004 (size: 0x8)
    FName __NameProperty_53;                                                          // 0x000C (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_54;                                         // 0x0018 (size: 0x20)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0038 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00B8 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x00D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0100 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_MeshRefPose;            // 0x0130 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_14;          // 0x0160 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_13;          // 0x0190 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_12;          // 0x01C0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_11;          // 0x01F0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_10;          // 0x0220 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_9;           // 0x0250 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_8;           // 0x0280 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_7;           // 0x02B0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_6;           // 0x02E0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_5;           // 0x0310 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_4;           // 0x0340 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_3;           // 0x0370 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_2;           // 0x03A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_1;           // 0x03D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x0400 (size: 0x30)

}; // Size: 0x430

class UABP_West_Heli_AH64D_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D0 (size: 0x8)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x03D8 (size: 0x20)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x03F8 (size: 0x20)
    FAnimNode_MeshSpaceRefPose AnimGraphNode_MeshRefPose;                             // 0x0418 (size: 0x10)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_14;                                 // 0x0428 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_13;                                 // 0x0550 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_12;                                 // 0x0678 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_11;                                 // 0x07A0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_10;                                 // 0x08C8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_9;                                  // 0x09F0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_8;                                  // 0x0B18 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_7;                                  // 0x0C40 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_6;                                  // 0x0D68 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_5;                                  // 0x0E90 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_4;                                  // 0x0FB8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_3;                                  // 0x10E0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_2;                                  // 0x1208 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_1;                                  // 0x1330 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x1458 (size: 0x128)
    double DoorAngle;                                                                 // 0x1580 (size: 0x8)
    double TurretAngle;                                                               // 0x1588 (size: 0x8)
    double GunElevation;                                                              // 0x1590 (size: 0x8)
    double MainRotorSpeed;                                                            // 0x1598 (size: 0x8)
    double MainRotorFlapsAngle;                                                       // 0x15A0 (size: 0x8)
    double TailRotorSpeed;                                                            // 0x15A8 (size: 0x8)
    double TailRotorFlapsAngle;                                                       // 0x15B0 (size: 0x8)
    double TailStabilizerAngle;                                                       // 0x15B8 (size: 0x8)
    double RotorSpeedOffset;                                                          // 0x15C0 (size: 0x8)
    FRotator MainRotorRotation;                                                       // 0x15C8 (size: 0x18)
    FRotator TailRotorRotation;                                                       // 0x15E0 (size: 0x18)
    FRotator MainRotorFlapsRotation;                                                  // 0x15F8 (size: 0x18)
    FRotator TailRotorFlapsRotation;                                                  // 0x1610 (size: 0x18)
    FRotator DoorsRotation;                                                           // 0x1628 (size: 0x18)
    FRotator TurretRotation;                                                          // 0x1640 (size: 0x18)
    FRotator GunRotation;                                                             // 0x1658 (size: 0x18)
    FRotator TailStabilizerRotation;                                                  // 0x1670 (size: 0x18)

    void AnimGraph(FPoseLink& AnimGraph);
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_EF77F2124AFCA26EC5C2EF86C32D9FB7();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_E8034E944B62D71795AADD9159CD1395();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_34DAF2C34C1D24338F0ACAB3312F1B33();
    void EvaluateGraphExposedInputs_ExecuteUbergraph_ABP_West_Heli_AH64D_AnimGraphNode_ModifyBone_F92F228E463D43DF0DDF0A8C60518E98();
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void UpdateSpeedOffset(double Increment);
    void UpdateRotorSpeed();
    void UpdateDoors();
    void UpdateFlaps();
    void UpdateTurret();
    void UpdateTailStabilizer();
    void ExecuteUbergraph_ABP_West_Heli_AH64D(int32 EntryPoint);
}; // Size: 0x1688

#endif
