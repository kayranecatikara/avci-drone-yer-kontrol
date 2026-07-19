---@meta

---@class IBPI_EGUI_GameInstanceInterface_C : IInterface
local IBPI_EGUI_GameInstanceInterface_C = {}

---@param SaveOperationsAllowed_ boolean
---@param LoadOperationsAllowed_ boolean
function IBPI_EGUI_GameInstanceInterface_C:GetSaveGameOperationsAllowed(SaveOperationsAllowed_, LoadOperationsAllowed_) end
---@param SaveOperationsAllowed_ boolean
---@param LoadOperationsAllowed_ boolean
function IBPI_EGUI_GameInstanceInterface_C:SetSaveGameOperationsAllowed(SaveOperationsAllowed_, LoadOperationsAllowed_) end
---@param IsNewSaveFile_ boolean
IBPI_EGUI_GameInstanceInterface_C['SetIsNewSaveFile?'] = function(self, IsNewSaveFile_) end
---@param LoadingScreenWidget UWBP_ESGU_LoadingScreen_C
function IBPI_EGUI_GameInstanceInterface_C:SetNewActiveLoadingScreen(LoadingScreenWidget) end
---@param LoadingScreenWidget UWBP_ESGU_LoadingScreen_C
function IBPI_EGUI_GameInstanceInterface_C:GetCurrentActiveLoadingScreen(LoadingScreenWidget) end
---@param BenchmarkRequested_ boolean
IBPI_EGUI_GameInstanceInterface_C['HasGameBenchmarkBeenRequested?'] = function(self, BenchmarkRequested_) end
---@param BenchmarkComplete_ boolean
function IBPI_EGUI_GameInstanceInterface_C:SetupGameInstanceForGameBenchmark(BenchmarkComplete_) end
---@param SaveGameOperation FS_SaveOperationInfos
---@param Level FName
---@param Absolute boolean
---@param Options FString
---@param ForceOperation_ boolean
function IBPI_EGUI_GameInstanceInterface_C:SetupGameInstanceForSaveGameOperation(SaveGameOperation, Level, Absolute, Options, ForceOperation_) end
---@param Save_Game_Operation_Infos FS_SaveOperationInfos
---@param UsePreviousDatas_ boolean
---@param ForceOperation_ boolean
function IBPI_EGUI_GameInstanceInterface_C:StartSaveGameOperation(Save_Game_Operation_Infos, UsePreviousDatas_, ForceOperation_) end
---@param ActorRef TSoftObjectPtr<AActor>
---@param ActorInfos FS_ActorSaveInfos
function IBPI_EGUI_GameInstanceInterface_C:RegisterForSaveGame(ActorRef, ActorInfos) end


