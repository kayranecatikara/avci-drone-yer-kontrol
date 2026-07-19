#ifndef UE4SS_SDK_BTTask_SetMovementSpeed_HPP
#define UE4SS_SDK_BTTask_SetMovementSpeed_HPP

class UBTTask_SetMovementSpeed_C : public UBTTask_BlueprintBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A8 (size: 0x8)
    TEnumAsByte<E_AI_EnemySoldierMovementSpeed::Type> Speed;                          // 0x00B0 (size: 0x1)

    void ReceiveExecuteAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void ExecuteUbergraph_BTTask_SetMovementSpeed(int32 EntryPoint);
}; // Size: 0xB1

#endif
