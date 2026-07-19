#ifndef UE4SS_SDK_BP_GameInstance_HPP
#define UE4SS_SDK_BP_GameInstance_HPP

class UBP_GameInstance_C : public UGameInstance
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x01C0 (size: 0x8)
    TEnumAsByte<E_Levels::Type> ELevel;                                               // 0x01C8 (size: 0x1)
    TEnumAsByte<E_UAV::Type> EUAV;                                                    // 0x01C9 (size: 0x1)
    double Reverse Roll Axis;                                                         // 0x01D0 (size: 0x8)
    double Reverse Throttle Axis;                                                     // 0x01D8 (size: 0x8)
    double Reverse Pitch Axis;                                                        // 0x01E0 (size: 0x8)
    double Reverse Yaw Axis;                                                          // 0x01E8 (size: 0x8)
    TEnumAsByte<E_Controller::Type> EController;                                      // 0x01F0 (size: 0x1)
    TEnumAsByte<E_ExplosiveType::Type> EExplosiveType;                                // 0x01F1 (size: 0x1)
    FText PlayerNickname;                                                             // 0x01F8 (size: 0x10)
    bool canUseThermal;                                                               // 0x0208 (size: 0x1)
    bool canUseLockKit;                                                               // 0x0209 (size: 0x1)
    TEnumAsByte<E_MapMode::Type> EMapMode;                                            // 0x020A (size: 0x1)
    int32 PoleEnemyCount;                                                             // 0x020C (size: 0x4)
    int32 RuinedCityEnemyCount;                                                       // 0x0210 (size: 0x4)
    int32 RuralEnemyCount;                                                            // 0x0214 (size: 0x4)
    double DeadZone;                                                                  // 0x0218 (size: 0x8)
    bool canUsePushImpact;                                                            // 0x0220 (size: 0x1)
    FSimpleControllerMappingProfile MappingProfilePlayer;                             // 0x0228 (size: 0x150)
    FString deviceName;                                                               // 0x0378 (size: 0x10)
    int32 MilitaryAirportEnemyCount;                                                  // 0x0388 (size: 0x4)
    FString ProfileName;                                                              // 0x0390 (size: 0x10)
    int32 PeakEnemyCount;                                                             // 0x03A0 (size: 0x4)
    TEnumAsByte<E_FiberType::Type> EFiberType;                                        // 0x03A4 (size: 0x1)
    TEnumAsByte<E_GameStates::Type> E Game State;                                     // 0x03A5 (size: 0x1)
    class UDataTable* DTMaps;                                                         // 0x03A8 (size: 0x8)
    ESimpleControllerType ControllerType;                                             // 0x03B0 (size: 0x1)
    double RC Expo Roll;                                                              // 0x03B8 (size: 0x8)
    double RC Expo Pitch;                                                             // 0x03C0 (size: 0x8)
    double RC Expo Yaw;                                                               // 0x03C8 (size: 0x8)
    double Axis Speed Roll;                                                           // 0x03D0 (size: 0x8)
    double Axis Speed Pitch;                                                          // 0x03D8 (size: 0x8)
    double Axis Speed Yaw;                                                            // 0x03E0 (size: 0x8)
    double FieldOfView;                                                               // 0x03E8 (size: 0x8)
    bool isLoggedBefore;                                                              // 0x03F0 (size: 0x1)
    TEnumAsByte<E_UAV_FlightMode::Type> EUAV Flight Mode;                             // 0x03F1 (size: 0x1)
    double TotalPlayTime;                                                             // 0x03F8 (size: 0x8)
    class UBP_SaveGame_ScoreBoard_C* BP Save Game Score Board;                        // 0x0400 (size: 0x8)
    class AGM_UAVBase_C* GM UAVBase;                                                  // 0x0408 (size: 0x8)
    double TotalFlightTime;                                                           // 0x0410 (size: 0x8)
    int32 TotalKillCount;                                                             // 0x0418 (size: 0x4)
    TEnumAsByte<E_UAVType::Type> EUAV Type;                                           // 0x041C (size: 0x1)

    void Set Explosive Type(TEnumAsByte<E_ExplosiveType::Type> EExplosiveType);
    void LoadLevel();
    void Set E Controller(TEnumAsByte<E_Controller::Type> EController);
    void Set Level(TEnumAsByte<E_Levels::Type> Level);
    void ReceiveInit();
    void ReceiveShutdown();
    void AutoSaveTotalTime();
    void CalculateTotalPlayTime();
    void CalculateTotalFlyPlayTime();
    void AutoSaveFlyTotalTime();
    void SaveTotalKillCount();
    void CalculateTotalKillCount();
    void ExecuteUbergraph_BP_GameInstance(int32 EntryPoint);
}; // Size: 0x41D

#endif
