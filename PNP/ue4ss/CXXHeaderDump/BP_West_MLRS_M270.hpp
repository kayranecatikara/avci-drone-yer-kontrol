#ifndef UE4SS_SDK_BP_West_MLRS_M270_HPP
#define UE4SS_SDK_BP_West_MLRS_M270_HPP

class ABP_West_MLRS_M270_C : public AActor
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02A8 (size: 0x8)
    class UNiagaraComponent* DamagedSmokeFX;                                          // 0x02B0 (size: 0x8)
    class UNiagaraComponent* WheelDustL5;                                             // 0x02B8 (size: 0x8)
    class UNiagaraComponent* WheelDustL4;                                             // 0x02C0 (size: 0x8)
    class UNiagaraComponent* WheelDustL3;                                             // 0x02C8 (size: 0x8)
    class UNiagaraComponent* WheelDustL2;                                             // 0x02D0 (size: 0x8)
    class UNiagaraComponent* WheelDustL1;                                             // 0x02D8 (size: 0x8)
    class UNiagaraComponent* WheelDustR5;                                             // 0x02E0 (size: 0x8)
    class UNiagaraComponent* WheelDustR4;                                             // 0x02E8 (size: 0x8)
    class UNiagaraComponent* WheelDustR3;                                             // 0x02F0 (size: 0x8)
    class UNiagaraComponent* WheelDustR2;                                             // 0x02F8 (size: 0x8)
    class UNiagaraComponent* WheelDustR1;                                             // 0x0300 (size: 0x8)
    class UStaticMeshComponent* DamagedModel;                                         // 0x0308 (size: 0x8)
    class USkeletalMeshComponent* SkeletalMesh;                                       // 0x0310 (size: 0x8)
    class UABP_West_MLRS_M270_C* AnimInstance;                                        // 0x0318 (size: 0x8)
    class UMaterialInstanceDynamic* BodyMaterial;                                     // 0x0320 (size: 0x8)
    class UMaterialInstanceDynamic* TracksMaterial;                                   // 0x0328 (size: 0x8)

    void UserConstructionScript();
    void SetShowDamaged(bool ShowDamage);
    void SetWheelSpeed(double WheelsSpeed);
    void SetWheelSmokeIntensity(double Intensity);
    void SetDoors(double DoorsAngle);
    void SetDoorHatches(double DoorHatchesAngle);
    void SetSkinType(double SkinType);
    void SetFrontHatches(double FrontHatchesAngle);
    void SetRoofHatch(double RoofHatchAngle);
    void SetLightsEmissivity(double LightEmissivity);
    void SetRocketLauncherRotation(double RocketLauncherRotation);
    void ReceiveBeginPlay();
    void SetRocketLauncherElevation(double RocketLauncherElevation);
    void ExecuteUbergraph_BP_West_MLRS_M270(int32 EntryPoint);
}; // Size: 0x330

#endif
