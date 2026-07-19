#ifndef UE4SS_SDK_BP_Checkpoint_HPP
#define UE4SS_SDK_BP_Checkpoint_HPP

class ABP_Checkpoint_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UBoxComponent* COL_Interact;                                                // 0x0330 (size: 0x8)
    class UStaticMeshComponent* SM_Checkpoint;                                        // 0x0338 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0340 (size: 0x8)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x0348 (size: 0x8)
    bool isPassed;                                                                    // 0x0350 (size: 0x1)

    void ChangeSettings(bool isCheckpoint, bool is Next);
    void ReceiveBeginPlay();
    void BndEvt__BP_Checkpoint_COL_Interact_K2Node_ComponentBoundEvent_0_ComponentBeginOverlapSignature__DelegateSignature(class UPrimitiveComponent* OverlappedComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void ExecuteUbergraph_BP_Checkpoint(int32 EntryPoint);
}; // Size: 0x351

#endif
