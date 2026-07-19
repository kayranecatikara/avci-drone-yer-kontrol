---@meta

---@class ABP_West_MLRS_M270_C : AActor
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DamagedSmokeFX UNiagaraComponent
---@field WheelDustL5 UNiagaraComponent
---@field WheelDustL4 UNiagaraComponent
---@field WheelDustL3 UNiagaraComponent
---@field WheelDustL2 UNiagaraComponent
---@field WheelDustL1 UNiagaraComponent
---@field WheelDustR5 UNiagaraComponent
---@field WheelDustR4 UNiagaraComponent
---@field WheelDustR3 UNiagaraComponent
---@field WheelDustR2 UNiagaraComponent
---@field WheelDustR1 UNiagaraComponent
---@field DamagedModel UStaticMeshComponent
---@field SkeletalMesh USkeletalMeshComponent
---@field AnimInstance UABP_West_MLRS_M270_C
---@field BodyMaterial UMaterialInstanceDynamic
---@field TracksMaterial UMaterialInstanceDynamic
local ABP_West_MLRS_M270_C = {}

function ABP_West_MLRS_M270_C:UserConstructionScript() end
---@param ShowDamage boolean
function ABP_West_MLRS_M270_C:SetShowDamaged(ShowDamage) end
---@param WheelsSpeed double
function ABP_West_MLRS_M270_C:SetWheelSpeed(WheelsSpeed) end
---@param Intensity double
function ABP_West_MLRS_M270_C:SetWheelSmokeIntensity(Intensity) end
---@param DoorsAngle double
function ABP_West_MLRS_M270_C:SetDoors(DoorsAngle) end
---@param DoorHatchesAngle double
function ABP_West_MLRS_M270_C:SetDoorHatches(DoorHatchesAngle) end
---@param SkinType double
function ABP_West_MLRS_M270_C:SetSkinType(SkinType) end
---@param FrontHatchesAngle double
function ABP_West_MLRS_M270_C:SetFrontHatches(FrontHatchesAngle) end
---@param RoofHatchAngle double
function ABP_West_MLRS_M270_C:SetRoofHatch(RoofHatchAngle) end
---@param LightEmissivity double
function ABP_West_MLRS_M270_C:SetLightsEmissivity(LightEmissivity) end
---@param RocketLauncherRotation double
function ABP_West_MLRS_M270_C:SetRocketLauncherRotation(RocketLauncherRotation) end
function ABP_West_MLRS_M270_C:ReceiveBeginPlay() end
---@param RocketLauncherElevation double
function ABP_West_MLRS_M270_C:SetRocketLauncherElevation(RocketLauncherElevation) end
---@param EntryPoint int32
function ABP_West_MLRS_M270_C:ExecuteUbergraph_BP_West_MLRS_M270(EntryPoint) end


