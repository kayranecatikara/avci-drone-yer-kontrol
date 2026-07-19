---@meta

---@class UBP_GameInstance_C : UGameInstance
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ELevel E_Levels::Type
---@field EUAV E_UAV::Type
---@field ['Reverse Roll Axis'] double
---@field ['Reverse Throttle Axis'] double
---@field ['Reverse Pitch Axis'] double
---@field ['Reverse Yaw Axis'] double
---@field EController E_Controller::Type
---@field EExplosiveType E_ExplosiveType::Type
---@field PlayerNickname FText
---@field canUseThermal boolean
---@field canUseLockKit boolean
---@field EMapMode E_MapMode::Type
---@field PoleEnemyCount int32
---@field RuinedCityEnemyCount int32
---@field RuralEnemyCount int32
---@field DeadZone double
---@field canUsePushImpact boolean
---@field MappingProfilePlayer FSimpleControllerMappingProfile
---@field deviceName FString
---@field MilitaryAirportEnemyCount int32
---@field ProfileName FString
---@field PeakEnemyCount int32
---@field EFiberType E_FiberType::Type
---@field ['E Game State'] E_GameStates::Type
---@field DTMaps UDataTable
---@field ControllerType ESimpleControllerType
---@field ['RC Expo Roll'] double
---@field ['RC Expo Pitch'] double
---@field ['RC Expo Yaw'] double
---@field ['Axis Speed Roll'] double
---@field ['Axis Speed Pitch'] double
---@field ['Axis Speed Yaw'] double
---@field FieldOfView double
---@field isLoggedBefore boolean
---@field ['EUAV Flight Mode'] E_UAV_FlightMode::Type
---@field TotalPlayTime double
---@field ['BP Save Game Score Board'] UBP_SaveGame_ScoreBoard_C
---@field ['GM UAVBase'] AGM_UAVBase_C
---@field TotalFlightTime double
---@field TotalKillCount int32
---@field ['EUAV Type'] E_UAVType::Type
local UBP_GameInstance_C = {}

---@param EExplosiveType E_ExplosiveType::Type
UBP_GameInstance_C['Set Explosive Type'] = function(self, EExplosiveType) end
function UBP_GameInstance_C:LoadLevel() end
---@param EController E_Controller::Type
UBP_GameInstance_C['Set E Controller'] = function(self, EController) end
---@param Level E_Levels::Type
UBP_GameInstance_C['Set Level'] = function(self, Level) end
function UBP_GameInstance_C:ReceiveInit() end
function UBP_GameInstance_C:ReceiveShutdown() end
function UBP_GameInstance_C:AutoSaveTotalTime() end
function UBP_GameInstance_C:CalculateTotalPlayTime() end
function UBP_GameInstance_C:CalculateTotalFlyPlayTime() end
function UBP_GameInstance_C:AutoSaveFlyTotalTime() end
function UBP_GameInstance_C:SaveTotalKillCount() end
function UBP_GameInstance_C:CalculateTotalKillCount() end
---@param EntryPoint int32
function UBP_GameInstance_C:ExecuteUbergraph_BP_GameInstance(EntryPoint) end


