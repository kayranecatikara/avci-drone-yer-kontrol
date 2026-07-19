#ifndef UE4SS_SDK_BPP_AIDrone_HPP
#define UE4SS_SDK_BPP_AIDrone_HPP

class ABPP_AIDrone_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class USphereComponent* Sphere;                                                   // 0x0330 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Explosive1;                                // 0x0338 (size: 0x8)
    class UStaticMeshComponent* SM_Battery15;                                         // 0x0340 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone15_Bracket;                                  // 0x0348 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone15_Propeller4;                               // 0x0350 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone15_Propeller3;                               // 0x0358 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone15_Propeller2;                               // 0x0360 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone15_Propeller1;                               // 0x0368 (size: 0x8)
    class UStaticMeshComponent* SM_Drone15;                                           // 0x0370 (size: 0x8)
    class UStaticMeshComponent* SM_Battery7;                                          // 0x0378 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Explosive;                                 // 0x0380 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Bracket;                                   // 0x0388 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller4;                                // 0x0390 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller3;                                // 0x0398 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller2;                                // 0x03A0 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller1;                                // 0x03A8 (size: 0x8)
    class UStaticMeshComponent* SM_Drone7;                                            // 0x03B0 (size: 0x8)
    class UAudioComponent* Audio;                                                     // 0x03B8 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Bracket;                                  // 0x03C0 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Explosive;                                // 0x03C8 (size: 0x8)
    class UStaticMeshComponent* SM_Battery10;                                         // 0x03D0 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Propeller4;                               // 0x03D8 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Propeller3;                               // 0x03E0 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Propeller2;                               // 0x03E8 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone10_Propeller1;                               // 0x03F0 (size: 0x8)
    class UStaticMeshComponent* SM_Drone10;                                           // 0x03F8 (size: 0x8)
    class UBPC_AIMove_C* BPC_AIMove;                                                  // 0x0400 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0408 (size: 0x8)
    class ABP_Spline_C* Spline;                                                       // 0x0410 (size: 0x8)
    double Speed;                                                                     // 0x0418 (size: 0x8)
    FVector Mesh Scale;                                                               // 0x0420 (size: 0x18)
    double Yaw Rotation Angle;                                                        // 0x0438 (size: 0x8)
    class UBP_GameInstance_C* As BP Game Instance;                                    // 0x0440 (size: 0x8)
    double Pitch Rotation Angle;                                                      // 0x0448 (size: 0x8)
    int32 RandomValue;                                                                // 0x0450 (size: 0x4)
    float Delta Seconds;                                                              // 0x0454 (size: 0x4)
    double Countdown;                                                                 // 0x0458 (size: 0x8)
    FTimerHandle CounterTimeHandle;                                                   // 0x0460 (size: 0x8)
    bool isFinishedTime;                                                              // 0x0468 (size: 0x1)
    class ABP_MainOPSoldier_C* BP Main OPSoldier;                                     // 0x0470 (size: 0x8)
    class AHUD_MainUAV_C* HUD Main Drone;                                             // 0x0478 (size: 0x8)
    class ABP_OPSoldier_C* BP OPSoldier;                                              // 0x0480 (size: 0x8)

    void Counter();
    void UserConstructionScript();
    void SetVisibility7(bool isShow);
    void SetVisibility10(bool isShow);
    void SetVisibility15(bool isShow);
    void ReceiveBeginPlay();
    void HideAllDrones();
    void SuccessfulKamikaze();
    void ReceiveTick(float DeltaSeconds);
    void OPSoldierDead_Event();
    void ExecuteUbergraph_BPP_AIDrone(int32 EntryPoint);
}; // Size: 0x488

#endif
