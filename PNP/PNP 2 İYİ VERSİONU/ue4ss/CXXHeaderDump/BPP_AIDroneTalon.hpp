#ifndef UE4SS_SDK_BPP_AIDroneTalon_HPP
#define UE4SS_SDK_BPP_AIDroneTalon_HPP

class ABPP_AIDroneTalon_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UTalonGPSSpoofComponent* TalonGPSSpoof;                                     // 0x0330 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_WingSmall_R;                                 // 0x0338 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_WingSmall_L;                                 // 0x0340 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_Wing_R;                                      // 0x0348 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_Wing_L;                                      // 0x0350 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_Body;                                        // 0x0358 (size: 0x8)
    class UBoxComponent* Box;                                                         // 0x0360 (size: 0x8)
    class UStaticMeshComponent* SM_Talon_Propeller;                                   // 0x0368 (size: 0x8)
    class UArrowComponent* Arrow;                                                     // 0x0370 (size: 0x8)
    class UBankingComponent* Banking;                                                 // 0x0378 (size: 0x8)
    class UAudioComponent* Audio;                                                     // 0x0380 (size: 0x8)
    class UBPC_AIMove_C* BPC_AIMove;                                                  // 0x0388 (size: 0x8)
    class ABP_Spline_C* Spline;                                                       // 0x0390 (size: 0x8)
    double Speed;                                                                     // 0x0398 (size: 0x8)
    FVector Mesh Scale;                                                               // 0x03A0 (size: 0x18)
    double Yaw Rotation Angle;                                                        // 0x03B8 (size: 0x8)
    class UBP_GameInstance_C* As BP Game Instance;                                    // 0x03C0 (size: 0x8)
    double Pitch Rotation Angle;                                                      // 0x03C8 (size: 0x8)
    int32 RandomValue;                                                                // 0x03D0 (size: 0x4)
    float Delta Seconds;                                                              // 0x03D4 (size: 0x4)
    double Countdown;                                                                 // 0x03D8 (size: 0x8)
    FTimerHandle CounterTimeHandle;                                                   // 0x03E0 (size: 0x8)
    bool isFinishedTime;                                                              // 0x03E8 (size: 0x1)
    class ABP_MainOPSoldier_C* BP Main OPSoldier;                                     // 0x03F0 (size: 0x8)
    class AHUD_MainUAV_C* HUD Main Drone;                                             // 0x03F8 (size: 0x8)
    class ABP_OPSoldier_C* BP OPSoldier;                                              // 0x0400 (size: 0x8)
    bool Crashed;                                                                     // 0x0408 (size: 0x1)
    class AGM_UAVBase_C* As GM UAVBase;                                               // 0x0410 (size: 0x8)
    TArray<class UStaticMeshComponent*> Pieces;                                       // 0x0418 (size: 0x10)
    TArray<class UStaticMeshComponent*> PiecesCopy;                                   // 0x0428 (size: 0x10)

    void Counter();
    void UserConstructionScript();
    void ReceiveTick(float DeltaSeconds);
    void BndEvt__BPP_AIDroneTalon_Box_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(class UPrimitiveComponent* OverlappedComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_BPP_AIDroneTalon(int32 EntryPoint);
}; // Size: 0x438

#endif
