#ifndef UE4SS_SDK_BPP_UAV_Drone_HPP
#define UE4SS_SDK_BPP_UAV_Drone_HPP

class ABPP_UAV_Drone_C : public ABPP_UAV_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x23C0 (size: 0x8)
    class UDroneAngleFlightComponent* DroneAngleFlight;                               // 0x23C8 (size: 0x8)
    class UDroneTCPController* DroneTCPController;                                    // 0x23D0 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_FiberOptic;                                  // 0x23D8 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerRR;                                 // 0x23E0 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_Bracket;                                     // 0x23E8 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_ExplosivePersonal;                           // 0x23F0 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerFL;                                 // 0x23F8 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerRL;                                 // 0x2400 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_ExplosiveHeavy;                              // 0x2408 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerFR;                                 // 0x2410 (size: 0x8)
    class UStaticMeshComponent* SM_Battery;                                           // 0x2418 (size: 0x8)
    class UNiagaraComponent* NS_Fiber1;                                               // 0x2420 (size: 0x8)
    FVector VectorDownDirection;                                                      // 0x2428 (size: 0x18)
    FDroneInputData Current Input;                                                    // 0x2440 (size: 0x14)

    void InpActEvt_Q_K2Node_InputKeyEvent_0(FKey Key);
    void ArmAction(double ArmedAction);
    void InpAxisEvt_I_KeyboardYaw_K2Node_InputAxisEvent_2(float AxisValue);
    void InpAxisEvt_I_KeyboardThrottle_K2Node_InputAxisEvent_3(float AxisValue);
    void ArmRemote(bool isEngineOn);
    void MovementPitchAxis(double PitchAxisInput);
    void MovementYawAxis(double MovementYawAxis);
    void MovementThrottleAxis(double MovementThrottleAxis);
    void InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_0(float AxisValue);
    void InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_1(float AxisValue);
    void MovementRollAxis(double RollAxisInput);
    void ReceiveTick(float DeltaSeconds);
    void ReceiveBeginPlay();
    void PropellerRotate(double Delta Second);
    void ExecuteUbergraph_BPP_UAV_Drone(int32 EntryPoint);
}; // Size: 0x2454

#endif
