---@meta

---@class UWBP_ScoreBoard_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Intro UWidgetAnimation
---@field RetainerBox_2 URetainerBox
---@field Text_ControllerName UTextBlock
---@field Text_ControllerType UTextBlock
---@field Text_Count_Drone UTextBlock
---@field Text_Count_FixedGun UTextBlock
---@field Text_Count_Heavy UTextBlock
---@field Text_Count_Helicopter UTextBlock
---@field Text_Count_Soldier UTextBlock
---@field Text_Count_Vehicle UTextBlock
---@field Text_CrashC UTextBlock
---@field Text_DroneType UTextBlock
---@field Text_EnemyKilledC UTextBlock
---@field Text_EnemyLeftC UTextBlock
---@field Text_ExplosiveType UTextBlock
---@field Text_FailC UTextBlock
---@field Text_MapMode UTextBlock
---@field Text_MapName UTextBlock
---@field Text_SuccessC UTextBlock
---@field Text_TotalEnemyC UTextBlock
---@field TextBlock_CurrentTime UTextBlock
---@field TimerHandle FTimerHandle
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ComboBoxSelection TMap<FString, int32>
---@field ComboBox_Controllers UComboBoxString
---@field ['GM Main Drone Base'] AGM_UAVBase_C
local UWBP_ScoreBoard_C = {}

function UWBP_ScoreBoard_C:Construct() end
function UWBP_ScoreBoard_C:SetBoardValue() end
function UWBP_ScoreBoard_C:Destruct() end
function UWBP_ScoreBoard_C:RestartOnce() end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ScoreBoard_C:ondeviceDetachedEventDelegate_Event_0(device, connectionIndex) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ScoreBoard_C:ondeviceAttachedEventDelegate_Event_0(device, connectionIndex) end
---@param EntryPoint int32
function UWBP_ScoreBoard_C:ExecuteUbergraph_WBP_ScoreBoard(EntryPoint) end


