#ifndef UE4SS_SDK_BP_PatrolRoute_HPP
#define UE4SS_SDK_BP_PatrolRoute_HPP

class ABP_PatrolRoute_C : public AActor
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02A8 (size: 0x8)
    class USplineComponent* PatroLRoute;                                              // 0x02B0 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x02B8 (size: 0x8)
    int32 RouteIndex;                                                                 // 0x02C0 (size: 0x4)
    int32 Direction;                                                                  // 0x02C4 (size: 0x4)

    void WorldLocationOfSplinePoint(FVector& Location);
    void IncrementPatrolRouteIndex();
    void ExecuteUbergraph_BP_PatrolRoute(int32 EntryPoint);
}; // Size: 0x2C8

#endif
