#ifndef UE4SS_SDK_BP_OPSoldier_HPP
#define UE4SS_SDK_BP_OPSoldier_HPP

class ABP_OPSoldier_C : public ACharacter
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0650 (size: 0x8)
    class UCapsuleComponent* COL_Interact;                                            // 0x0658 (size: 0x8)
    class UArrowComponent* Arrow1;                                                    // 0x0660 (size: 0x8)
    class UStaticMeshComponent* SM_FPV_View;                                          // 0x0668 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0670 (size: 0x8)
    bool isDead;                                                                      // 0x0678 (size: 0x1)
    FBP_OPSoldier_COPSoldierDead OPSoldierDead;                                       // 0x0680 (size: 0x10)
    void OPSoldierDead();
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x0690 (size: 0x8)

    void ReceiveBeginPlay();
    void InteractDrone(class ABPP_UAV_C* Object);
    void Interact(class ABPP_UAV_C* BPP Drone Base);
    void CalculateDistance();
    void ExecuteUbergraph_BP_OPSoldier(int32 EntryPoint);
    void OPSoldierDead__DelegateSignature();
}; // Size: 0x698

#endif
