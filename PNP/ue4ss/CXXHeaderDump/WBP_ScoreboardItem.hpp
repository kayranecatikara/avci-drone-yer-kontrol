#ifndef UE4SS_SDK_WBP_ScoreboardItem_HPP
#define UE4SS_SDK_WBP_ScoreboardItem_HPP

class UWBP_ScoreboardItem_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* ItemAnim;                                                 // 0x02D8 (size: 0x8)
    class UTextBlock* TextBlock_Date;                                                 // 0x02E0 (size: 0x8)
    class UTextBlock* TextBlock_DateTime;                                             // 0x02E8 (size: 0x8)
    class UTextBlock* TextBlock_FailCrash;                                            // 0x02F0 (size: 0x8)
    class UTextBlock* TextBlock_SuccessScore;                                         // 0x02F8 (size: 0x8)
    class UTextBlock* TextBlock_TotalCrash;                                           // 0x0300 (size: 0x8)
    class UTextBlock* TextBlock_TotalTime;                                            // 0x0308 (size: 0x8)
    FText Text_FailScore;                                                             // 0x0310 (size: 0x10)
    FText Text_SuccessScore;                                                          // 0x0320 (size: 0x10)
    FText Text_TotalScore;                                                            // 0x0330 (size: 0x10)
    FText Text_TotalTime;                                                             // 0x0340 (size: 0x10)
    FText Text_Date;                                                                  // 0x0350 (size: 0x10)
    FText Text_DateTime;                                                              // 0x0360 (size: 0x10)

    void Construct();
    void ExecuteUbergraph_WBP_ScoreboardItem(int32 EntryPoint);
}; // Size: 0x370

#endif
