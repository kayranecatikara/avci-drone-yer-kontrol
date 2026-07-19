#ifndef UE4SS_SDK_BP_AI_EnemySoldier_HPP
#define UE4SS_SDK_BP_AI_EnemySoldier_HPP

class ABP_AI_EnemySoldier_C : public ACharacter
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0650 (size: 0x8)
    class USkeletalMeshComponent* SM_Body;                                            // 0x0658 (size: 0x8)
    class USkeletalMeshComponent* SM_LeftArm;                                         // 0x0660 (size: 0x8)
    class USkeletalMeshComponent* SM_RightLeg;                                        // 0x0668 (size: 0x8)
    class USkeletalMeshComponent* SM_RightArm;                                        // 0x0670 (size: 0x8)
    class USkeletalMeshComponent* SM_LegLeft;                                         // 0x0678 (size: 0x8)
    class UCapsuleComponent* COL_Interact;                                            // 0x0680 (size: 0x8)
    class UArrowComponent* Arrow_FireDirection;                                       // 0x0688 (size: 0x8)
    bool isWieldWeapon;                                                               // 0x0690 (size: 0x1)
    class ABP_PatrolRoute_C* PatroLRoute;                                             // 0x0698 (size: 0x8)
    FBP_AI_EnemySoldier_CAttackEnd AttackEnd;                                         // 0x06A0 (size: 0x10)
    void AttackEnd();
    class UBP_GameInstance_C* AGame Instance;                                         // 0x06B0 (size: 0x8)
    TEnumAsByte<E_ExplosiveType::Type> EExplosive Type;                               // 0x06B8 (size: 0x1)
    bool isDead;                                                                      // 0x06B9 (size: 0x1)
    bool isDroneCircle;                                                               // 0x06BA (size: 0x1)
    bool isRunbackCircle;                                                             // 0x06BB (size: 0x1)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x06C0 (size: 0x8)

    void SetMovementSpeed(TEnumAsByte<E_AI_EnemySoldierMovementSpeed::Type> Speed, double& SpeedValue);
    void GetPatrolRoute(class ABP_PatrolRoute_C*& PatroLRoute);
    void OnNotifyEnd_9A5E320B49991A2D22973880ADC25EBA(FName NotifyName);
    void OnNotifyBegin_9A5E320B49991A2D22973880ADC25EBA(FName NotifyName);
    void OnInterrupted_9A5E320B49991A2D22973880ADC25EBA(FName NotifyName);
    void OnBlendOut_9A5E320B49991A2D22973880ADC25EBA(FName NotifyName);
    void OnCompleted_9A5E320B49991A2D22973880ADC25EBA(FName NotifyName);
    void Attack();
    void WieldWeapon(bool IsDetach);
    void Fire();
    void DeadCharacter();
    void ReceiveBeginPlay();
    void InteractDrone(class ABPP_UAV_C* Drone Pawn);
    void Interact(class ABPP_UAV_C* BPP Drone Base);
    void CalculateDistance();
    void SoldierAttack(bool isAttack);
    void ExecuteUbergraph_BP_AI_EnemySoldier(int32 EntryPoint);
    void AttackEnd__DelegateSignature();
}; // Size: 0x6C8

#endif
