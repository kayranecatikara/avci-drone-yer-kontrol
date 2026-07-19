#ifndef UE4SS_SDK_BPP_UAV_HPP
#define UE4SS_SDK_BPP_UAV_HPP

class ABPP_UAV_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UArrowComponent* MovementDirection;                                         // 0x0330 (size: 0x8)
    class UStaticMeshComponent* SM_UAV;                                               // 0x0338 (size: 0x8)
    class UArrowComponent* GlobalFrontDirection;                                      // 0x0340 (size: 0x8)
    class UNiagaraComponent* NS_Fiber;                                                // 0x0348 (size: 0x8)
    class USceneCaptureComponent2D* SceneCaptureComponent2D;                          // 0x0350 (size: 0x8)
    class UParticleSystemComponent* ParticleSystem_Rain;                              // 0x0358 (size: 0x8)
    class UNiagaraComponent* Niagara_Snow;                                            // 0x0360 (size: 0x8)
    class UBoxComponent* COL_Interact;                                                // 0x0368 (size: 0x8)
    class UCineCameraComponent* CineCamera;                                           // 0x0370 (size: 0x8)
    class UAudioComponent* DroneEngine;                                               // 0x0378 (size: 0x8)
    class UStaticMeshComponent* SM_ParentMesh;                                        // 0x0380 (size: 0x8)
    class USpringArmComponent* SpringArm;                                             // 0x0388 (size: 0x8)
    float Timeline_0_NewTrack_0_BBAE549246028493CBFB7DB582FAD51F;                     // 0x0390 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline_0__Direction_BBAE549246028493CBFB7DB582FAD51F; // 0x0394 (size: 0x1)
    class UTimelineComponent* Timeline_0;                                             // 0x0398 (size: 0x8)
    float Timeline_Alpha_A6750D194769452E56EB099C97026911;                            // 0x03A0 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline__Direction_A6750D194769452E56EB099C97026911; // 0x03A4 (size: 0x1)
    class UTimelineComponent* Timeline;                                               // 0x03A8 (size: 0x8)
    double CurrentSpeed;                                                              // 0x03B0 (size: 0x8)
    double MaxSpeed;                                                                  // 0x03B8 (size: 0x8)
    bool IsFlipped;                                                                   // 0x03C0 (size: 0x1)
    bool isGround;                                                                    // 0x03C1 (size: 0x1)
    double Altitude;                                                                  // 0x03C8 (size: 0x8)
    TEnumAsByte<E_GameMode::Type> E Game Mode;                                        // 0x03D0 (size: 0x1)
    double RC Expo Roll;                                                              // 0x03D8 (size: 0x8)
    class AHUD_MainUAV_C* HUD Main UAV;                                               // 0x03E0 (size: 0x8)
    double Roll Axis Speed;                                                           // 0x03E8 (size: 0x8)
    double Pitch Axis Speed;                                                          // 0x03F0 (size: 0x8)
    double Yaw Axis Speed;                                                            // 0x03F8 (size: 0x8)
    double RC Expo Yaw;                                                               // 0x0400 (size: 0x8)
    double RC Expo Pitch;                                                             // 0x0408 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0410 (size: 0x8)
    FTransform InitialTransform;                                                      // 0x0420 (size: 0x60)
    double Reverse Roll Axis;                                                         // 0x0480 (size: 0x8)
    double Reverse Pitch Axis;                                                        // 0x0488 (size: 0x8)
    double Reverse Yaw Axis;                                                          // 0x0490 (size: 0x8)
    double Reverse Throttle Axis;                                                     // 0x0498 (size: 0x8)
    double FirstBatteryStart;                                                         // 0x04A0 (size: 0x8)
    double FirstBatteryEnd;                                                           // 0x04A8 (size: 0x8)
    double CurrentBatteryCounter;                                                     // 0x04B0 (size: 0x8)
    double SecondBatteryStart;                                                        // 0x04B8 (size: 0x8)
    double SecondBatteryEnd;                                                          // 0x04C0 (size: 0x8)
    double BatteryDurationPower;                                                      // 0x04C8 (size: 0x8)
    class AActor* LockTargetActor;                                                    // 0x04D0 (size: 0x8)
    FCameraFocusSettings LockFocusSettings;                                           // 0x04D8 (size: 0x60)
    bool IsLocked;                                                                    // 0x0538 (size: 0x1)
    bool isLockMoving;                                                                // 0x0539 (size: 0x1)
    bool isRespawn;                                                                   // 0x053A (size: 0x1)
    class APawn* Spec Pawn;                                                           // 0x0540 (size: 0x8)
    TEnumAsByte<E_Controller::Type> EController;                                      // 0x0548 (size: 0x1)
    TEnumAsByte<E_ExplosiveType::Type> EExplosiveType;                                // 0x0549 (size: 0x1)
    bool canUseThermal;                                                               // 0x054A (size: 0x1)
    bool canUseLockKit;                                                               // 0x054B (size: 0x1)
    TEnumAsByte<E_MapMode::Type> EMapMode;                                            // 0x054C (size: 0x1)
    double JammerCurrentInput;                                                        // 0x0550 (size: 0x8)
    double FieldOfView;                                                               // 0x0558 (size: 0x8)
    double ExplosiveWeight;                                                           // 0x0560 (size: 0x8)
    bool isEngineOn;                                                                  // 0x0568 (size: 0x1)
    bool isOpenTermal;                                                                // 0x0569 (size: 0x1)
    class UMaterialInstanceDynamic* M_Glitch;                                         // 0x0570 (size: 0x8)
    class ABP_AI_EnemySoldier_C* BP AI Controller;                                    // 0x0578 (size: 0x8)
    bool canPushImpact;                                                               // 0x0580 (size: 0x1)
    bool isTriggerReady;                                                              // 0x0581 (size: 0x1)
    double RollAxisInput;                                                             // 0x0588 (size: 0x8)
    double PitchAxisInput;                                                            // 0x0590 (size: 0x8)
    double YawAxisInput;                                                              // 0x0598 (size: 0x8)
    double ThrottleAxisInput;                                                         // 0x05A0 (size: 0x8)
    double TriggerActionInput;                                                        // 0x05A8 (size: 0x8)
    double DeadZone;                                                                  // 0x05B0 (size: 0x8)
    double ImpactActionInput;                                                         // 0x05B8 (size: 0x8)
    float LockKitActionInput;                                                         // 0x05C0 (size: 0x4)
    float ThermalActionInput;                                                         // 0x05C4 (size: 0x4)
    double ArmActionInput;                                                            // 0x05C8 (size: 0x8)
    float RespawnActionInput;                                                         // 0x05D0 (size: 0x4)
    double PropwashTimer;                                                             // 0x05D8 (size: 0x8)
    bool canPropwash;                                                                 // 0x05E0 (size: 0x1)
    bool isActiveThermalButton;                                                       // 0x05E1 (size: 0x1)
    bool isActiveLockKitButton;                                                       // 0x05E2 (size: 0x1)
    float MousePitch;                                                                 // 0x05E4 (size: 0x4)
    float MouseRoll;                                                                  // 0x05E8 (size: 0x4)
    float KeybaordThrottle;                                                           // 0x05EC (size: 0x4)
    float KeyboardYaw;                                                                // 0x05F0 (size: 0x4)
    double DistanceToInitialLocation;                                                 // 0x05F8 (size: 0x8)
    bool canRopeBroke;                                                                // 0x0600 (size: 0x1)
    double RopeBrokeTimer;                                                            // 0x0608 (size: 0x8)
    double CurrentMaxFiberDistance;                                                   // 0x0610 (size: 0x8)
    bool isBrokeFiber;                                                                // 0x0618 (size: 0x1)
    double CurrentFiberDistance;                                                      // 0x0620 (size: 0x8)
    double BatteryFillAmount;                                                         // 0x0628 (size: 0x8)
    FBPP_UAV_CRestartDrone RestartDrone;                                              // 0x0630 (size: 0x10)
    void RestartDrone();
    TEnumAsByte<E_UAVPositionMode::Type> E UAV Position Mode;                         // 0x0640 (size: 0x1)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x0648 (size: 0x8)
    double ExplosionEffectScaleMultiply;                                              // 0x0650 (size: 0x8)
    class UDataTable* DT UAV;                                                         // 0x0658 (size: 0x8)
    TEnumAsByte<E_UAV::Type> UAV;                                                     // 0x0660 (size: 0x1)
    double Max Speed Train;                                                           // 0x0668 (size: 0x8)
    double Max Speed Attack;                                                          // 0x0670 (size: 0x8)
    double Explosion Heavy Radius;                                                    // 0x0678 (size: 0x8)
    FVector Explosion Effect Scale;                                                   // 0x0680 (size: 0x18)
    double Explosion Effect Scale Multiply;                                           // 0x0698 (size: 0x8)
    double Propeller Rotate Speed;                                                    // 0x06A0 (size: 0x8)
    double Lock Distance;                                                             // 0x06A8 (size: 0x8)
    double Propwash Duration;                                                         // 0x06B0 (size: 0x8)
    double Jammer Action Input;                                                       // 0x06B8 (size: 0x8)
    double Jammer Default Input;                                                      // 0x06C0 (size: 0x8)
    double Rope Broke Duration;                                                       // 0x06C8 (size: 0x8)
    double Fiber 5KMDistance;                                                         // 0x06D0 (size: 0x8)
    double Fiber 10KMDistance;                                                        // 0x06D8 (size: 0x8)
    double Battery Duration;                                                          // 0x06E0 (size: 0x8)
    FPostProcessSettings PPThermal;                                                   // 0x06F0 (size: 0x700)
    FPostProcessSettings PPNormal;                                                    // 0x0DF0 (size: 0x700)
    FPostProcessSettings PPOutside First Phase;                                       // 0x14F0 (size: 0x700)
    FPostProcessSettings PPOutside Second Phase;                                      // 0x1BF0 (size: 0x700)
    double Explosion Personal Radius;                                                 // 0x22F0 (size: 0x8)
    double MinEngineSoundPitch;                                                       // 0x22F8 (size: 0x8)
    double MaxEngineSoundPitch;                                                       // 0x2300 (size: 0x8)
    double Mass;                                                                      // 0x2308 (size: 0x8)
    double Explosion Weight;                                                          // 0x2310 (size: 0x8)
    FS_BatteryPhaseValue Battery Information First Phase 1;                           // 0x2318 (size: 0x28)
    FS_BatteryPhaseValue Battery Information First Phase 2;                           // 0x2340 (size: 0x28)
    FS_BatteryPhaseValue Battery Information First Phase 3;                           // 0x2368 (size: 0x28)
    FS_BatteryPhaseValue Battery Information First Phase 4;                           // 0x2390 (size: 0x28)
    int32 BatteryPhase;                                                               // 0x23B8 (size: 0x4)

    void NormalizeDeadzone(double Input, double& Output);
    void Drone Explosion Effect(bool isArena);
    void Deactive UAV();
    void Active UAV(class APawn* Spec Pawn);
    void Set Trace for Lock Target(bool& is Hit);
    void Set Max Speed(double Speed);
    void Timeline__FinishedFunc();
    void Timeline__UpdateFunc();
    void Timeline_0__FinishedFunc();
    void Timeline_0__UpdateFunc();
    void InpActEvt_Two_K2Node_InputKeyEvent_10(FKey Key);
    void InpActEvt_One_K2Node_InputKeyEvent_9(FKey Key);
    void InpActEvt_One_K2Node_InputKeyEvent_8(FKey Key);
    void leftDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856();
    void leftDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856();
    void rightDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856();
    void rightDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856();
    void topDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856();
    void topDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856();
    void bottomDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856();
    void bottomDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856();
    void leftReleased_425BC56D4C171681E860E88B9871C4DD();
    void leftPressed_425BC56D4C171681E860E88B9871C4DD();
    void rightReleased_425BC56D4C171681E860E88B9871C4DD();
    void rightPressed_425BC56D4C171681E860E88B9871C4DD();
    void topReleased_425BC56D4C171681E860E88B9871C4DD();
    void topPressed_425BC56D4C171681E860E88B9871C4DD();
    void bottomReleased_425BC56D4C171681E860E88B9871C4DD();
    void bottomPressed_425BC56D4C171681E860E88B9871C4DD();
    void rightStickY_62DCCD4148EEA0BC332F778043B48922(const float AxisValue);
    void rightStickX_62DCCD4148EEA0BC332F778043B48922(const float AxisValue);
    void leftStickY_62DCCD4148EEA0BC332F778043B48922(const float AxisValue);
    void leftStickX_62DCCD4148EEA0BC332F778043B48922(const float AxisValue);
    void InpActEvt_Y_K2Node_InputKeyEvent_7(FKey Key);
    void actionReleased_1A31509C41A7CB6CAA3689AC137697B5();
    void actionPressed_1A31509C41A7CB6CAA3689AC137697B5();
    void actionReleased_A03D830243A26BA9AD376BB8EF9EF1D2();
    void actionPressed_A03D830243A26BA9AD376BB8EF9EF1D2();
    void actionReleased_9A20994841EA3A0A5E6A8BA003F0944D();
    void actionPressed_9A20994841EA3A0A5E6A8BA003F0944D();
    void actionReleased_6A6101CC47F684910BDB03AD6ED464A4();
    void actionPressed_6A6101CC47F684910BDB03AD6ED464A4();
    void actionReleased_B313AC7143F4C61E97F8E2B14E0E870D();
    void actionPressed_B313AC7143F4C61E97F8E2B14E0E870D();
    void actionReleased_CC76B9F74031A459C36D4DB328DC0EFF();
    void actionPressed_CC76B9F74031A459C36D4DB328DC0EFF();
    void InpActEvt_T_K2Node_InputKeyEvent_6(FKey Key);
    void InpActEvt_R_K2Node_InputKeyEvent_5(FKey Key);
    void InpActEvt_R_K2Node_InputKeyEvent_4(FKey Key);
    void InpActEvt_Tab_K2Node_InputKeyEvent_3(FKey Key);
    void InpActEvt_Tab_K2Node_InputKeyEvent_2(FKey Key);
    void InpActEvt_Escape_K2Node_InputKeyEvent_1(FKey Key);
    void onAction_85DDBACC4039145C06BCE3B1FD23366A(const float AxisValue);
    void onAction_0E56CA72472F7431F923D7BFEC04D34E(const float AxisValue);
    void onAction_EA4EE0DA4CF7F8D938FB61BBFF74C8DF(const float AxisValue);
    void onAction_7BBEF8FF4169CC94CD29AC979C7269BA(const float AxisValue);
    void onAction_A5D7E7B641FED698A4F4849989958571(const float AxisValue);
    void onAction_8D20E44044B024F8C373F5B16D9A28B8(const float AxisValue);
    void InpActEvt_F_K2Node_InputKeyEvent_0(FKey Key);
    void failed_7349D12049F5FB6364A27AAA482A4E4B();
    void successful_7349D12049F5FB6364A27AAA482A4E4B();
    void onAction_44B963FF42A4985ECD88E4B505E9AB80(const float AxisValue);
    void onAction_798A68C44B27D99A4B6E209BFF85BA83(const float AxisValue);
    void onAction_CB3B6C624087C3490F98C5BF4B37C38E(const float AxisValue);
    void onAction_9771145E49CC5CC06F442BA522DE3FC9(const float AxisValue);
    void SetArmedAndText(TEnumAsByte<E_GameMode::Type> E Game Mode, bool IsArmed);
    void SetBPAIController(class ABP_AI_EnemySoldier_C* Input);
    void CameraShakeEffect();
    void ExplosiveDecal();
    void SetFieldOfView(double FieldOfView);
    void ShowParasiteEffect(bool isShow);
    void CheckFiberDistance();
    void ShowParasiteEffectOutside();
    void ShowFiberRopeInfo();
    void CallCircleExplosion();
    void SetFlightMode(TEnumAsByte<E_UAV_FlightMode::Type> E UAV Flight Mode);
    void IsActiveJammer(bool IsActive);
    void DestroyWithDelay();
    void BndEvt__BPP_MainDrone_Box_K2Node_ComponentBoundEvent_2_ComponentBeginOverlapSignature__DelegateSignature(class UPrimitiveComponent* OverlappedComponent, class AActor* OtherActor, class UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    void SoundForSpeed(double Value, double Roll, double Pitch, double Yaw);
    void SetThermalProcessAndFOV(bool IsActive);
    void InitializeCustomize();
    void RestartGame(float Duration);
    void ChangeFlightMode();
    void LockKitButton(bool IsPressed);
    void ThermalButton(bool IsPressed);
    void InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_0(float AxisValue);
    void InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_1(float AxisValue);
    void InpAxisEvt_I_KeyboardYaw_K2Node_InputAxisEvent_3(float AxisValue);
    void InpAxisEvt_I_KeyboardThrottle_K2Node_InputAxisEvent_2(float AxisValue);
    void ReceiveTick(float DeltaSeconds);
    void ReceiveBeginPlay();
    void TriggerAction(double AmmunitionAction);
    void PushImpactAction(double PushImpactAction);
    void LockKitAction(float LockKitAction);
    void RespawnAction(float RespawnAction);
    void ThermalAction(float ThermalAction);
    void ArmAction(double ArmedAction);
    void MovementThrottleAxis(double MovementThrottleAxis);
    void MovementYawAxis(double MovementYawAxis);
    void MovementRollAxis(double RollAxisInput);
    void MovementPitchAxis(double PitchAxisInput);
    void ShowTriggerInfo();
    void TargetLockUI();
    void CheckCanPropwash();
    void CheckCanFiberRope();
    void AnalogGlitch();
    void RestartBatteryValues();
    void Reset Battery();
    void BatteryTimer();
    void CheckOnGround();
    void AltitudeDistance();
    void UpdateDistanceToInitialLocation();
    void CheckFlipAndRevert();
    void IsGroundCheck();
    void ExecuteUbergraph_BPP_UAV(int32 EntryPoint);
    void RestartDrone__DelegateSignature();
}; // Size: 0x23BC

#endif
