---@meta

---@class UBFL_EasySaveGameFunctions_C : UBlueprintFunctionLibrary
local UBFL_EasySaveGameFunctions_C = {}

---@param __WorldContext UObject
---@param SaveGameOperationManager ABP_EasySaveGameOperationsManager_C
function UBFL_EasySaveGameFunctions_C:GetSaveGameOperationsManager(__WorldContext, SaveGameOperationManager) end
---@param PlayTimeInSeconds int32
---@param __WorldContext UObject
---@param Result FText
function UBFL_EasySaveGameFunctions_C:GetPlayTimeAsText(PlayTimeInSeconds, __WorldContext, Result) end
---@param StartDate FDateTime
---@param PreviousPlayTime int32
---@param __WorldContext UObject
---@param NewPlayTime int32
function UBFL_EasySaveGameFunctions_C:CalcNewPlayTime(StartDate, PreviousPlayTime, __WorldContext, NewPlayTime) end
---@param SaveFileName FString
---@param __WorldContext UObject
---@param ThumbnailPath FString
function UBFL_EasySaveGameFunctions_C:CaptureThumbnailForSaveFile(SaveFileName, __WorldContext, ThumbnailPath) end
---@param SaveSlot FString
---@param IncludeFileName_ boolean
---@param __WorldContext UObject
---@return FString
function UBFL_EasySaveGameFunctions_C:GetThumbnailFilePath(SaveSlot, IncludeFileName_, __WorldContext) end
---@param __WorldContext UObject
---@param SaveFilesPath FString
function UBFL_EasySaveGameFunctions_C:GetSaveFilesPath(__WorldContext, SaveFilesPath) end
---@param SaveType FString
---@param __WorldContext UObject
---@param FoundSlots TArray<FString>
---@param FoundSlots_ boolean
function UBFL_EasySaveGameFunctions_C:GetAllSaveSlots(SaveType, __WorldContext, FoundSlots, FoundSlots_) end
---@param Paths TArray<FString>
---@param FindNewest_ boolean
---@param __WorldContext UObject
---@param SlotUniqueName FString
---@param SlotIndex int32
---@param SaveSlot UBP_EasySaveGameObject_C
function UBFL_EasySaveGameFunctions_C:FindNewestOrOldestSaveSlotFromList(Paths, FindNewest_, __WorldContext, SlotUniqueName, SlotIndex, SaveSlot) end
---@param SaveType FString
---@param MaxAmountOfSavesForType int32
---@param __WorldContext UObject
---@param SaveUniqueName FString
function UBFL_EasySaveGameFunctions_C:FindAvailableIndexForSaveType(SaveType, MaxAmountOfSavesForType, __WorldContext, SaveUniqueName) end


