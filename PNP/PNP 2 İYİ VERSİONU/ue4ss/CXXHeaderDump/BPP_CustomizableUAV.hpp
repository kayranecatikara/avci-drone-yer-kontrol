#ifndef UE4SS_SDK_BPP_CustomizableUAV_HPP
#define UE4SS_SDK_BPP_CustomizableUAV_HPP

class ABPP_CustomizableUAV_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UStaticMeshComponent* SM_Marble;                                            // 0x0330 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller1;                                // 0x0338 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller2;                                // 0x0340 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller3;                                // 0x0348 (size: 0x8)
    class UStaticMeshComponent* SM_Battery7;                                          // 0x0350 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone7_Propeller;                                 // 0x0358 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_7;                                          // 0x0360 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0368 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0370 (size: 0x8)
    FTransform TrainTransform;                                                        // 0x0380 (size: 0x60)
    FTransform AttackTransform;                                                       // 0x03E0 (size: 0x60)
    FTransform FiberTransform10KM;                                                    // 0x0440 (size: 0x60)
    FTransform FiberTransform5KM;                                                     // 0x04A0 (size: 0x60)

    void SetVisibilityArray(TArray<class UStaticMeshComponent*>& NewParam, bool bNewVisibility);
    void SetVisibilityUAV(bool Visibility, TArray<class UStaticMeshComponent*>& UAV Pieces, class USceneComponent* ExplosiveBracket, class UStaticMeshComponent* ExplosiveHeavy, class UStaticMeshComponent* ExplosivePersonalOut, class UStaticMeshComponent* ExplosivePersonalIn);
    void ReceiveBeginPlay();
    void AllSetNoneVisibilityDrone();
    void AllSetNoneVisibilityFiber();
    void AllSetNoneVisibilityComponents();
    void SetDroneTransform();
    void SetFiberTransform();
    void SetVisibilitySDrone7(bool isVisibility);
    void ExecuteUbergraph_BPP_CustomizableUAV(int32 EntryPoint);
}; // Size: 0x500

#endif
