---@meta

---@class UEasyLoadingScreenAsync : UBlueprintAsyncActionBase
---@field OnUpdate FEasyLoadingScreenAsyncOnUpdate
---@field OnComplete FEasyLoadingScreenAsyncOnComplete
local UEasyLoadingScreenAsync = {}

---@param WorldContextObject UObject
---@param URL FString
---@param Level TSoftObjectPtr<UWorld>
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
function UEasyLoadingScreenAsync:OpenServerLevelWithUMG2(WorldContextObject, URL, Level, bAbsolute, Options, DelayOpen) end
---@param WorldContextObject UObject
---@param URL FString
---@param LevelName FName
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
function UEasyLoadingScreenAsync:OpenServerLevelWithUMG(WorldContextObject, URL, LevelName, bAbsolute, Options, DelayOpen) end
---@param WorldContextObject UObject
---@param Level TSoftObjectPtr<UWorld>
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
function UEasyLoadingScreenAsync:OpenLevelWithUMG2(WorldContextObject, Level, bAbsolute, Options, DelayOpen) end
---@param WorldContextObject UObject
---@param LevelName FName
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
function UEasyLoadingScreenAsync:OpenLevelWithUMG(WorldContextObject, LevelName, bAbsolute, Options, DelayOpen) end
---@param WorldContextObject UObject
---@param Level TSoftObjectPtr<UWorld>
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
---@return UEasyLoadingScreenAsync
function UEasyLoadingScreenAsync:OpenLevelWithPercentage2(WorldContextObject, Level, bAbsolute, Options, DelayOpen) end
---@param WorldContextObject UObject
---@param LevelName FName
---@param bAbsolute boolean
---@param Options FString
---@param DelayOpen float
---@return UEasyLoadingScreenAsync
function UEasyLoadingScreenAsync:OpenLevelWithPercentage(WorldContextObject, LevelName, bAbsolute, Options, DelayOpen) end


