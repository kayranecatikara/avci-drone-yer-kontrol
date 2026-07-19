#ifndef UE4SS_SDK_WBP_WarningInfo_HPP
#define UE4SS_SDK_WBP_WarningInfo_HPP

class UWBP_WarningInfo_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* Entry;                                                    // 0x02D8 (size: 0x8)
    class UTextBlock* TextBlock_Info;                                                 // 0x02E0 (size: 0x8)
    FText Text_Info;                                                                  // 0x02E8 (size: 0x10)

    void Construct();
    void ExecuteUbergraph_WBP_WarningInfo(int32 EntryPoint);
}; // Size: 0x2F8

#endif
