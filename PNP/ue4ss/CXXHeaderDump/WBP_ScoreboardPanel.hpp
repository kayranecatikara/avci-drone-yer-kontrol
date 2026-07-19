#ifndef UE4SS_SDK_WBP_ScoreboardPanel_HPP
#define UE4SS_SDK_WBP_ScoreboardPanel_HPP

class UWBP_ScoreboardPanel_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UScrollBox* ScrollBox;                                                      // 0x02D8 (size: 0x8)

    void Notify_Scoreboard(FString FailCrash, FString SuccessCrash, FString TotalCrash, FString Date, FString DateTime, FString TotalTime);
    void ClearChildItems();
    void Notify_Killfeed(FString Killer, FString WhoDead, bool isNet, bool isFail);
    void ExecuteUbergraph_WBP_ScoreboardPanel(int32 EntryPoint);
}; // Size: 0x2E0

#endif
