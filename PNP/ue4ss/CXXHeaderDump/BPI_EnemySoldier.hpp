#ifndef UE4SS_SDK_BPI_EnemySoldier_HPP
#define UE4SS_SDK_BPI_EnemySoldier_HPP

class IBPI_EnemySoldier_C : public IInterface
{

    void SetMovementSpeed(TEnumAsByte<E_AI_EnemySoldierMovementSpeed::Type> Speed, double& SpeedValue);
    void GetPatrolRoute(class ABP_PatrolRoute_C*& PatroLRoute);
}; // Size: 0x28

#endif
