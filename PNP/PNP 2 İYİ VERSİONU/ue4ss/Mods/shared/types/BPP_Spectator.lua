---@meta

---@class ABPP_Spectator_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SpectatorTracking USpectatorTrackingComponent
---@field CineCamera UCineCameraComponent
---@field DefaultSceneRoot USceneComponent
---@field SpectatorSpeed double
---@field ZoomSpeed double
---@field ['BPP MainDrone'] ABPP_UAV_C
---@field ['HUD Main Drone'] AHUD_MainUAV_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['Reverse Throttle Axis'] double
---@field ['Reverse Pitch Axis'] double
---@field ['Reverse Yaw Axis'] double
---@field isCompletedLevel boolean
---@field canRotate boolean
---@field SpawnDroneAxisInput float
---@field PitchAxisInput float
---@field ZoomAxisInput float
---@field YawAxisInput float
---@field ['GM UAV Base'] AGM_UAVBase_C
---@field Crashed boolean
---@field Target AActor
---@field ['Focus Settings'] FCameraFocusSettings
local ABPP_Spectator_C = {}

function ABPP_Spectator_C:leftDpadReleased_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:leftDpadPressed_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:rightDpadReleased_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:rightDpadPressed_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:topDpadReleased_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:topDpadPressed_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:bottomDpadReleased_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:bottomDpadPressed_E7B710F149BA11720448C5AEB567E56B() end
function ABPP_Spectator_C:actionReleased_E1FCD34540B0A2CA78449E9B38EF0C83() end
function ABPP_Spectator_C:actionPressed_E1FCD34540B0A2CA78449E9B38EF0C83() end
---@param Key FKey
function ABPP_Spectator_C:InpActEvt_E_K2Node_InputKeyEvent_3(Key) end
---@param Key FKey
function ABPP_Spectator_C:InpActEvt_Tab_K2Node_InputKeyEvent_2(Key) end
---@param Key FKey
function ABPP_Spectator_C:InpActEvt_Tab_K2Node_InputKeyEvent_1(Key) end
---@param Key FKey
function ABPP_Spectator_C:InpActEvt_Escape_K2Node_InputKeyEvent_0(Key) end
---@param AxisValue float
function ABPP_Spectator_C:onAction_7B2EFCD44879D68D516A57B11BD6E251(AxisValue) end
---@param AxisValue float
function ABPP_Spectator_C:onAction_F60342974C4CD2E3F4A35D80E8E29F2E(AxisValue) end
---@param AxisValue float
function ABPP_Spectator_C:onAction_90427C0245DE4EAA58138E9ED0888F76(AxisValue) end
---@param AxisValue float
function ABPP_Spectator_C:onAction_7B71C67F489E058981AB61851A38E600(AxisValue) end
function ABPP_Spectator_C:failed_9B71C67E41AC31D2683779A46D997440() end
function ABPP_Spectator_C:successful_9B71C67E41AC31D2683779A46D997440() end
function ABPP_Spectator_C:SetFocusCamera() end
function ABPP_Spectator_C:CompletedLevel() end
function ABPP_Spectator_C:ReceiveBeginPlay() end
---@param AxisValue float
function ABPP_Spectator_C:InpAxisEvt_I_KeyboardSpecSoom_K2Node_InputAxisEvent_3(AxisValue) end
---@param AxisValue float
function ABPP_Spectator_C:InpAxisEvt_I_KeyboardSpecPitch_K2Node_InputAxisEvent_1(AxisValue) end
---@param AxisValue float
function ABPP_Spectator_C:InpAxisEvt_I_KeyboardSpecYaw_K2Node_InputAxisEvent_0(AxisValue) end
---@param Spawn_Drone_Axis_Input double
ABPP_Spectator_C['Spawn Drone'] = function(self, Spawn_Drone_Axis_Input) end
---@param Zoom_Axis_Input double
function ABPP_Spectator_C:CameraZoom(Zoom_Axis_Input) end
---@param Yaw_Axis_Input float
---@param Pitch_Axis_Input double
function ABPP_Spectator_C:CameraRotationLook(Yaw_Axis_Input, Pitch_Axis_Input) end
---@param EntryPoint int32
function ABPP_Spectator_C:ExecuteUbergraph_BPP_Spectator(EntryPoint) end


