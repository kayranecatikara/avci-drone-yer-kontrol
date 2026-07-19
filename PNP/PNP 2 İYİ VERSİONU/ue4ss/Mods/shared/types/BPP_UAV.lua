---@meta

---@class ABPP_UAV_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field MovementDirection UArrowComponent
---@field SM_UAV UStaticMeshComponent
---@field GlobalFrontDirection UArrowComponent
---@field NS_Fiber UNiagaraComponent
---@field SceneCaptureComponent2D USceneCaptureComponent2D
---@field ParticleSystem_Rain UParticleSystemComponent
---@field Niagara_Snow UNiagaraComponent
---@field COL_Interact UBoxComponent
---@field CineCamera UCineCameraComponent
---@field DroneEngine UAudioComponent
---@field SM_ParentMesh UStaticMeshComponent
---@field SpringArm USpringArmComponent
---@field Timeline_0_NewTrack_0_BBAE549246028493CBFB7DB582FAD51F float
---@field Timeline_0__Direction_BBAE549246028493CBFB7DB582FAD51F ETimelineDirection::Type
---@field Timeline_0 UTimelineComponent
---@field Timeline_Alpha_A6750D194769452E56EB099C97026911 float
---@field Timeline__Direction_A6750D194769452E56EB099C97026911 ETimelineDirection::Type
---@field Timeline UTimelineComponent
---@field CurrentSpeed double
---@field MaxSpeed double
---@field IsFlipped boolean
---@field isGround boolean
---@field Altitude double
---@field ['E Game Mode'] E_GameMode::Type
---@field ['RC Expo Roll'] double
---@field ['HUD Main UAV'] AHUD_MainUAV_C
---@field ['Roll Axis Speed'] double
---@field ['Pitch Axis Speed'] double
---@field ['Yaw Axis Speed'] double
---@field ['RC Expo Yaw'] double
---@field ['RC Expo Pitch'] double
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field InitialTransform FTransform
---@field ['Reverse Roll Axis'] double
---@field ['Reverse Pitch Axis'] double
---@field ['Reverse Yaw Axis'] double
---@field ['Reverse Throttle Axis'] double
---@field FirstBatteryStart double
---@field FirstBatteryEnd double
---@field CurrentBatteryCounter double
---@field SecondBatteryStart double
---@field SecondBatteryEnd double
---@field BatteryDurationPower double
---@field LockTargetActor AActor
---@field LockFocusSettings FCameraFocusSettings
---@field IsLocked boolean
---@field isLockMoving boolean
---@field isRespawn boolean
---@field ['Spec Pawn'] APawn
---@field EController E_Controller::Type
---@field EExplosiveType E_ExplosiveType::Type
---@field canUseThermal boolean
---@field canUseLockKit boolean
---@field EMapMode E_MapMode::Type
---@field JammerCurrentInput double
---@field FieldOfView double
---@field ExplosiveWeight double
---@field isEngineOn boolean
---@field isOpenTermal boolean
---@field M_Glitch UMaterialInstanceDynamic
---@field ['BP AI Controller'] ABP_AI_EnemySoldier_C
---@field canPushImpact boolean
---@field isTriggerReady boolean
---@field RollAxisInput double
---@field PitchAxisInput double
---@field YawAxisInput double
---@field ThrottleAxisInput double
---@field TriggerActionInput double
---@field DeadZone double
---@field ImpactActionInput double
---@field LockKitActionInput float
---@field ThermalActionInput float
---@field ArmActionInput double
---@field RespawnActionInput float
---@field PropwashTimer double
---@field canPropwash boolean
---@field isActiveThermalButton boolean
---@field isActiveLockKitButton boolean
---@field MousePitch float
---@field MouseRoll float
---@field KeybaordThrottle float
---@field KeyboardYaw float
---@field DistanceToInitialLocation double
---@field canRopeBroke boolean
---@field RopeBrokeTimer double
---@field CurrentMaxFiberDistance double
---@field isBrokeFiber boolean
---@field CurrentFiberDistance double
---@field BatteryFillAmount double
---@field RestartDrone FBPP_UAV_CRestartDrone
---@field ['E UAV Position Mode'] E_UAVPositionMode::Type
---@field ['GM UAV Base'] AGM_UAVBase_C
---@field ExplosionEffectScaleMultiply double
---@field ['DT UAV'] UDataTable
---@field UAV E_UAV::Type
---@field ['Max Speed Train'] double
---@field ['Max Speed Attack'] double
---@field ['Explosion Heavy Radius'] double
---@field ['Explosion Effect Scale'] FVector
---@field ['Explosion Effect Scale Multiply'] double
---@field ['Propeller Rotate Speed'] double
---@field ['Lock Distance'] double
---@field ['Propwash Duration'] double
---@field ['Jammer Action Input'] double
---@field ['Jammer Default Input'] double
---@field ['Rope Broke Duration'] double
---@field ['Fiber 5KMDistance'] double
---@field ['Fiber 10KMDistance'] double
---@field ['Battery Duration'] double
---@field PPThermal FPostProcessSettings
---@field PPNormal FPostProcessSettings
---@field ['PPOutside First Phase'] FPostProcessSettings
---@field ['PPOutside Second Phase'] FPostProcessSettings
---@field ['Explosion Personal Radius'] double
---@field MinEngineSoundPitch double
---@field MaxEngineSoundPitch double
---@field Mass double
---@field ['Explosion Weight'] double
---@field ['Battery Information First Phase 1'] FS_BatteryPhaseValue
---@field ['Battery Information First Phase 2'] FS_BatteryPhaseValue
---@field ['Battery Information First Phase 3'] FS_BatteryPhaseValue
---@field ['Battery Information First Phase 4'] FS_BatteryPhaseValue
---@field BatteryPhase int32
local ABPP_UAV_C = {}

---@param Input double
---@param Output double
function ABPP_UAV_C:NormalizeDeadzone(Input, Output) end
---@param isArena boolean
ABPP_UAV_C['Drone Explosion Effect'] = function(self, isArena) end
ABPP_UAV_C['Deactive UAV'] = function(self, ) end
---@param Spec_Pawn APawn
ABPP_UAV_C['Active UAV'] = function(self, Spec_Pawn) end
---@param is_Hit boolean
ABPP_UAV_C['Set Trace for Lock Target'] = function(self, is_Hit) end
---@param Speed double
ABPP_UAV_C['Set Max Speed'] = function(self, Speed) end
function ABPP_UAV_C:Timeline__FinishedFunc() end
function ABPP_UAV_C:Timeline__UpdateFunc() end
function ABPP_UAV_C:Timeline_0__FinishedFunc() end
function ABPP_UAV_C:Timeline_0__UpdateFunc() end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_Two_K2Node_InputKeyEvent_10(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_One_K2Node_InputKeyEvent_9(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_One_K2Node_InputKeyEvent_8(Key) end
function ABPP_UAV_C:leftDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:leftDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:rightDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:rightDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:topDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:topDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:bottomDpadReleased_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:bottomDpadPressed_B6CD13C24E1B8621F252DBB6B27F6856() end
function ABPP_UAV_C:leftReleased_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:leftPressed_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:rightReleased_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:rightPressed_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:topReleased_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:topPressed_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:bottomReleased_425BC56D4C171681E860E88B9871C4DD() end
function ABPP_UAV_C:bottomPressed_425BC56D4C171681E860E88B9871C4DD() end
---@param AxisValue float
function ABPP_UAV_C:rightStickY_62DCCD4148EEA0BC332F778043B48922(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:rightStickX_62DCCD4148EEA0BC332F778043B48922(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:leftStickY_62DCCD4148EEA0BC332F778043B48922(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:leftStickX_62DCCD4148EEA0BC332F778043B48922(AxisValue) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_Y_K2Node_InputKeyEvent_7(Key) end
function ABPP_UAV_C:actionReleased_1A31509C41A7CB6CAA3689AC137697B5() end
function ABPP_UAV_C:actionPressed_1A31509C41A7CB6CAA3689AC137697B5() end
function ABPP_UAV_C:actionReleased_A03D830243A26BA9AD376BB8EF9EF1D2() end
function ABPP_UAV_C:actionPressed_A03D830243A26BA9AD376BB8EF9EF1D2() end
function ABPP_UAV_C:actionReleased_9A20994841EA3A0A5E6A8BA003F0944D() end
function ABPP_UAV_C:actionPressed_9A20994841EA3A0A5E6A8BA003F0944D() end
function ABPP_UAV_C:actionReleased_6A6101CC47F684910BDB03AD6ED464A4() end
function ABPP_UAV_C:actionPressed_6A6101CC47F684910BDB03AD6ED464A4() end
function ABPP_UAV_C:actionReleased_B313AC7143F4C61E97F8E2B14E0E870D() end
function ABPP_UAV_C:actionPressed_B313AC7143F4C61E97F8E2B14E0E870D() end
function ABPP_UAV_C:actionReleased_CC76B9F74031A459C36D4DB328DC0EFF() end
function ABPP_UAV_C:actionPressed_CC76B9F74031A459C36D4DB328DC0EFF() end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_T_K2Node_InputKeyEvent_6(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_R_K2Node_InputKeyEvent_5(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_R_K2Node_InputKeyEvent_4(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_Tab_K2Node_InputKeyEvent_3(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_Tab_K2Node_InputKeyEvent_2(Key) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_Escape_K2Node_InputKeyEvent_1(Key) end
---@param AxisValue float
function ABPP_UAV_C:onAction_85DDBACC4039145C06BCE3B1FD23366A(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_0E56CA72472F7431F923D7BFEC04D34E(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_EA4EE0DA4CF7F8D938FB61BBFF74C8DF(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_7BBEF8FF4169CC94CD29AC979C7269BA(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_A5D7E7B641FED698A4F4849989958571(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_8D20E44044B024F8C373F5B16D9A28B8(AxisValue) end
---@param Key FKey
function ABPP_UAV_C:InpActEvt_F_K2Node_InputKeyEvent_0(Key) end
function ABPP_UAV_C:failed_7349D12049F5FB6364A27AAA482A4E4B() end
function ABPP_UAV_C:successful_7349D12049F5FB6364A27AAA482A4E4B() end
---@param AxisValue float
function ABPP_UAV_C:onAction_44B963FF42A4985ECD88E4B505E9AB80(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_798A68C44B27D99A4B6E209BFF85BA83(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_CB3B6C624087C3490F98C5BF4B37C38E(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:onAction_9771145E49CC5CC06F442BA522DE3FC9(AxisValue) end
---@param E_Game_Mode E_GameMode::Type
---@param IsArmed boolean
function ABPP_UAV_C:SetArmedAndText(E_Game_Mode, IsArmed) end
---@param Input ABP_AI_EnemySoldier_C
function ABPP_UAV_C:SetBPAIController(Input) end
function ABPP_UAV_C:CameraShakeEffect() end
function ABPP_UAV_C:ExplosiveDecal() end
---@param FieldOfView double
function ABPP_UAV_C:SetFieldOfView(FieldOfView) end
---@param isShow boolean
function ABPP_UAV_C:ShowParasiteEffect(isShow) end
function ABPP_UAV_C:CheckFiberDistance() end
function ABPP_UAV_C:ShowParasiteEffectOutside() end
function ABPP_UAV_C:ShowFiberRopeInfo() end
function ABPP_UAV_C:CallCircleExplosion() end
---@param E_UAV_Flight_Mode E_UAV_FlightMode::Type
function ABPP_UAV_C:SetFlightMode(E_UAV_Flight_Mode) end
---@param IsActive boolean
function ABPP_UAV_C:IsActiveJammer(IsActive) end
function ABPP_UAV_C:DestroyWithDelay() end
---@param OverlappedComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param OtherBodyIndex int32
---@param bFromSweep boolean
---@param SweepResult FHitResult
function ABPP_UAV_C:BndEvt__BPP_MainDrone_Box_K2Node_ComponentBoundEvent_2_ComponentBeginOverlapSignature__DelegateSignature(OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult) end
---@param Value double
---@param Roll double
---@param Pitch double
---@param Yaw double
function ABPP_UAV_C:SoundForSpeed(Value, Roll, Pitch, Yaw) end
---@param IsActive boolean
function ABPP_UAV_C:SetThermalProcessAndFOV(IsActive) end
function ABPP_UAV_C:InitializeCustomize() end
---@param Duration float
function ABPP_UAV_C:RestartGame(Duration) end
function ABPP_UAV_C:ChangeFlightMode() end
---@param IsPressed boolean
function ABPP_UAV_C:LockKitButton(IsPressed) end
---@param IsPressed boolean
function ABPP_UAV_C:ThermalButton(IsPressed) end
---@param AxisValue float
function ABPP_UAV_C:InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_0(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_1(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:InpAxisEvt_I_KeyboardYaw_K2Node_InputAxisEvent_3(AxisValue) end
---@param AxisValue float
function ABPP_UAV_C:InpAxisEvt_I_KeyboardThrottle_K2Node_InputAxisEvent_2(AxisValue) end
---@param DeltaSeconds float
function ABPP_UAV_C:ReceiveTick(DeltaSeconds) end
function ABPP_UAV_C:ReceiveBeginPlay() end
---@param AmmunitionAction double
function ABPP_UAV_C:TriggerAction(AmmunitionAction) end
---@param PushImpactAction double
function ABPP_UAV_C:PushImpactAction(PushImpactAction) end
---@param LockKitAction float
function ABPP_UAV_C:LockKitAction(LockKitAction) end
---@param RespawnAction float
function ABPP_UAV_C:RespawnAction(RespawnAction) end
---@param ThermalAction float
function ABPP_UAV_C:ThermalAction(ThermalAction) end
---@param ArmedAction double
function ABPP_UAV_C:ArmAction(ArmedAction) end
---@param MovementThrottleAxis double
function ABPP_UAV_C:MovementThrottleAxis(MovementThrottleAxis) end
---@param MovementYawAxis double
function ABPP_UAV_C:MovementYawAxis(MovementYawAxis) end
---@param RollAxisInput double
function ABPP_UAV_C:MovementRollAxis(RollAxisInput) end
---@param PitchAxisInput double
function ABPP_UAV_C:MovementPitchAxis(PitchAxisInput) end
function ABPP_UAV_C:ShowTriggerInfo() end
function ABPP_UAV_C:TargetLockUI() end
function ABPP_UAV_C:CheckCanPropwash() end
function ABPP_UAV_C:CheckCanFiberRope() end
function ABPP_UAV_C:AnalogGlitch() end
function ABPP_UAV_C:RestartBatteryValues() end
ABPP_UAV_C['Reset Battery'] = function(self, ) end
function ABPP_UAV_C:BatteryTimer() end
function ABPP_UAV_C:CheckOnGround() end
function ABPP_UAV_C:AltitudeDistance() end
function ABPP_UAV_C:UpdateDistanceToInitialLocation() end
function ABPP_UAV_C:CheckFlipAndRevert() end
function ABPP_UAV_C:IsGroundCheck() end
---@param EntryPoint int32
function ABPP_UAV_C:ExecuteUbergraph_BPP_UAV(EntryPoint) end
function ABPP_UAV_C:RestartDrone__DelegateSignature() end


