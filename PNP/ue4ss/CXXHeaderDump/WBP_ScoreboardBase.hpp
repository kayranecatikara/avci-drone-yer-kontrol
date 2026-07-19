#ifndef UE4SS_SDK_WBP_ScoreboardBase_HPP
#define UE4SS_SDK_WBP_ScoreboardBase_HPP

class UWBP_ScoreboardBase_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* Gate;                                                     // 0x02D8 (size: 0x8)
    class UImage* Image_Line;                                                         // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* WBP_EGUI_CommonText;                                // 0x02E8 (size: 0x8)
    class UWBP_ScoreboardPanel_C* WBP_ScoreboardPanel;                                // 0x02F0 (size: 0x8)

    void ShowNoDataText(ESlateVisibility InVisibility);
    void ExecuteUbergraph_WBP_ScoreboardBase(int32 EntryPoint);
}; // Size: 0x2F8

#endif
