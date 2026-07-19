---@meta

---@class ABP_EasySaveGameOperationsManager_C : AActor
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DefaultSceneRoot USceneComponent
---@field ['IsSavingOrLoading?'] boolean
---@field CurrentSaveGameOperation FS_SaveOperationInfos
---@field BatchSize int32
---@field CurrentSaveSlot FString
---@field PersistentActorsToSave TMap<TSoftObjectPtr<AActor>, FS_ActorSaveInfos>
---@field PersistentActors TMap<TSoftObjectPtr<AActor>, FString>
---@field ['WorldInitialized?'] boolean
---@field ActorsToDestroyOnLoad TArray<TSoftObjectPtr<AActor>>
---@field CurrentSaveGameObject UBP_EasySaveGameObject_C
---@field ActorsToFindOrRespawn TMap<FString, FS_MapsOfActorsToFindOrRespawn>
---@field FoundActorsList TArray<AActor>
---@field SaveGameOperationStarted FBP_EasySaveGameOperationsManager_CSaveGameOperationStarted
---@field SaveGameOperationEnded FBP_EasySaveGameOperationsManager_CSaveGameOperationEnded
---@field NoLevelActorsMaps FS_MapsOfActorsToFindOrRespawn
---@field CurrentLevelActorsMaps FS_MapsOfActorsToFindOrRespawn
---@field RegisteredFindActorsIndexes TMap<TSoftObjectPtr<AActor>, int32>
---@field ActorsToFindSorted TMap<TSoftClassPtr<AActor>, FS_ArrayOfActorsSaveInfos>
---@field WorkingActorsSaveInfos TArray<FS_ActorSaveInfos>
---@field WorkingMap TMap<TSoftClassPtr<AActor>, FS_DatasOfActorsToFindOrRespawn>
---@field WorkingMapCurrentLevel TMap<TSoftClassPtr<AActor>, FS_DatasOfActorsToFindOrRespawn>
---@field WorkingMapNoLevel TMap<TSoftClassPtr<AActor>, FS_DatasOfActorsToFindOrRespawn>
---@field RegisteredRespawnActorsIndexes TMap<TSoftObjectPtr<AActor>, int32>
---@field ActorsToRespawnSorted TMap<TSoftClassPtr<AActor>, FS_ArrayOfActorsSaveInfos>
---@field WorkingMapOfDatas TMap<FString, FString>
---@field MapOfDatasCurrentLevel TMap<FString, FString>
---@field MapOfDatasNoLevel TMap<FString, FString>
---@field WorkingClass TSoftClassPtr<AActor>
---@field CurrentIndex int32
---@field LoadStep int32
---@field SaveGameOperationsQueue TArray<FS_SaveOperationInfos>
---@field LevelToLoadInQueue FName
---@field IndexInQueueOfLevelToLoad int32
---@field LoadedTime FDateTime
---@field PlayTime int32
---@field AutoSavesTimer FTimerHandle
---@field GameInstance UGameInstance
---@field ['AutoSavesPaused?'] boolean
---@field ThumbnailWarmUpFrames int32
---@field ['WaitingForThumbnailCapture?'] boolean
---@field SceneCaptureComponent2D USceneCaptureComponent2D
---@field AbsoluteLevelOption boolean
---@field LevelInQueueOptions FString
---@field SlotNameOfLevelToLoadInQueue FString
---@field NewGameInitialization FBP_EasySaveGameOperationsManager_CNewGameInitialization
---@field RenderTargetTexture TSoftObjectPtr<UTextureRenderTarget2D>
---@field ['AlwaysAllowAutoSaves?'] boolean
---@field PlayerTransformToSave FTransform
local ABP_EasySaveGameOperationsManager_C = {}

---@param Allowed_ boolean
ABP_EasySaveGameOperationsManager_C['AutoSavesAllowed?'] = function(self, Allowed_) end
---@param Pause_ boolean
function ABP_EasySaveGameOperationsManager_C:PauseOrResumeAutoSaves(Pause_) end
---@param OperationType E_SaveGameOperationType::Type
---@param SaveGame UBP_EasySaveGameObject_C
function ABP_EasySaveGameOperationsManager_C:SaveOrLoadPlayerTransform(OperationType, SaveGame) end
---@param NewOperationInfos FS_SaveOperationInfos
---@param LevelToLoad FName
---@param Absolute boolean
---@param Options FString
function ABP_EasySaveGameOperationsManager_C:AddOperationToQueue(NewOperationInfos, LevelToLoad, Absolute, Options) end
---@param SaveUniqueName FString
function ABP_EasySaveGameOperationsManager_C:DeleteSaveSlot(SaveUniqueName) end
---@param ActorWasDestroyed_ boolean
---@param SaveGameComponentRef TSoftObjectPtr<UBP_EasySaveGameComponent_C>
---@param ActorClass TSoftClassPtr<AActor>
---@param SaveLevel_ boolean
---@param ActorUniqueID FString
---@param SaveActorDestructionAsVar_ boolean
function ABP_EasySaveGameOperationsManager_C:SaveActorsToRespawnOrFind(ActorWasDestroyed_, SaveGameComponentRef, ActorClass, SaveLevel_, ActorUniqueID, SaveActorDestructionAsVar_) end
function ABP_EasySaveGameOperationsManager_C:SaveDatasToWorkingMaps() end
---@param ActorSaveInfos FS_ActorSaveInfos
---@param ActorRef TSoftObjectPtr<AActor>
---@param ActorClass TSoftClassPtr<AActor>
---@param ActorsSourceMap TMap<TSoftClassPtr<AActor>, FS_ArrayOfActorsSaveInfos>
---@param RegisteredActorsIndexes TMap<TSoftObjectPtr<AActor>, int32>
function ABP_EasySaveGameOperationsManager_C:SortActorsToRespawnOrFind(ActorSaveInfos, ActorRef, ActorClass, ActorsSourceMap, RegisteredActorsIndexes) end
function ABP_EasySaveGameOperationsManager_C:SaveOrLoadCompleted() end
---@param StopLoadingScreen_ boolean
---@param PlayFadeAnimation_ boolean
---@param OperationType E_SaveGameOperationType::Type
function ABP_EasySaveGameOperationsManager_C:StartStopLoadingScreen(StopLoadingScreen_, PlayFadeAnimation_, OperationType) end
function ABP_EasySaveGameOperationsManager_C:SaveCurrentMetadatas() end
---@param Loaded UClass
function ABP_EasySaveGameOperationsManager_C:OnLoaded_9A1A99894A0AF0F88E2E01BC57ADDF5E(Loaded) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EasySaveGameOperationsManager_C:InpActEvt_IA_QuickSave_K2Node_EnhancedInputActionEvent_1(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EasySaveGameOperationsManager_C:InpActEvt_IA_QuickLoad_K2Node_EnhancedInputActionEvent_0(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param SaveGame USaveGame
---@param bSuccess boolean
function ABP_EasySaveGameOperationsManager_C:Completed_47F5366F472B474B02BA4BBFFFA239FD(SaveGame, bSuccess) end
---@param SaveGame USaveGame
---@param bSuccess boolean
function ABP_EasySaveGameOperationsManager_C:Completed_B71FFDC1411BD40FBA7633BBA3E0F555(SaveGame, bSuccess) end
---@param Loaded UObject
function ABP_EasySaveGameOperationsManager_C:OnLoaded_FE88A4C54D5A50DD5A7DCD9FBC958C7B(Loaded) end
---@param Save_Game_Operation_Infos FS_SaveOperationInfos
function ABP_EasySaveGameOperationsManager_C:StartSaveGameOperation(Save_Game_Operation_Infos) end
---@param ActorRef TSoftObjectPtr<AActor>
---@param ActorSaveInfos FS_ActorSaveInfos
function ABP_EasySaveGameOperationsManager_C:RegisterForSaveFiles(ActorRef, ActorSaveInfos) end
---@param OperationInfos FS_SaveOperationInfos
---@param LevelName FName
---@param Absolute boolean
---@param Options FString
function ABP_EasySaveGameOperationsManager_C:LoadNewLevel(OperationInfos, LevelName, Absolute, Options) end
---@param DeltaSeconds float
function ABP_EasySaveGameOperationsManager_C:ReceiveTick(DeltaSeconds) end
function ABP_EasySaveGameOperationsManager_C:ReceiveBeginPlay() end
function ABP_EasySaveGameOperationsManager_C:TriggerAutoSave() end
function ABP_EasySaveGameOperationsManager_C:TriggerQuickSave() end
function ABP_EasySaveGameOperationsManager_C:QuickLoad() end
---@param EntryPoint int32
function ABP_EasySaveGameOperationsManager_C:ExecuteUbergraph_BP_EasySaveGameOperationsManager(EntryPoint) end
function ABP_EasySaveGameOperationsManager_C:NewGameInitialization__DelegateSignature() end
---@param Operation FS_SaveOperationInfos
function ABP_EasySaveGameOperationsManager_C:SaveGameOperationEnded__DelegateSignature(Operation) end
---@param Operation FS_SaveOperationInfos
function ABP_EasySaveGameOperationsManager_C:SaveGameOperationStarted__DelegateSignature(Operation) end


