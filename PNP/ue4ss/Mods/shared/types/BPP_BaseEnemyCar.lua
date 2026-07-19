---@meta

---@class ABPP_BaseEnemyCar_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field COL_TargetLock_ UBoxComponent
---@field S_Truck UAudioComponent
---@field S_Helicopter UAudioComponent
---@field S_Pickup UAudioComponent
---@field S_WeaponFireEastyArty UAudioComponent
---@field S_WeaponFireTank UAudioComponent
---@field COL_PersonalExplosive USphereComponent
---@field Particle_Fire UParticleSystemComponent
---@field EastArty_GunFire UParticleSystemComponent
---@field EastSpg_GunFire UParticleSystemComponent
---@field BPC_AIMove UBPC_AIMove_C
---@field FrontLeft UNiagaraComponent
---@field FrontRight UNiagaraComponent
---@field FLWheelDust UNiagaraComponent
---@field RearLeft UNiagaraComponent
---@field RearRight UNiagaraComponent
---@field DamagedSmoke UNiagaraComponent
---@field RLWheelDust UNiagaraComponent
---@field DamagedModel UStaticMeshComponent
---@field FRWheelDust UNiagaraComponent
---@field RRWheelDust UNiagaraComponent
---@field SkeletalMesh USkeletalMeshComponent
---@field DefaultSceneRoot USceneComponent
---@field ['Car Anim Instance'] UABP_East_LUV_3151_C
---@field Spline ABP_Spline_C
---@field Speed double
---@field DistanceAlongSpline double
---@field isLoop boolean
---@field ['Wheels Speed'] double
---@field BodyMaterial1 UMaterialInstanceDynamic
---@field ['Skin Type'] double
---@field ['Skeletal Mesh Asset'] USkeletalMesh
---@field ['Anim Class'] UClass
---@field ['Damaged Static Mesh'] UStaticMesh
---@field ['Helicopter Anim Instance'] UABP_West_Heli_AH64D_C
---@field ['Wehicle Type'] E_EnemyCarType::Type
---@field ['Smoke Intensity'] double
---@field ['Rotor Speed'] double
---@field ['Pitch Rotation Angle'] double
---@field ['ABP West MLRS M270'] UABP_West_MLRS_M270_C
---@field ['Rocket Launcher Rotation'] double
---@field ['Rocket Launcher Elevation'] double
---@field ['ABP East SPG 2S3Akatsia'] UABP_East_SPG_2S3Akatsia_C
---@field ['SPG Turret Rotation'] double
---@field ['SPG Gun Elevation'] double
---@field ['ABP East Arty ZU23'] UABP_East_Arty_ZU23_C
---@field EastArtySuspensionAngle double
---@field EastArtyGunElevation double
---@field EastArtyTurrentRotation double
---@field ['ABP East Command 9S552'] UABP_East_Command_9S552_C
---@field ['Wehicle  Material'] UMaterialInterface
---@field FireActionHandle FTimerHandle
---@field ['Yaw Rotation Angle'] double
---@field ['Mesh Scale'] FVector
---@field ['Ammunition Sphere Radius'] float
---@field ['AGame Instance'] UBP_GameInstance_C
---@field ['EExplosive Type'] E_ExplosiveType::Type
---@field isDead boolean
---@field TargetLockScale FVector
---@field TargetLockLocation FVector
---@field Health double
---@field ['GM UAV Base'] AGM_UAVBase_C
local ABPP_BaseEnemyCar_C = {}

---@param Intensity double
function ABPP_BaseEnemyCar_C:SetWheelSmokeIntensity(Intensity) end
function ABPP_BaseEnemyCar_C:UserConstructionScript() end
---@param Angle double
function ABPP_BaseEnemyCar_C:SetWheelAngle(Angle) end
---@param ShowDamage boolean
function ABPP_BaseEnemyCar_C:SetShowDamaged(ShowDamage) end
---@param SkinType double
function ABPP_BaseEnemyCar_C:SetSkinType(SkinType) end
function ABPP_BaseEnemyCar_C:Dead() end
---@param WehicleType E_EnemyCarType::Type
---@param ShowDamage boolean
---@param SkinType double
ABPP_BaseEnemyCar_C['Set Settings'] = function(self, WehicleType, ShowDamage, SkinType) end
---@param Intensity double
function ABPP_BaseEnemyCar_C:SetWheelSmokeIntensity2(Intensity) end
function ABPP_BaseEnemyCar_C:ReceiveBeginPlay() end
---@param MainRotorSpeed double
function ABPP_BaseEnemyCar_C:SetMainRotorSpeed(MainRotorSpeed) end
---@param TailRotorSpeed double
function ABPP_BaseEnemyCar_C:SetTailRotorSpeed(TailRotorSpeed) end
---@param WheelsSpeed double
function ABPP_BaseEnemyCar_C:SetWheelSpeed(WheelsSpeed) end
---@param RocketLauncherRotation double
function ABPP_BaseEnemyCar_C:SetRocketLauncherRotation(RocketLauncherRotation) end
---@param RocketLauncherElevation double
function ABPP_BaseEnemyCar_C:SetRocketLauncherElevation(RocketLauncherElevation) end
---@param TurretRotation double
---@param GunElevation double
ABPP_BaseEnemyCar_C['SPG Turret Angle'] = function(self, TurretRotation, GunElevation) end
---@param Angle double
ABPP_BaseEnemyCar_C['Set Turrent Rotation'] = function(self, Angle) end
---@param Angle double
ABPP_BaseEnemyCar_C['Set Gun Elevation'] = function(self, Angle) end
---@param Angle double
ABPP_BaseEnemyCar_C['Suspension angle'] = function(self, Angle) end
---@param Speed double
function ABPP_BaseEnemyCar_C:CommandWheels(Speed) end
function ABPP_BaseEnemyCar_C:PlayMuzzleFlash() end
---@param IsChecked boolean
---@param GunFire UActorComponent
function ABPP_BaseEnemyCar_C:FireEastSPG(IsChecked, GunFire) end
function ABPP_BaseEnemyCar_C:MyInteract() end
---@param OverlappedComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param OtherBodyIndex int32
---@param bFromSweep boolean
---@param SweepResult FHitResult
function ABPP_BaseEnemyCar_C:BndEvt__BPP_BaseEnemyCar_COL_Ammunition_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult) end
---@param Target ABPP_UAV_C
function ABPP_BaseEnemyCar_C:InteractDrone(Target) end
---@param BPP_Drone_Base ABPP_UAV_C
function ABPP_BaseEnemyCar_C:Interact(BPP_Drone_Base) end
---@param EntryPoint int32
function ABPP_BaseEnemyCar_C:ExecuteUbergraph_BPP_BaseEnemyCar(EntryPoint) end


