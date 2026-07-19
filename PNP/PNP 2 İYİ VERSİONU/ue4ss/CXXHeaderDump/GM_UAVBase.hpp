#ifndef UE4SS_SDK_GM_UAVBase_HPP
#define UE4SS_SDK_GM_UAVBase_HPP

class AGM_UAVBase_C : public AGameModeBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0340 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0348 (size: 0x8)
    int32 FailCrashCount;                                                             // 0x0350 (size: 0x4)
    int32 SuccesCrashCount;                                                           // 0x0354 (size: 0x4)
    int32 ScoreboardDegreeCount;                                                      // 0x0358 (size: 0x4)
    int32 SoldierCount;                                                               // 0x035C (size: 0x4)
    int32 DroneCount;                                                                 // 0x0360 (size: 0x4)
    int32 VehicleCount;                                                               // 0x0364 (size: 0x4)
    int32 HelicopterCount;                                                            // 0x0368 (size: 0x4)
    int32 HeavyCount;                                                                 // 0x036C (size: 0x4)
    int32 FixedGunCount;                                                              // 0x0370 (size: 0x4)
    int32 CurrentKilledEnemyCount;                                                    // 0x0374 (size: 0x4)
    int32 AllEnemyCount;                                                              // 0x0378 (size: 0x4)
    class AHUD_MainUAV_C* HUD Main UAV;                                               // 0x0380 (size: 0x8)
    FString SaveScoreboardName;                                                       // 0x0388 (size: 0x10)
    class USaveGame* SaveScoreboardRef;                                               // 0x0398 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x03A0 (size: 0x8)
    TArray<class ABPP_BaseEnemyCar_C*> BPP Enemy Cars;                                // 0x03A8 (size: 0x10)
    TArray<class ABP_AI_EnemySoldier_C*> BP AI Enemy Soldiers;                        // 0x03B8 (size: 0x10)
    TArray<class ABP_OPSoldier_C*> BP OP Soldiers;                                    // 0x03C8 (size: 0x10)
    int32 TotalVehicleCount;                                                          // 0x03D8 (size: 0x4)
    int32 TotalHelicopterCount;                                                       // 0x03DC (size: 0x4)
    int32 TotalHeavyCount;                                                            // 0x03E0 (size: 0x4)
    int32 TotalFixedGunCount;                                                         // 0x03E4 (size: 0x4)
    FTimerHandle ScoreboardTotalTimerHandle;                                          // 0x03E8 (size: 0x8)
    int32 GameScoreboardSecondsTimer;                                                 // 0x03F0 (size: 0x4)
    int32 GameScoreboardMinutesTimer;                                                 // 0x03F4 (size: 0x4)
    int32 ScoreboardSecondsTimer;                                                     // 0x03F8 (size: 0x4)
    int32 ScoreboardMinutesTimer;                                                     // 0x03FC (size: 0x4)
    class ABPP_UAV_C* BPP UAV;                                                        // 0x0400 (size: 0x8)
    int32 CurrentCheckpointCount;                                                     // 0x0408 (size: 0x4)
    TArray<class ABP_Checkpoint_C*> AllCheckpoints;                                   // 0x0410 (size: 0x10)
    int32 TotalCheckpointCount;                                                       // 0x0420 (size: 0x4)
    bool isCompletedRace;                                                             // 0x0424 (size: 0x1)
    class UDataTable* DT UAV;                                                         // 0x0428 (size: 0x8)
    class UBP_SaveGame_ScoreBoard_C* BP Save Game Score Board;                        // 0x0430 (size: 0x8)
    class ABPP_UAV_SpawnPoint_C* UAV Spawn Point;                                     // 0x0438 (size: 0x8)
    TArray<class TSubclassOf<APawn>> StarterPlatforms;                                // 0x0440 (size: 0x10)
    TSubclassOf<class APawn> SpawnedStarterPlatform;                                  // 0x0450 (size: 0x8)
    class ABPP_Spectator_C* BPP Spectator;                                            // 0x0458 (size: 0x8)
    class ABPP_AIDroneTalon_C* AIDroneTalon;                                          // 0x0460 (size: 0x8)
    TArray<class ABPP_AIDroneTalon_C*> Out Actors;                                    // 0x0468 (size: 0x10)

    void GetSelectionDrone(TSubclassOf<class ABPP_UAV_C>& SelectedDrone);
    void SaveScoreBoard();
    void UpdateFailCrashCount();
    void UpdateSuccessCrashCount();
    void UpdateScoreboardDegreeCount();
    void UpdateEnemyCount(TEnumAsByte<E_EnemyCarType::Type> Vehicle, bool NotVehicle, int32 SoldierAndDrone);
    void ReceiveBeginPlay();
    void UpdateCheckpointInformation();
    void RestartRaceModeSettings();
    void SuccessKamikaze(bool isFail, FString WhoDead);
    void FailKamikaze();
    void SuccessNet();
    void FailNet();
    void DamageVehicle(FString WhoDead);
    void SuccessNotifyKillFeed(FString WhoDead);
    void InteractDrone();
    void UpdateEnemyKilledCount();
    void FlyMinTimer();
    void ExecuteUbergraph_GM_UAVBase(int32 EntryPoint);
}; // Size: 0x478

#endif
