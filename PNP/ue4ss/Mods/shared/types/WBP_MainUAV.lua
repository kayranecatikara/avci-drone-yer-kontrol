---@meta

---@class UWBP_MainUAV_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Border_FinishRace UBorder
---@field CardFinish_Blur UBackgroundBlur
---@field Image_Battery1 UImage
---@field Image_Battery2 UImage
---@field Image_CrashUI UImage
---@field Image_Crosshair UImage
---@field Image_FiberCamera UImage
---@field Image_JammerUI UImage
---@field Image_LeftJoystick UImage
---@field Image_LeftJoystickBG UImage
---@field Image_LockKit1 UImage
---@field Image_LockKit2 UImage
---@field Image_RightJoystick UImage
---@field Image_RightJoystickBG UImage
---@field Image_TargetLock UImage
---@field Image_WindUI UImage
---@field ProgressBar_Battery1 UProgressBar
---@field ProgressBar_Battery2 UProgressBar
---@field Text_AirSpeed UTextBlock
---@field Text_AirSpeed_1 UTextBlock
---@field Text_AirSpeed_2 UTextBlock
---@field Text_ALTValue UTextBlock
---@field Text_Arm_Notice UTextBlock
---@field Text_Battery_1 UTextBlock
---@field Text_Battery_2 UTextBlock
---@field Text_Current1 UTextBlock
---@field Text_Current2 UTextBlock
---@field Text_Distance UTextBlock
---@field Text_DistanceInitial UTextBlock
---@field Text_DistanceValue UTextBlock
---@field Text_FlightMode UTextBlock
---@field Text_GroundSpeed UTextBlock
---@field Text_GroundSpeedG UTextBlock
---@field Text_GroundSpeeds UTextBlock
---@field Text_Heading UTextBlock
---@field Text_Hover UTextBlock
---@field Text_LOW_VOLTAGE UTextBlock
---@field Text_LQ UTextBlock
---@field Text_Navigation UTextBlock
---@field Text_RaceCheckpoint UTextBlock
---@field Text_RaceTimer UTextBlock
---@field Text_RX_LOSS UTextBlock
---@field Text_Speed UTextBlock
---@field Text_ThrottlePercent UTextBlock
---@field ['Text_Timer_Mİnutes'] UTextBlock
---@field Text_Timer_Seconds UTextBlock
---@field TextBlock_Arm UTextBlock
---@field TextBlock_Trigger UTextBlock
---@field ['BPP UAV'] ABPP_UAV_C
---@field Seconds int32
---@field Minutes int32
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['GM UAV Base'] AGM_UAVBase_C
---@field RaceTimer double
---@field ['BP Save Game Score Board'] UBP_SaveGame_ScoreBoard_C
---@field ['As BPP UAV Drone'] ABPP_UAV_Drone_C
local UWBP_MainUAV_C = {}

---@return FText
function UWBP_MainUAV_C:Get_Text_Current2_Text() end
---@return FText
UWBP_MainUAV_C['Set Current1 Text'] = function(self, ) end
---@return FText
function UWBP_MainUAV_C:Get_Text_AirSpeed_3_Text() end
---@return FText
UWBP_MainUAV_C['Set GroundSpeed Text'] = function(self, ) end
---@return FText
UWBP_MainUAV_C['Set ThrottlePercent Text'] = function(self, ) end
---@return FText
UWBP_MainUAV_C['Set Heading Text'] = function(self, ) end
---@return FText
function UWBP_MainUAV_C:Distance() end
---@return FText
function UWBP_MainUAV_C:SignalText() end
---@return FText
UWBP_MainUAV_C['Set Timer Mİnutes'] = function(self, ) end
---@return FText
UWBP_MainUAV_C['Set Timer Seconds'] = function(self, ) end
---@param Meters double
---@param NewParam FText
UWBP_MainUAV_C['M to Text'] = function(self, Meters, NewParam) end
---@return FText
UWBP_MainUAV_C['Set Altitude Text'] = function(self, ) end
---@return FText
UWBP_MainUAV_C['Set Speed Text'] = function(self, ) end
function UWBP_MainUAV_C:Construct() end
function UWBP_MainUAV_C:ResetFlyMin() end
---@param IsArmOn boolean
function UWBP_MainUAV_C:SetArmText(IsArmOn) end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityJammerIcon(Show) end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityWindIcon(Show) end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityLock1Icon(Show) end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityLock2Icon(Show) end
---@param Visibility ESlateVisibility
function UWBP_MainUAV_C:SetShowHideCrosshair(Visibility) end
---@param Visibility ESlateVisibility
function UWBP_MainUAV_C:ShowArmModeText(Visibility) end
---@param isShow boolean
function UWBP_MainUAV_C:SetTriggerText(isShow) end
function UWBP_MainUAV_C:UpdateAxisControllers() end
function UWBP_MainUAV_C:FlyMinTimer() end
---@param In_Size double
---@param isLock boolean
function UWBP_MainUAV_C:TargetLockUI(In_Size, isLock) end
---@param InVisibility ESlateVisibility
function UWBP_MainUAV_C:SetVisibilityTargetLockUI(InVisibility) end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityLockSquare(Show) end
function UWBP_MainUAV_C:UpdateBatteryInfos() end
---@param Show boolean
function UWBP_MainUAV_C:SetVisibilityCrashIcon(Show) end
function UWBP_MainUAV_C:Hover() end
function UWBP_MainUAV_C:LQ() end
function UWBP_MainUAV_C:CallResetBatteryInfo() end
---@param Percent float
---@param FirstBattery double
---@param SecondBattery double
function UWBP_MainUAV_C:SetBatteryInfo(Percent, FirstBattery, SecondBattery) end
function UWBP_MainUAV_C:UpdateRaceCheckpointCount() end
function UWBP_MainUAV_C:UpdateRaceTimer() end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_MainUAV_C:Tick(MyGeometry, InDeltaTime) end
function UWBP_MainUAV_C:ResetTimer() end
---@param UAV_Flight_Mode E_UAV_FlightMode::Type
function UWBP_MainUAV_C:SetFlightModeText(UAV_Flight_Mode) end
---@param isFinish boolean
function UWBP_MainUAV_C:UpdateFinishCard(isFinish) end
function UWBP_MainUAV_C:SetInitialBatteryValues() end
---@param EntryPoint int32
function UWBP_MainUAV_C:ExecuteUbergraph_WBP_MainUAV(EntryPoint) end


