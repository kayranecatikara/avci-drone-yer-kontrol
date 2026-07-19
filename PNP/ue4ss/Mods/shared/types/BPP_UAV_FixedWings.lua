---@meta

---@class ABPP_UAV_FixedWings_C : ABPP_UAV_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SM_Wing_RR UStaticMeshComponent
---@field SM_Wing_RL UStaticMeshComponent
---@field SM_Wing_LR UStaticMeshComponent
---@field SM_Wing_LL UStaticMeshComponent
---@field SM_Drone_Propeller UStaticMeshComponent
---@field Timeline_1_NewTrack_0_0424907D45AA85DEA7222E83ED4F1D8D float
---@field Timeline_1__Direction_0424907D45AA85DEA7222E83ED4F1D8D ETimelineDirection::Type
---@field Timeline_1 UTimelineComponent
---@field MovemetSmoothValue float
---@field RotateAngle float
---@field CurrentPitchRotation float
---@field Gravity double
---@field isLaunched boolean
---@field ThrottleForYaw double
---@field LiftMultiplier double
---@field ThrustPower double
---@field DragFactor double
local ABPP_UAV_FixedWings_C = {}

---@param DeltaTime double
function ABPP_UAV_FixedWings_C:ServoDeflections(DeltaTime) end
function ABPP_UAV_FixedWings_C:Timeline_1__FinishedFunc() end
function ABPP_UAV_FixedWings_C:Timeline_1__UpdateFunc() end
---@param Key FKey
function ABPP_UAV_FixedWings_C:InpActEvt_Q_K2Node_InputKeyEvent_0(Key) end
function ABPP_UAV_FixedWings_C:LaunchedPlatform() end
---@param AxisValue float
function ABPP_UAV_FixedWings_C:InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_1(AxisValue) end
---@param AxisValue float
function ABPP_UAV_FixedWings_C:InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_0(AxisValue) end
function ABPP_UAV_FixedWings_C:ChangeFlightMode() end
---@param DeltaSeconds float
function ABPP_UAV_FixedWings_C:ReceiveTick(DeltaSeconds) end
function ABPP_UAV_FixedWings_C:ReceiveBeginPlay() end
function ABPP_UAV_FixedWings_C:MovementPitch() end
function ABPP_UAV_FixedWings_C:MovementRoll() end
---@param ArmedAction double
function ABPP_UAV_FixedWings_C:ArmAction(ArmedAction) end
---@param EntryPoint int32
function ABPP_UAV_FixedWings_C:ExecuteUbergraph_BPP_UAV_FixedWings(EntryPoint) end


