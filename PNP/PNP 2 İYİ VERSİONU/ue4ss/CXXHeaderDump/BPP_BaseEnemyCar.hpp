#ifndef UE4SS_SDK_BPP_BaseEnemyCar_HPP
#define UE4SS_SDK_BPP_BaseEnemyCar_HPP

class ABPP_BaseEnemyCar_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UBoxComponent* COL_TargetLock_;                                             // 0x0330 (size: 0x8)
    class UAudioComponent* S_Truck;                                                   // 0x0338 (size: 0x8)
    class UAudioComponent* S_Helicopter;                                              // 0x0340 (size: 0x8)
    class UAudioComponent* S_Pickup;                                                  // 0x0348 (size: 0x8)
    class UAudioComponent* S_WeaponFireEastyArty;                                     // 0x0350 (size: 0x8)
    class UAudioComponent* S_WeaponFireTank;                                          // 0x0358 (size: 0x8)
    class USphereComponent* COL_PersonalExplosive;                                    // 0x0360 (size: 0x8)
    class UParticleSystemComponent* Particle_Fire;                                    // 0x0368 (size: 0x8)
    class UParticleSystemComponent* EastArty_GunFire;                                 // 0x0370 (size: 0x8)
    class UParticleSystemComponent* EastSpg_GunFire;                                  // 0x0378 (size: 0x8)
    class UBPC_AIMove_C* BPC_AIMove;                                                  // 0x0380 (size: 0x8)
    class UNiagaraComponent* FrontLeft;                                               // 0x0388 (size: 0x8)
    class UNiagaraComponent* FrontRight;                                              // 0x0390 (size: 0x8)
    class UNiagaraComponent* FLWheelDust;                                             // 0x0398 (size: 0x8)
    class UNiagaraComponent* RearLeft;                                                // 0x03A0 (size: 0x8)
    class UNiagaraComponent* RearRight;                                               // 0x03A8 (size: 0x8)
    class UNiagaraComponent* DamagedSmoke;                                            // 0x03B0 (size: 0x8)
    class UNiagaraComponent* RLWheelDust;                                             // 0x03B8 (size: 0x8)
    class UStaticMeshComponent* DamagedModel;                                         // 0x03C0 (size: 0x8)
    class UNiagaraComponent* FRWheelDust;                                             // 0x03C8 (size: 0x8)
    class UNiagaraComponent* RRWheelDust;                                             // 0x03D0 (size: 0x8)
    class USkeletalMeshComponent* SkeletalMesh;                                       // 0x03D8 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x03E0 (size: 0x8)
    class UABP_East_LUV_3151_C* Car Anim Instance;                                    // 0x03E8 (size: 0x8)
    class ABP_Spline_C* Spline;                                                       // 0x03F0 (size: 0x8)
    double Speed;                                                                     // 0x03F8 (size: 0x8)
    double DistanceAlongSpline;                                                       // 0x0400 (size: 0x8)
    bool isLoop;                                                                      // 0x0408 (size: 0x1)
    double Wheels Speed;                                                              // 0x0410 (size: 0x8)
    class UMaterialInstanceDynamic* BodyMaterial1;                                    // 0x0418 (size: 0x8)
    double Skin Type;                                                                 // 0x0420 (size: 0x8)
    class USkeletalMesh* Skeletal Mesh Asset;                                         // 0x0428 (size: 0x8)
    UClass* Anim Class;                                                               // 0x0430 (size: 0x8)
    class UStaticMesh* Damaged Static Mesh;                                           // 0x0438 (size: 0x8)
    class UABP_West_Heli_AH64D_C* Helicopter Anim Instance;                           // 0x0440 (size: 0x8)
    TEnumAsByte<E_EnemyCarType::Type> Wehicle Type;                                   // 0x0448 (size: 0x1)
    double Smoke Intensity;                                                           // 0x0450 (size: 0x8)
    double Rotor Speed;                                                               // 0x0458 (size: 0x8)
    double Pitch Rotation Angle;                                                      // 0x0460 (size: 0x8)
    class UABP_West_MLRS_M270_C* ABP West MLRS M270;                                  // 0x0468 (size: 0x8)
    double Rocket Launcher Rotation;                                                  // 0x0470 (size: 0x8)
    double Rocket Launcher Elevation;                                                 // 0x0478 (size: 0x8)
    class UABP_East_SPG_2S3Akatsia_C* ABP East SPG 2S3Akatsia;                        // 0x0480 (size: 0x8)
    double SPG Turret Rotation;                                                       // 0x0488 (size: 0x8)
    double SPG Gun Elevation;                                                         // 0x0490 (size: 0x8)
    class UABP_East_Arty_ZU23_C* ABP East Arty ZU23;                                  // 0x0498 (size: 0x8)
    double EastArtySuspensionAngle;                                                   // 0x04A0 (size: 0x8)
    double EastArtyGunElevation;                                                      // 0x04A8 (size: 0x8)
    double EastArtyTurrentRotation;                                                   // 0x04B0 (size: 0x8)
    class UABP_East_Command_9S552_C* ABP East Command 9S552;                          // 0x04B8 (size: 0x8)
    class UMaterialInterface* Wehicle  Material;                                      // 0x04C0 (size: 0x8)
    FTimerHandle FireActionHandle;                                                    // 0x04C8 (size: 0x8)
    double Yaw Rotation Angle;                                                        // 0x04D0 (size: 0x8)
    FVector Mesh Scale;                                                               // 0x04D8 (size: 0x18)
    float Ammunition Sphere Radius;                                                   // 0x04F0 (size: 0x4)
    class UBP_GameInstance_C* AGame Instance;                                         // 0x04F8 (size: 0x8)
    TEnumAsByte<E_ExplosiveType::Type> EExplosive Type;                               // 0x0500 (size: 0x1)
    bool isDead;                                                                      // 0x0501 (size: 0x1)
    FVector TargetLockScale;                                                          // 0x0508 (size: 0x18)
    FVector TargetLockLocation;                                                       // 0x0520 (size: 0x18)
    double Health;                                                                    // 0x0538 (size: 0x8)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x0540 (size: 0x8)

    void SetWheelSmokeIntensity(double Intensity);
    void UserConstructionScript();
    void SetWheelAngle(double Angle);
    void SetShowDamaged(bool ShowDamage);
    void SetSkinType(double SkinType);
    void Dead();
    void Set Settings(TEnumAsByte<E_EnemyCarType::Type> WehicleType, bool ShowDamage, double SkinType);
    void SetWheelSmokeIntensity2(double Intensity);
    void ReceiveBeginPlay();
    void SetMainRotorSpeed(double MainRotorSpeed);
    void SetTailRotorSpeed(double TailRotorSpeed);
    void SetWheelSpeed(double WheelsSpeed);
    void SetRocketLauncherRotation(double RocketLauncherRotation);
    void SetRocketLauncherElevation(double RocketLauncherElevation);
    void SPG Turret Angle(double TurretRotation, double GunElevation);
    void Set Turrent Rotation(double Angle);
    void Set Gun Elevation(double Angle);
    void Suspension angle(double Angle);
    void CommandWheels(double Speed);
    void PlayMuzzleFlash();
    void FireEastSPG(bool IsChecked, class UActorComponent* GunFire);
    void MyInteract();
    void BndEvt__BPP_BaseEnemyCar_COL_Ammunition_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(class UPrimitiveComponent* OverlappedComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void InteractDrone(class ABPP_UAV_C* Target);
    void Interact(class ABPP_UAV_C* BPP Drone Base);
    void ExecuteUbergraph_BPP_BaseEnemyCar(int32 EntryPoint);
}; // Size: 0x548

#endif
