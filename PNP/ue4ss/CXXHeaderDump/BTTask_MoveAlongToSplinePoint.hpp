#ifndef UE4SS_SDK_BTTask_MoveAlongToSplinePoint_HPP
#define UE4SS_SDK_BTTask_MoveAlongToSplinePoint_HPP

class UBTTask_MoveAlongToSplinePoint_C : public UBTTask_BlueprintBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A8 (size: 0x8)

    void OnFail_6F30BE0248E9C2EDF23B7EAF480DBF56(TEnumAsByte<EPathFollowingResult::Type> MovementResult);
    void OnSuccess_6F30BE0248E9C2EDF23B7EAF480DBF56(TEnumAsByte<EPathFollowingResult::Type> MovementResult);
    void ReceiveExecuteAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void ReceiveAbortAI(class AAIController* OwnerController, class APawn* ControlledPawn);
    void ExecuteUbergraph_BTTask_MoveAlongToSplinePoint(int32 EntryPoint);
}; // Size: 0xB0

#endif
