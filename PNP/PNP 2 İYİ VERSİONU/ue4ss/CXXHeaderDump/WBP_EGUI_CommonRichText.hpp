#ifndef UE4SS_SDK_WBP_EGUI_CommonRichText_HPP
#define UE4SS_SDK_WBP_EGUI_CommonRichText_HPP

class UWBP_EGUI_CommonRichText_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class URichTextBlock* RichText;                                                   // 0x02D8 (size: 0x8)
    FText Text;                                                                       // 0x02E0 (size: 0x10)
    FS_CommonTextInfo TextStyling;                                                    // 0x02F0 (size: 0x18)
    class UDataTable* RichTextStyleSet;                                               // 0x0308 (size: 0x8)
    TArray<class TSubclassOf<URichTextBlockDecorator>> RichTextDecoratorClasses;      // 0x0310 (size: 0x10)
    bool WrapText?;                                                                   // 0x0320 (size: 0x1)
    bool InitByCodeOnly?;                                                             // 0x0321 (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x0322 (size: 0x1)
    FSlateColor TextColor;                                                            // 0x0324 (size: 0x14)
    bool OverrideColorsOnly?;                                                         // 0x0338 (size: 0x1)
    FTextBlockStyle CustomRichTextStyle;                                              // 0x0340 (size: 0x2E0)

    void SetText(FText InText);
    void GetText(FText& Text);
    void UpdateFontInfos(FS_CommonTextInfo TextStyling, FText Text);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EGUI_CommonRichText(int32 EntryPoint);
}; // Size: 0x620

#endif
