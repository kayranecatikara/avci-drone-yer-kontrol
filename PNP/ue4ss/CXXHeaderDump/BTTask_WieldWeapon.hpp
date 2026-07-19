#ifndef UE4SS_SDK_BTTask_WieldWeapon_HPP
#define UE4SS_SDK_BTTask_WieldWeapon_HPP

class UBTTask_WieldWeapon_C : public UBTTask_BlueprintBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A8 (size: 0x8)

    void ReceiveExecuteAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void ExecuteUbergraph_BTTask_WieldWeapon(int32 EntryPoint);
}; // Size: 0xB0

#endif
