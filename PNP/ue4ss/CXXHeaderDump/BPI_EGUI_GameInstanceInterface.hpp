#ifndef UE4SS_SDK_BPI_EGUI_GameInstanceInterface_HPP
#define UE4SS_SDK_BPI_EGUI_GameInstanceInterface_HPP

class IBPI_EGUI_GameInstanceInterface_C : public IInterface
{

    void GetSaveGameOperationsAllowed(bool& SaveOperationsAllowed?, bool& LoadOperationsAllowed?);
    void SetSaveGameOperationsAllowed(bool SaveOperationsAllowed?, bool LoadOperationsAllowed?);
    void SetIsNewSaveFile?(bool IsNewSaveFile?);
    void SetNewActiveLoadingScreen(class UWBP_ESGU_LoadingScreen_C* LoadingScreenWidget);
    void GetCurrentActiveLoadingScreen(class UWBP_ESGU_LoadingScreen_C*& LoadingScreenWidget);
    void HasGameBenchmarkBeenRequested?(bool& BenchmarkRequested?);
    void SetupGameInstanceForGameBenchmark(bool BenchmarkComplete?);
    void SetupGameInstanceForSaveGameOperation(FS_SaveOperationInfos SaveGameOperation, FName Level, bool Absolute, FString Options, bool ForceOperation?);
    void StartSaveGameOperation(FS_SaveOperationInfos Save Game Operation Infos, bool UsePreviousDatas?, bool ForceOperation?);
    void RegisterForSaveGame(TSoftObjectPtr<AActor> ActorRef, FS_ActorSaveInfos ActorInfos);
}; // Size: 0x28

#endif
