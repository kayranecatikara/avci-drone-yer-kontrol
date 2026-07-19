#ifndef UE4SS_SDK_S_Scoreboard_HPP
#define UE4SS_SDK_S_Scoreboard_HPP

struct FS_Scoreboard
{
    TArray<int32> FailCrashCount_17_6D773F8346B7495634BB19BEDA322120;                 // 0x0000 (size: 0x10)
    TArray<int32> SuccesCrashCount_19_761C44FF4477F74B850E368873DB5761;               // 0x0010 (size: 0x10)
    int32 ScoreboardDegreeCount_20_79FB3A3C455656865CA61582E1FB64CF;                  // 0x0020 (size: 0x4)
    TArray<FString> ScoreboardDate_22_B4608C864B337E224ADD2DAFF9621EED;               // 0x0028 (size: 0x10)
    TArray<FString> ScoreboardDateTime_25_2CECB5EC45F47526D8B4E19CEDC2F7E8;           // 0x0038 (size: 0x10)
    TArray<FString> ScoreboardTotalTime_26_99CDA16B4339FD419322C0ADB11F944E;          // 0x0048 (size: 0x10)

}; // Size: 0x58

#endif
