#ifndef UE4SS_SDK_BP_SaveGame_ScoreBoard_HPP
#define UE4SS_SDK_BP_SaveGame_ScoreBoard_HPP

class UBP_SaveGame_ScoreBoard_C : public USaveGame
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0028 (size: 0x8)
    FS_Scoreboard ScoreboardPole;                                                     // 0x0030 (size: 0x58)
    FS_Scoreboard ScoreboardRuinedCity;                                               // 0x0088 (size: 0x58)
    FS_Scoreboard ScoreboardRural;                                                    // 0x00E0 (size: 0x58)
    FS_Scoreboard ScoreboardMilitaryAirport;                                          // 0x0138 (size: 0x58)
    FS_Scoreboard ScoreboardPeak;                                                     // 0x0190 (size: 0x58)
    FS_Scoreboard ScoreboardJungle;                                                   // 0x01E8 (size: 0x58)
    FS_Scoreboard ScoreboardTrench;                                                   // 0x0240 (size: 0x58)
    double TotalTime;                                                                 // 0x0298 (size: 0x8)
    double TotalFlyTime;                                                              // 0x02A0 (size: 0x8)
    int32 TotalKillCount;                                                             // 0x02A8 (size: 0x4)

    FS_Scoreboard GetScoreboard(TEnumAsByte<E_Levels::Type> Level);
    void SaveScorebaordData(TEnumAsByte<E_Levels::Type> Level, const int32 FailCrashCount, const int32 SuccessCrashCount, const FString TotalTime);
    void ExecuteUbergraph_BP_SaveGame_ScoreBoard(int32 EntryPoint);
}; // Size: 0x2AC

#endif
