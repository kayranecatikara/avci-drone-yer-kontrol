---@meta

---@class AGM_UAVBase_C : AGameModeBase
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DefaultSceneRoot USceneComponent
---@field FailCrashCount int32
---@field SuccesCrashCount int32
---@field ScoreboardDegreeCount int32
---@field SoldierCount int32
---@field DroneCount int32
---@field VehicleCount int32
---@field HelicopterCount int32
---@field HeavyCount int32
---@field FixedGunCount int32
---@field CurrentKilledEnemyCount int32
---@field AllEnemyCount int32
---@field ['HUD Main UAV'] AHUD_MainUAV_C
---@field SaveScoreboardName FString
---@field SaveScoreboardRef USaveGame
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['BPP Enemy Cars'] TArray<ABPP_BaseEnemyCar_C>
---@field ['BP AI Enemy Soldiers'] TArray<ABP_AI_EnemySoldier_C>
---@field ['BP OP Soldiers'] TArray<ABP_OPSoldier_C>
---@field TotalVehicleCount int32
---@field TotalHelicopterCount int32
---@field TotalHeavyCount int32
---@field TotalFixedGunCount int32
---@field ScoreboardTotalTimerHandle FTimerHandle
---@field GameScoreboardSecondsTimer int32
---@field GameScoreboardMinutesTimer int32
---@field ScoreboardSecondsTimer int32
---@field ScoreboardMinutesTimer int32
---@field ['BPP UAV'] ABPP_UAV_C
---@field CurrentCheckpointCount int32
---@field AllCheckpoints TArray<ABP_Checkpoint_C>
---@field TotalCheckpointCount int32
---@field isCompletedRace boolean
---@field ['DT UAV'] UDataTable
---@field ['BP Save Game Score Board'] UBP_SaveGame_ScoreBoard_C
---@field ['UAV Spawn Point'] ABPP_UAV_SpawnPoint_C
---@field StarterPlatforms TArray<TSubclassOf<APawn>>
---@field SpawnedStarterPlatform TSubclassOf<APawn>
---@field ['BPP Spectator'] ABPP_Spectator_C
---@field AIDroneTalon ABPP_AIDroneTalon_C
---@field ['Out Actors'] TArray<ABPP_AIDroneTalon_C>
local AGM_UAVBase_C = {}

---@param SelectedDrone TSubclassOf<ABPP_UAV_C>
function AGM_UAVBase_C:GetSelectionDrone(SelectedDrone) end
function AGM_UAVBase_C:SaveScoreBoard() end
function AGM_UAVBase_C:UpdateFailCrashCount() end
function AGM_UAVBase_C:UpdateSuccessCrashCount() end
function AGM_UAVBase_C:UpdateScoreboardDegreeCount() end
---@param Vehicle E_EnemyCarType::Type
---@param NotVehicle boolean
---@param SoldierAndDrone int32
function AGM_UAVBase_C:UpdateEnemyCount(Vehicle, NotVehicle, SoldierAndDrone) end
function AGM_UAVBase_C:ReceiveBeginPlay() end
function AGM_UAVBase_C:UpdateCheckpointInformation() end
function AGM_UAVBase_C:RestartRaceModeSettings() end
---@param isFail boolean
---@param WhoDead FString
function AGM_UAVBase_C:SuccessKamikaze(isFail, WhoDead) end
function AGM_UAVBase_C:FailKamikaze() end
function AGM_UAVBase_C:SuccessNet() end
function AGM_UAVBase_C:FailNet() end
---@param WhoDead FString
function AGM_UAVBase_C:DamageVehicle(WhoDead) end
---@param WhoDead FString
function AGM_UAVBase_C:SuccessNotifyKillFeed(WhoDead) end
function AGM_UAVBase_C:InteractDrone() end
function AGM_UAVBase_C:UpdateEnemyKilledCount() end
function AGM_UAVBase_C:FlyMinTimer() end
---@param EntryPoint int32
function AGM_UAVBase_C:ExecuteUbergraph_GM_UAVBase(EntryPoint) end


