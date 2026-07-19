---@meta

---@class ABPP_MenuCam_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ControllerCapture USceneCaptureComponent2D
---@field RectLight_Controller URectLightComponent
---@field RectLight_UAV URectLightComponent
---@field SKM_RadioMasterPocket USkeletalMeshComponent
---@field SM_SDrone_Propeller2 UStaticMeshComponent
---@field SM_Battery UStaticMeshComponent
---@field SM_SDrone_Propeller3 UStaticMeshComponent
---@field SM_SDrone_Propeller4 UStaticMeshComponent
---@field SM_SDrone_Propeller1 UStaticMeshComponent
---@field ['SM_SDrone_7"'] UStaticMeshComponent
---@field DroneCapture USceneCaptureComponent2D
---@field InterpToMovement UInterpToMovementComponent
---@field CineCamera UCineCameraComponent
---@field DefaultSceneRoot USceneComponent
---@field Timeline_0_NewTrack_1_ECFCA1434AEC619FA50765BBC9FDFB3D float
---@field Timeline_0__Direction_ECFCA1434AEC619FA50765BBC9FDFB3D ETimelineDirection::Type
---@field Timeline_0 UTimelineComponent
---@field Timeline_NewTrack_1_57CB5A8749D785A25D67F4861D580833 float
---@field Timeline__Direction_57CB5A8749D785A25D67F4861D580833 ETimelineDirection::Type
---@field Timeline UTimelineComponent
---@field Timeline_2_NewTrack_0_FC2FE8794C67D3B47807F7A5B40334C5 float
---@field Timeline_2__Direction_FC2FE8794C67D3B47807F7A5B40334C5 ETimelineDirection::Type
---@field Timeline_2 UTimelineComponent
---@field DroneTransform FTransform
---@field ['HUD Main Menu'] AHUD_MainMenu_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field MaximumDegree double
---@field MinumumDegree double
---@field RollAxisInput double
---@field PitchAxisInput double
---@field ThrottleAxisInput double
---@field YawAxisInput double
---@field DeadZone double
---@field InitialTransform FTransform
---@field UAVTransform FTransform
---@field MenuCameraPhase E_MenuCameraPhases::Type
---@field MiniDroneTransform FTransform
---@field StartControlRotation FRotator
---@field TargetControlRotation FRotator
---@field isRotated boolean
local ABPP_MenuCam_C = {}

---@param Input double
---@param Output double
function ABPP_MenuCam_C:NormalizeDeadzone(Input, Output) end
function ABPP_MenuCam_C:Timeline_2__FinishedFunc() end
function ABPP_MenuCam_C:Timeline_2__UpdateFunc() end
function ABPP_MenuCam_C:Timeline__FinishedFunc() end
function ABPP_MenuCam_C:Timeline__UpdateFunc() end
function ABPP_MenuCam_C:Timeline_0__FinishedFunc() end
function ABPP_MenuCam_C:Timeline_0__UpdateFunc() end
function ABPP_MenuCam_C:failed_450A7522400B4CBB7613909D7157054F() end
function ABPP_MenuCam_C:successful_450A7522400B4CBB7613909D7157054F() end
---@param AxisValue float
function ABPP_MenuCam_C:onAction_CAF3C7E84B78055A99946E98035BF4B6(AxisValue) end
---@param AxisValue float
function ABPP_MenuCam_C:onAction_347FAD934BDC8F7A39A48998768D5735(AxisValue) end
---@param AxisValue float
function ABPP_MenuCam_C:onAction_2AA3B148420E2A12DB44E9A8AF67BFEA(AxisValue) end
---@param AxisValue float
function ABPP_MenuCam_C:onAction_25E518404515131C72411D983ECAFCFD(AxisValue) end
function ABPP_MenuCam_C:ReceiveBeginPlay() end
---@param isMenu boolean
---@param Target E_MenuCameraPhases::Type
function ABPP_MenuCam_C:MoveToCam(isMenu, Target) end
function ABPP_MenuCam_C:LoadedData_Event() end
---@param CurrentLocation FVector
---@param CurrentRotation FRotator
---@param TargetLocation FVector
---@param TargetRotation FRotator
function ABPP_MenuCam_C:MoveToLocation(CurrentLocation, CurrentRotation, TargetLocation, TargetRotation) end
function ABPP_MenuCam_C:MoveToDroneSection() end
---@param Index E_MenuCameraPhases::Type
function ABPP_MenuCam_C:SetFocusSettings(Index) end
---@param isNormal boolean
function ABPP_MenuCam_C:RotateController(isNormal) end
---@param YawAxisInput double
function ABPP_MenuCam_C:MovementYawAxis(YawAxisInput) end
---@param ThrottleAxisInput double
function ABPP_MenuCam_C:MovementThrottleAxis(ThrottleAxisInput) end
---@param RollAxisInput double
function ABPP_MenuCam_C:MovementPitchAxis(RollAxisInput) end
---@param PitchAxisInput double
function ABPP_MenuCam_C:MovementRollAxis(PitchAxisInput) end
---@param EntryPoint int32
function ABPP_MenuCam_C:ExecuteUbergraph_BPP_MenuCam(EntryPoint) end


