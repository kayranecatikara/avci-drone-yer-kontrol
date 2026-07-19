#ifndef UE4SS_SDK_BPP_UAV_FixedWings_HPP
#define UE4SS_SDK_BPP_UAV_FixedWings_HPP

class ABPP_UAV_FixedWings_C : public ABPP_UAV_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x23C0 (size: 0x8)
    class UStaticMeshComponent* SM_Wing_RR;                                           // 0x23C8 (size: 0x8)
    class UStaticMeshComponent* SM_Wing_RL;                                           // 0x23D0 (size: 0x8)
    class UStaticMeshComponent* SM_Wing_LR;                                           // 0x23D8 (size: 0x8)
    class UStaticMeshComponent* SM_Wing_LL;                                           // 0x23E0 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_Propeller;                                   // 0x23E8 (size: 0x8)
    float Timeline_1_NewTrack_0_0424907D45AA85DEA7222E83ED4F1D8D;                     // 0x23F0 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline_1__Direction_0424907D45AA85DEA7222E83ED4F1D8D; // 0x23F4 (size: 0x1)
    class UTimelineComponent* Timeline_1;                                             // 0x23F8 (size: 0x8)
    float MovemetSmoothValue;                                                         // 0x2400 (size: 0x4)
    float RotateAngle;                                                                // 0x2404 (size: 0x4)
    float CurrentPitchRotation;                                                       // 0x2408 (size: 0x4)
    double Gravity;                                                                   // 0x2410 (size: 0x8)
    bool isLaunched;                                                                  // 0x2418 (size: 0x1)
    double ThrottleForYaw;                                                            // 0x2420 (size: 0x8)
    double LiftMultiplier;                                                            // 0x2428 (size: 0x8)
    double ThrustPower;                                                               // 0x2430 (size: 0x8)
    double DragFactor;                                                                // 0x2438 (size: 0x8)

    void ServoDeflections(double DeltaTime);
    void Timeline_1__FinishedFunc();
    void Timeline_1__UpdateFunc();
    void InpActEvt_Q_K2Node_InputKeyEvent_0(FKey Key);
    void LaunchedPlatform();
    void InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_1(float AxisValue);
    void InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_0(float AxisValue);
    void ChangeFlightMode();
    void ReceiveTick(float DeltaSeconds);
    void ReceiveBeginPlay();
    void MovementPitch();
    void MovementRoll();
    void ArmAction(double ArmedAction);
    void ExecuteUbergraph_BPP_UAV_FixedWings(int32 EntryPoint);
}; // Size: 0x2440

#endif
