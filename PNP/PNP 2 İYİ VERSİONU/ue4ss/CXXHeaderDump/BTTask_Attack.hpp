#ifndef UE4SS_SDK_BTTask_Attack_HPP
#define UE4SS_SDK_BTTask_Attack_HPP

class UBTTask_Attack_C : public UBTTask_BlueprintBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A8 (size: 0x8)

    void ReceiveExecuteAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void FinishedAttack();
    void ExecuteUbergraph_BTTask_Attack(int32 EntryPoint);
}; // Size: 0xB0

#endif
