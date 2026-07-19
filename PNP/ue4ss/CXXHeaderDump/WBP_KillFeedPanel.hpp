#ifndef UE4SS_SDK_WBP_KillFeedPanel_HPP
#define UE4SS_SDK_WBP_KillFeedPanel_HPP

class UWBP_KillFeedPanel_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UVerticalBox* VerticalBox_KillFeed;                                         // 0x02D8 (size: 0x8)
    class ABPP_UAV_C* BPP Main Drone;                                                 // 0x02E0 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x02E8 (size: 0x8)
    class AGM_UAVBase_C* GM  UAV Base;                                                // 0x02F0 (size: 0x8)
    class UDataTable* DTMaps;                                                         // 0x02F8 (size: 0x8)

    void Notify_Killfeed(FString Killer, FString WhoDead, bool isNet, bool isFail);
    void Construct();
    void Notify_Scoreboard(FString FailCrash, FString SuccessCrash, FString TotalCrash, FString Date, FString DateTime, FString TotalTime);
    void ExecuteUbergraph_WBP_KillFeedPanel(int32 EntryPoint);
}; // Size: 0x300

#endif
