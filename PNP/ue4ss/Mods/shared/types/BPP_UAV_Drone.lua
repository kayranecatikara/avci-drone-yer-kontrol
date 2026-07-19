---@meta

---@class ABPP_UAV_Drone_C : ABPP_UAV_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DroneAngleFlight UDroneAngleFlightComponent
---@field DroneTCPController UDroneTCPController
---@field SM_Drone_FiberOptic UStaticMeshComponent
---@field SM_Drone_PropellerRR UStaticMeshComponent
---@field SM_Drone_Bracket UStaticMeshComponent
---@field SM_Drone_ExplosivePersonal UStaticMeshComponent
---@field SM_Drone_PropellerFL UStaticMeshComponent
---@field SM_Drone_PropellerRL UStaticMeshComponent
---@field SM_Drone_ExplosiveHeavy UStaticMeshComponent
---@field SM_Drone_PropellerFR UStaticMeshComponent
---@field SM_Battery UStaticMeshComponent
---@field NS_Fiber1 UNiagaraComponent
---@field VectorDownDirection FVector
---@field ['Current Input'] FDroneInputData
local ABPP_UAV_Drone_C = {}

---@param Key FKey
function ABPP_UAV_Drone_C:InpActEvt_Q_K2Node_InputKeyEvent_0(Key) end
---@param ArmedAction double
function ABPP_UAV_Drone_C:ArmAction(ArmedAction) end
---@param AxisValue float
function ABPP_UAV_Drone_C:InpAxisEvt_I_KeyboardYaw_K2Node_InputAxisEvent_2(AxisValue) end
---@param AxisValue float
function ABPP_UAV_Drone_C:InpAxisEvt_I_KeyboardThrottle_K2Node_InputAxisEvent_3(AxisValue) end
---@param isEngineOn boolean
function ABPP_UAV_Drone_C:ArmRemote(isEngineOn) end
---@param PitchAxisInput double
function ABPP_UAV_Drone_C:MovementPitchAxis(PitchAxisInput) end
---@param MovementYawAxis double
function ABPP_UAV_Drone_C:MovementYawAxis(MovementYawAxis) end
---@param MovementThrottleAxis double
function ABPP_UAV_Drone_C:MovementThrottleAxis(MovementThrottleAxis) end
---@param AxisValue float
function ABPP_UAV_Drone_C:InpAxisEvt_I_MouseRoll_K2Node_InputAxisEvent_0(AxisValue) end
---@param AxisValue float
function ABPP_UAV_Drone_C:InpAxisEvt_I_MousePitch_K2Node_InputAxisEvent_1(AxisValue) end
---@param RollAxisInput double
function ABPP_UAV_Drone_C:MovementRollAxis(RollAxisInput) end
---@param DeltaSeconds float
function ABPP_UAV_Drone_C:ReceiveTick(DeltaSeconds) end
function ABPP_UAV_Drone_C:ReceiveBeginPlay() end
---@param Delta_Second double
function ABPP_UAV_Drone_C:PropellerRotate(Delta_Second) end
---@param EntryPoint int32
function ABPP_UAV_Drone_C:ExecuteUbergraph_BPP_UAV_Drone(EntryPoint) end


