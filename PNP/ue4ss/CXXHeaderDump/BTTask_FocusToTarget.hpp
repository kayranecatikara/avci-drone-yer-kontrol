#ifndef UE4SS_SDK_BTTask_FocusToTarget_HPP
#define UE4SS_SDK_BTTask_FocusToTarget_HPP

class UBTTask_FocusToTarget_C : public UBTTask_BlueprintBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A8 (size: 0x8)
    FBlackboardKeySelector AttackTargetKey;                                           // 0x00B0 (size: 0x28)

    void ReceiveExecuteAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void ExecuteUbergraph_BTTask_FocusToTarget(int32 EntryPoint);
}; // Size: 0xD8

#endif
