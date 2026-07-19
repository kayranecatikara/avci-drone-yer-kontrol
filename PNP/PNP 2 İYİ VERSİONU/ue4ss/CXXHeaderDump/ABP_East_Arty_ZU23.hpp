#ifndef UE4SS_SDK_ABP_East_Arty_ZU23_HPP
#define UE4SS_SDK_ABP_East_Arty_ZU23_HPP

struct FAnimBlueprintGeneratedConstantData : public FAnimBlueprintConstantData
{
    FName __NameProperty_45;                                                          // 0x0004 (size: 0x8)
    float __FloatProperty_46;                                                         // 0x000C (size: 0x4)
    FInputScaleBiasClampConstants __StructProperty_47;                                // 0x0010 (size: 0x2C)
    float __FloatProperty_48;                                                         // 0x003C (size: 0x4)
    bool __BoolProperty_49;                                                           // 0x0040 (size: 0x1)
    EAnimSyncMethod __EnumProperty_50;                                                // 0x0041 (size: 0x1)
    FName __NameProperty_51;                                                          // 0x0044 (size: 0x8)
    FAnimNodeFunctionRef __StructProperty_52;                                         // 0x0050 (size: 0x20)
    TEnumAsByte<ERefPoseType> __ByteProperty_53;                                      // 0x0070 (size: 0x1)
    FAnimSubsystem_PropertyAccess AnimBlueprintExtension_PropertyAccess;              // 0x0078 (size: 0x80)
    FAnimSubsystem_Base AnimBlueprintExtension_Base;                                  // 0x00F8 (size: 0x18)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ComponentToLocalSpace;  // 0x0110 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_7;           // 0x0140 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_6;           // 0x0170 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_Root;                   // 0x01A0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_5;           // 0x01D0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_4;           // 0x0200 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_3;           // 0x0230 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_2;           // 0x0260 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone_1;           // 0x0290 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ModifyBone;             // 0x02C0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_LocalToComponentSpace;  // 0x02F0 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_SequencePlayer;         // 0x0320 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_ApplyAdditive;          // 0x0350 (size: 0x30)
    FAnimNodeExposedValueHandler_PropertyAccess AnimGraphNode_LocalRefPose;           // 0x0380 (size: 0x30)

}; // Size: 0x3B0

class UABP_East_Arty_ZU23_C : public UAnimInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03C0 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_PropertyAccess;                     // 0x03C8 (size: 0x8)
    FAnimSubsystemInstance AnimBlueprintExtension_Base;                               // 0x03D0 (size: 0x8)
    FAnimNode_ConvertComponentToLocalSpace AnimGraphNode_ComponentToLocalSpace;       // 0x03D8 (size: 0x20)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_7;                                  // 0x03F8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_6;                                  // 0x0520 (size: 0x128)
    FAnimNode_Root AnimGraphNode_Root;                                                // 0x0648 (size: 0x20)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_5;                                  // 0x0668 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_4;                                  // 0x0790 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_3;                                  // 0x08B8 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_2;                                  // 0x09E0 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone_1;                                  // 0x0B08 (size: 0x128)
    FAnimNode_ModifyBone AnimGraphNode_ModifyBone;                                    // 0x0C30 (size: 0x128)
    FAnimNode_ConvertLocalToComponentSpace AnimGraphNode_LocalToComponentSpace;       // 0x0D58 (size: 0x20)
    FAnimNode_SequencePlayer AnimGraphNode_SequencePlayer;                            // 0x0D78 (size: 0x48)
    FAnimNode_ApplyAdditive AnimGraphNode_ApplyAdditive;                              // 0x0DC0 (size: 0xC8)
    FAnimNode_RefPose AnimGraphNode_LocalRefPose;                                     // 0x0E88 (size: 0x10)
    double Wheel Speed;                                                               // 0x0E98 (size: 0x8)
    double Turret angle;                                                              // 0x0EA0 (size: 0x8)
    double Gun Angle;                                                                 // 0x0EA8 (size: 0x8)
    double Suspension angle;                                                          // 0x0EB0 (size: 0x8)
    double Holders Position;                                                          // 0x0EB8 (size: 0x8)
    FRotator WheelRotation;                                                           // 0x0EC0 (size: 0x18)
    FRotator TurretRotation;                                                          // 0x0ED8 (size: 0x18)
    FRotator GunRotattion;                                                            // 0x0EF0 (size: 0x18)
    FRotator Suspension_Angle;                                                        // 0x0F08 (size: 0x18)
    FVector Holders_Position;                                                         // 0x0F20 (size: 0x18)
    double WheelSpeedOffset;                                                          // 0x0F38 (size: 0x8)
    FRotator SuspensionLeft;                                                          // 0x0F40 (size: 0x18)
    FRotator SuspensinRight;                                                          // 0x0F58 (size: 0x18)
    double OffsetSuspensionRight;                                                     // 0x0F70 (size: 0x8)
    double OffsetSuspensionLeft;                                                      // 0x0F78 (size: 0x8)
    FVector HolderPosition;                                                           // 0x0F80 (size: 0x18)

    void AnimGraph(FPoseLink& AnimGraph);
    void UpdateWeaponVerAngle();
    void UpdateWeaponHorAngle();
    void UpdateHatches();
    void UpdateTracksMaterial();
    void UpdateTurret();
    void UpdateWheels();
    void UpdateSpeedOffset(double Increment);
    void BlueprintUpdateAnimation(float DeltaTimeX);
    void Update Speed Offset(double Increment);
    void Update Turent and Gun angle();
    void Update Suspension Angle();
    void Update Holders Position();
    void Update Wheels();
    void TurretElevation(double Angle);
    void ExecuteUbergraph_ABP_East_Arty_ZU23(int32 EntryPoint);
}; // Size: 0xF98

#endif
