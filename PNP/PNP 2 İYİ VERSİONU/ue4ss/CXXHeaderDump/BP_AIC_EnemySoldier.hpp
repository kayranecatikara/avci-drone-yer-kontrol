#ifndef UE4SS_SDK_BP_AIC_EnemySoldier_HPP
#define UE4SS_SDK_BP_AIC_EnemySoldier_HPP

class ABP_AIC_EnemySoldier_C : public AAIController
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03D0 (size: 0x8)
    FName AttackTargetKeyName;                                                        // 0x03D8 (size: 0x8)
    FName StateKeyName;                                                               // 0x03E0 (size: 0x8)
    TEnumAsByte<E_AI_EnemySoldierState::Type> SoldierState;                           // 0x03E8 (size: 0x1)

    void SetStateAsRunback();
    void SetStateAsDead();
    void SetStateAsCombat(class AActor* AttackTarget);
    void SetStateAsPassive();
    void ReceivePossess(class APawn* PossessedPawn);
    void ExecuteUbergraph_BP_AIC_EnemySoldier(int32 EntryPoint);
}; // Size: 0x3E9

#endif
