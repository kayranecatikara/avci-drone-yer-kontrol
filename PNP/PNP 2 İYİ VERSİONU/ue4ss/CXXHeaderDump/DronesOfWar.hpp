#ifndef UE4SS_SDK_DronesOfWar_HPP
#define UE4SS_SDK_DronesOfWar_HPP

struct FDroneInputData
{
    float Throttle;                                                                   // 0x0000 (size: 0x4)
    float Pitch;                                                                      // 0x0004 (size: 0x4)
    float Roll;                                                                       // 0x0008 (size: 0x4)
    float Yaw;                                                                        // 0x000C (size: 0x4)
    bool bArmed;                                                                      // 0x0010 (size: 0x1)

}; // Size: 0x14

class UBankingComponent : public UActorComponent
{
    float BankingSensitivity;                                                         // 0x00A0 (size: 0x4)
    float MaxRoll;                                                                    // 0x00A4 (size: 0x4)
    float InterpSpeed;                                                                // 0x00A8 (size: 0x4)
    class USceneComponent* TargetMesh;                                                // 0x00B0 (size: 0x8)

}; // Size: 0xC0

class UDroneAngleFlightComponent : public UActorComponent
{
    class UPrimitiveComponent* TargetBody;                                            // 0x00A0 (size: 0x8)
    float MaxThrustAcceleration;                                                      // 0x00A8 (size: 0x4)
    float MaxHorizontalSpeed;                                                         // 0x00AC (size: 0x4)
    float ClimbVelGain;                                                               // 0x00B0 (size: 0x4)
    bool bCompensateGravity;                                                          // 0x00B4 (size: 0x1)
    float YawRateDegPerSec;                                                           // 0x00B8 (size: 0x4)
    bool bInvertPitch;                                                                // 0x00BC (size: 0x1)
    bool bInvertRoll;                                                                 // 0x00BD (size: 0x1)
    bool bRequireArmedForThrust;                                                      // 0x00BE (size: 0x1)
    class UDroneTCPController* TCPController;                                         // 0x00C0 (size: 0x8)

}; // Size: 0xC8

class UDroneTCPController : public UActorComponent
{
    FDroneInputData CurrentInput;                                                     // 0x00A0 (size: 0x14)
    int32 Port;                                                                       // 0x00B4 (size: 0x4)
    class AActor* TargetActor;                                                        // 0x00B8 (size: 0x8)
    bool bSuppressLocalKeysWhilePythonConnected;                                      // 0x00C0 (size: 0x1)
    float RollPitchTiltAngle;                                                         // 0x00C4 (size: 0x4)
    float RollPitchTiltSpeed;                                                         // 0x00C8 (size: 0x4)
    float MaxClimbSpeed;                                                              // 0x00CC (size: 0x4)
    bool bSendDebugGroundTruth;                                                       // 0x00D0 (size: 0x1)

    void DroneConnect();
}; // Size: 0x100

class USpectatorTrackingComponent : public UActorComponent
{
    bool bIsTracking;                                                                 // 0x00A0 (size: 0x1)
    class AActor* TrackingTarget;                                                     // 0x00A8 (size: 0x8)
    float TrackingInterpSpeed;                                                        // 0x00B0 (size: 0x4)
    class UCineCameraComponent* CineCameraComp;                                       // 0x00B8 (size: 0x8)

    void StopTracking();
    void StartTracking(class AActor* NewTarget);
    void ActivateCinematicView(float BlendSpeed);
}; // Size: 0xC0

class UTalonCrashComponent : public UActorComponent
{
    bool bIsCrashed;                                                                  // 0x00A0 (size: 0x1)
    float SpinSpeed;                                                                  // 0x00A4 (size: 0x4)
    float LookDownSpeed;                                                              // 0x00A8 (size: 0x4)
    float ForwardDamping;                                                             // 0x00AC (size: 0x4)

    void OnTalonHit(class UPrimitiveComponent* HitComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);
}; // Size: 0xB0

class UTalonGPSSpoofComponent : public UActorComponent
{
    bool bEnableGPSCorruption;                                                        // 0x00A0 (size: 0x1)
    bool bEnableNoise;                                                                // 0x00A1 (size: 0x1)
    float PositionNoiseMeters;                                                        // 0x00A4 (size: 0x4)
    bool bEnableSpeedNoise;                                                           // 0x00A8 (size: 0x1)
    float SpeedNoiseMetersPerSec;                                                     // 0x00AC (size: 0x4)
    float SpeedNoisePercent;                                                          // 0x00B0 (size: 0x4)
    bool bEnableConstantOffset;                                                       // 0x00B4 (size: 0x1)
    float OffsetStartDelaySeconds;                                                    // 0x00B8 (size: 0x4)
    FVector ConstantOffsetMeters;                                                     // 0x00C0 (size: 0x18)
    bool bEnableJumps;                                                                // 0x00D8 (size: 0x1)
    float JumpIntervalSeconds;                                                        // 0x00DC (size: 0x4)
    float JumpDurationSeconds;                                                        // 0x00E0 (size: 0x4)
    float JumpMagnitudeMeters;                                                        // 0x00E4 (size: 0x4)
    bool bEnableDropout;                                                              // 0x00E8 (size: 0x1)
    float DropoutStartSeconds;                                                        // 0x00EC (size: 0x4)
    float DropoutDurationSeconds;                                                     // 0x00F0 (size: 0x4)
    float DropoutRepeatIntervalSeconds;                                               // 0x00F4 (size: 0x4)
    bool bEnableDelay;                                                                // 0x00F8 (size: 0x1)
    float DelaySeconds;                                                               // 0x00FC (size: 0x4)
    bool bLimitUpdateRate;                                                            // 0x0100 (size: 0x1)
    float UpdateRateHz;                                                               // 0x0104 (size: 0x4)
    FVector CurrentSpoofedLocation;                                                   // 0x0108 (size: 0x18)
    float CurrentSpoofedSpeed;                                                        // 0x0120 (size: 0x4)
    FVector CurrentTrueLocation;                                                      // 0x0128 (size: 0x18)
    float CurrentTrueSpeed;                                                           // 0x0140 (size: 0x4)
    bool bNoiseActiveNow;                                                             // 0x0144 (size: 0x1)
    bool bSpeedNoiseActiveNow;                                                        // 0x0145 (size: 0x1)
    bool bOffsetActiveNow;                                                            // 0x0146 (size: 0x1)
    bool bJumpActiveNow;                                                              // 0x0147 (size: 0x1)
    bool bDropoutActiveNow;                                                           // 0x0148 (size: 0x1)
    bool bRateLimitActiveNow;                                                         // 0x0149 (size: 0x1)
    bool bDelayActiveNow;                                                             // 0x014A (size: 0x1)
    int32 ActiveCorruptionMask;                                                       // 0x014C (size: 0x4)
    float ElapsedSeconds;                                                             // 0x0150 (size: 0x4)
    float OffsetActiveSeconds;                                                        // 0x0154 (size: 0x4)
    float JumpRemainingSeconds;                                                       // 0x0158 (size: 0x4)
    float DropoutRemainingSeconds;                                                    // 0x015C (size: 0x4)

    int32 GetActiveCorruptionMask();
}; // Size: 0x1B8

#endif
