#ifndef UE4SS_SDK_WBP_EGUI_CommonTooltip_HPP
#define UE4SS_SDK_WBP_EGUI_CommonTooltip_HPP

class UWBP_EGUI_CommonTooltip_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonBackground_C* Background;                                   // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonRichText_C* RichText;                                       // 0x02E0 (size: 0x8)
    FS_CommonTextInfo TextStyling;                                                    // 0x02E8 (size: 0x18)

    void Construct();
    void UpdateText(FText InText);
    void ExecuteUbergraph_WBP_EGUI_CommonTooltip(int32 EntryPoint);
}; // Size: 0x300

#endif
