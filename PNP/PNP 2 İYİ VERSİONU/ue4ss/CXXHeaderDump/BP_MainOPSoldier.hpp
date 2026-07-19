#ifndef UE4SS_SDK_BP_MainOPSoldier_HPP
#define UE4SS_SDK_BP_MainOPSoldier_HPP

class ABP_MainOPSoldier_C : public ACharacter
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0650 (size: 0x8)
    class UStaticMeshComponent* SM_Tripod;                                            // 0x0658 (size: 0x8)
    class UStaticMeshComponent* SM_GroundControl1;                                    // 0x0660 (size: 0x8)
    class UStaticMeshComponent* SM_FPV_View;                                          // 0x0668 (size: 0x8)

    void ReceiveBeginPlay();
    void BndEvt__BP_MainOPSoldier_CapsuleComponent_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(class UPrimitiveComponent* OverlappedComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void ExecuteUbergraph_BP_MainOPSoldier(int32 EntryPoint);
}; // Size: 0x670

#endif
