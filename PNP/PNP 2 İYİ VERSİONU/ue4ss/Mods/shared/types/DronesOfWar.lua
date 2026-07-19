---@meta

---@class FDroneInputData
---@field Throttle float
---@field Pitch float
---@field Roll float
---@field Yaw float
---@field bArmed boolean
local FDroneInputData = {}



---@class UBankingComponent : UActorComponent
---@field BankingSensitivity float
---@field MaxRoll float
---@field InterpSpeed float
---@field TargetMesh USceneComponent
local UBankingComponent = {}



---@class UDroneAngleFlightComponent : UActorComponent
---@field TargetBody UPrimitiveComponent
---@field MaxThrustAcceleration float
---@field MaxHorizontalSpeed float
---@field ClimbVelGain float
---@field bCompensateGravity boolean
---@field YawRateDegPerSec float
---@field bInvertPitch boolean
---@field bInvertRoll boolean
---@field bRequireArmedForThrust boolean
---@field TCPController UDroneTCPController
local UDroneAngleFlightComponent = {}



---@class UDroneTCPController : UActorComponent
---@field CurrentInput FDroneInputData
---@field Port int32
---@field TargetActor AActor
---@field bSuppressLocalKeysWhilePythonConnected boolean
---@field RollPitchTiltAngle float
---@field RollPitchTiltSpeed float
---@field MaxClimbSpeed float
---@field bSendDebugGroundTruth boolean
local UDroneTCPController = {}

function UDroneTCPController:DroneConnect() end


---@class USpectatorTrackingComponent : UActorComponent
---@field bIsTracking boolean
---@field TrackingTarget AActor
---@field TrackingInterpSpeed float
---@field CineCameraComp UCineCameraComponent
local USpectatorTrackingComponent = {}

function USpectatorTrackingComponent:StopTracking() end
---@param NewTarget AActor
function USpectatorTrackingComponent:StartTracking(NewTarget) end
---@param BlendSpeed float
function USpectatorTrackingComponent:ActivateCinematicView(BlendSpeed) end


---@class UTalonCrashComponent : UActorComponent
---@field bIsCrashed boolean
---@field SpinSpeed float
---@field LookDownSpeed float
---@field ForwardDamping float
local UTalonCrashComponent = {}

---@param HitComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param NormalImpulse FVector
---@param Hit FHitResult
function UTalonCrashComponent:OnTalonHit(HitComponent, OtherActor, OtherComp, NormalImpulse, Hit) end


---@class UTalonGPSSpoofComponent : UActorComponent
---@field bEnableGPSCorruption boolean
---@field bEnableNoise boolean
---@field PositionNoiseMeters float
---@field bEnableSpeedNoise boolean
---@field SpeedNoiseMetersPerSec float
---@field SpeedNoisePercent float
---@field bEnableConstantOffset boolean
---@field OffsetStartDelaySeconds float
---@field ConstantOffsetMeters FVector
---@field bEnableJumps boolean
---@field JumpIntervalSeconds float
---@field JumpDurationSeconds float
---@field JumpMagnitudeMeters float
---@field bEnableDropout boolean
---@field DropoutStartSeconds float
---@field DropoutDurationSeconds float
---@field DropoutRepeatIntervalSeconds float
---@field bEnableDelay boolean
---@field DelaySeconds float
---@field bLimitUpdateRate boolean
---@field UpdateRateHz float
---@field CurrentSpoofedLocation FVector
---@field CurrentSpoofedSpeed float
---@field CurrentTrueLocation FVector
---@field CurrentTrueSpeed float
---@field bNoiseActiveNow boolean
---@field bSpeedNoiseActiveNow boolean
---@field bOffsetActiveNow boolean
---@field bJumpActiveNow boolean
---@field bDropoutActiveNow boolean
---@field bRateLimitActiveNow boolean
---@field bDelayActiveNow boolean
---@field ActiveCorruptionMask int32
---@field ElapsedSeconds float
---@field OffsetActiveSeconds float
---@field JumpRemainingSeconds float
---@field DropoutRemainingSeconds float
local UTalonGPSSpoofComponent = {}

---@return int32
function UTalonGPSSpoofComponent:GetActiveCorruptionMask() end


