#ifndef UE4SS_SDK_BP_EasySaveGameOperationsManager_HPP
#define UE4SS_SDK_BP_EasySaveGameOperationsManager_HPP

class ABP_EasySaveGameOperationsManager_C : public AActor
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02A8 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x02B0 (size: 0x8)
    bool IsSavingOrLoading?;                                                          // 0x02B8 (size: 0x1)
    FS_SaveOperationInfos CurrentSaveGameOperation;                                   // 0x02C0 (size: 0x18)
    int32 BatchSize;                                                                  // 0x02D8 (size: 0x4)
    FString CurrentSaveSlot;                                                          // 0x02E0 (size: 0x10)
    TMap<class TSoftObjectPtr<AActor>, class FS_ActorSaveInfos> PersistentActorsToSave; // 0x02F0 (size: 0x50)
    TMap<class TSoftObjectPtr<AActor>, class FString> PersistentActors;               // 0x0340 (size: 0x50)
    bool WorldInitialized?;                                                           // 0x0390 (size: 0x1)
    TArray<TSoftObjectPtr<AActor>> ActorsToDestroyOnLoad;                             // 0x0398 (size: 0x10)
    class UBP_EasySaveGameObject_C* CurrentSaveGameObject;                            // 0x03A8 (size: 0x8)
    TMap<class FString, class FS_MapsOfActorsToFindOrRespawn> ActorsToFindOrRespawn;  // 0x03B0 (size: 0x50)
    TArray<class AActor*> FoundActorsList;                                            // 0x0400 (size: 0x10)
    FBP_EasySaveGameOperationsManager_CSaveGameOperationStarted SaveGameOperationStarted; // 0x0410 (size: 0x10)
    void SaveGameOperationStarted(FS_SaveOperationInfos Operation);
    FBP_EasySaveGameOperationsManager_CSaveGameOperationEnded SaveGameOperationEnded; // 0x0420 (size: 0x10)
    void SaveGameOperationEnded(FS_SaveOperationInfos Operation);
    FS_MapsOfActorsToFindOrRespawn NoLevelActorsMaps;                                 // 0x0430 (size: 0xA0)
    FS_MapsOfActorsToFindOrRespawn CurrentLevelActorsMaps;                            // 0x04D0 (size: 0xA0)
    TMap<TSoftObjectPtr<AActor>, int32> RegisteredFindActorsIndexes;                  // 0x0570 (size: 0x50)
    TMap<class TSoftClassPtr<AActor>, class FS_ArrayOfActorsSaveInfos> ActorsToFindSorted; // 0x05C0 (size: 0x50)
    TArray<FS_ActorSaveInfos> WorkingActorsSaveInfos;                                 // 0x0610 (size: 0x10)
    TMap<class TSoftClassPtr<AActor>, class FS_DatasOfActorsToFindOrRespawn> WorkingMap; // 0x0620 (size: 0x50)
    TMap<class TSoftClassPtr<AActor>, class FS_DatasOfActorsToFindOrRespawn> WorkingMapCurrentLevel; // 0x0670 (size: 0x50)
    TMap<class TSoftClassPtr<AActor>, class FS_DatasOfActorsToFindOrRespawn> WorkingMapNoLevel; // 0x06C0 (size: 0x50)
    TMap<TSoftObjectPtr<AActor>, int32> RegisteredRespawnActorsIndexes;               // 0x0710 (size: 0x50)
    TMap<class TSoftClassPtr<AActor>, class FS_ArrayOfActorsSaveInfos> ActorsToRespawnSorted; // 0x0760 (size: 0x50)
    TMap<class FString, class FString> WorkingMapOfDatas;                             // 0x07B0 (size: 0x50)
    TMap<class FString, class FString> MapOfDatasCurrentLevel;                        // 0x0800 (size: 0x50)
    TMap<class FString, class FString> MapOfDatasNoLevel;                             // 0x0850 (size: 0x50)
    TSoftClassPtr<AActor> WorkingClass;                                               // 0x08A0 (size: 0x28)
    int32 CurrentIndex;                                                               // 0x08C8 (size: 0x4)
    int32 LoadStep;                                                                   // 0x08CC (size: 0x4)
    TArray<FS_SaveOperationInfos> SaveGameOperationsQueue;                            // 0x08D0 (size: 0x10)
    FName LevelToLoadInQueue;                                                         // 0x08E0 (size: 0x8)
    int32 IndexInQueueOfLevelToLoad;                                                  // 0x08E8 (size: 0x4)
    FDateTime LoadedTime;                                                             // 0x08F0 (size: 0x8)
    int32 PlayTime;                                                                   // 0x08F8 (size: 0x4)
    FTimerHandle AutoSavesTimer;                                                      // 0x0900 (size: 0x8)
    class UGameInstance* GameInstance;                                                // 0x0908 (size: 0x8)
    bool AutoSavesPaused?;                                                            // 0x0910 (size: 0x1)
    int32 ThumbnailWarmUpFrames;                                                      // 0x0914 (size: 0x4)
    bool WaitingForThumbnailCapture?;                                                 // 0x0918 (size: 0x1)
    class USceneCaptureComponent2D* SceneCaptureComponent2D;                          // 0x0920 (size: 0x8)
    bool AbsoluteLevelOption;                                                         // 0x0928 (size: 0x1)
    FString LevelInQueueOptions;                                                      // 0x0930 (size: 0x10)
    FString SlotNameOfLevelToLoadInQueue;                                             // 0x0940 (size: 0x10)
    FBP_EasySaveGameOperationsManager_CNewGameInitialization NewGameInitialization;   // 0x0950 (size: 0x10)
    void NewGameInitialization();
    TSoftObjectPtr<UTextureRenderTarget2D> RenderTargetTexture;                       // 0x0960 (size: 0x28)
    bool AlwaysAllowAutoSaves?;                                                       // 0x0988 (size: 0x1)
    FTransform PlayerTransformToSave;                                                 // 0x0990 (size: 0x60)

    void AutoSavesAllowed?(bool& Allowed?);
    void PauseOrResumeAutoSaves(bool Pause?);
    void SaveOrLoadPlayerTransform(TEnumAsByte<E_SaveGameOperationType::Type> OperationType, class UBP_EasySaveGameObject_C* SaveGame);
    void AddOperationToQueue(FS_SaveOperationInfos NewOperationInfos, FName LevelToLoad, bool Absolute, FString Options);
    void DeleteSaveSlot(FString SaveUniqueName);
    void SaveActorsToRespawnOrFind(bool ActorWasDestroyed?, TSoftObjectPtr<UBP_EasySaveGameComponent_C> SaveGameComponentRef, const TSoftClassPtr<AActor>& ActorClass, bool SaveLevel?, FString ActorUniqueID, bool SaveActorDestructionAsVar?);
    void SaveDatasToWorkingMaps();
    void SortActorsToRespawnOrFind(const FS_ActorSaveInfos& ActorSaveInfos, const TSoftObjectPtr<AActor>& ActorRef, const TSoftClassPtr<AActor>& ActorClass, const TMap<class TSoftClassPtr<AActor>, class FS_ArrayOfActorsSaveInfos>& ActorsSourceMap, const TMap<TSoftObjectPtr<AActor>, int32>& RegisteredActorsIndexes);
    void SaveOrLoadCompleted();
    void StartStopLoadingScreen(bool StopLoadingScreen?, bool PlayFadeAnimation?, TEnumAsByte<E_SaveGameOperationType::Type> OperationType);
    void SaveCurrentMetadatas();
    void OnLoaded_9A1A99894A0AF0F88E2E01BC57ADDF5E(UClass* Loaded);
    void InpActEvt_IA_QuickSave_K2Node_EnhancedInputActionEvent_1(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_QuickLoad_K2Node_EnhancedInputActionEvent_0(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void Completed_47F5366F472B474B02BA4BBFFFA239FD(class USaveGame* SaveGame, bool bSuccess);
    void Completed_B71FFDC1411BD40FBA7633BBA3E0F555(class USaveGame* SaveGame, bool bSuccess);
    void OnLoaded_FE88A4C54D5A50DD5A7DCD9FBC958C7B(class UObject* Loaded);
    void StartSaveGameOperation(FS_SaveOperationInfos Save Game Operation Infos);
    void RegisterForSaveFiles(TSoftObjectPtr<AActor> ActorRef, FS_ActorSaveInfos ActorSaveInfos);
    void LoadNewLevel(FS_SaveOperationInfos OperationInfos, FName LevelName, bool Absolute, FString Options);
    void ReceiveTick(float DeltaSeconds);
    void ReceiveBeginPlay();
    void TriggerAutoSave();
    void TriggerQuickSave();
    void QuickLoad();
    void ExecuteUbergraph_BP_EasySaveGameOperationsManager(int32 EntryPoint);
    void NewGameInitialization__DelegateSignature();
    void SaveGameOperationEnded__DelegateSignature(FS_SaveOperationInfos Operation);
    void SaveGameOperationStarted__DelegateSignature(FS_SaveOperationInfos Operation);
}; // Size: 0x9F0

#endif
