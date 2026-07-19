#ifndef UE4SS_SDK_BP_LakeWater_HPP
#define UE4SS_SDK_BP_LakeWater_HPP

class ABP_LakeWater_C : public AActor
{
    class UStaticMeshComponent* WaterSurface;                                         // 0x02A8 (size: 0x8)
    class UMaterialInterface* Ocean Material;                                         // 0x02B0 (size: 0x8)
    double Water Scale X;                                                             // 0x02B8 (size: 0x8)
    double Water Scale Y;                                                             // 0x02C0 (size: 0x8)
    double Wave Speed;                                                                // 0x02C8 (size: 0x8)
    class UMaterialInstanceDynamic* Water Material;                                   // 0x02D0 (size: 0x8)
    double Overall Water Scale;                                                       // 0x02D8 (size: 0x8)
    double Variation Amount;                                                          // 0x02E0 (size: 0x8)
    FLinearColor Primary Water Color;                                                 // 0x02E8 (size: 0x10)
    FLinearColor Secondary Water Color;                                               // 0x02F8 (size: 0x10)

    void UserConstructionScript();
}; // Size: 0x308

#endif
