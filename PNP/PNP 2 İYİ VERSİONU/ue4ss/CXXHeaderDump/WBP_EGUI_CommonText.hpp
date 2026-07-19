#ifndef UE4SS_SDK_WBP_EGUI_CommonText_HPP
#define UE4SS_SDK_WBP_EGUI_CommonText_HPP

class UWBP_EGUI_CommonText_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UTextBlock* TextWidget;                                                     // 0x02D8 (size: 0x8)
    FText Text;                                                                       // 0x02E0 (size: 0x10)
    FS_CommonTextInfo TextStyling;                                                    // 0x02F0 (size: 0x18)
    class UMaterialInterface* FontMaterialOverride;                                   // 0x0308 (size: 0x8)
    bool WrapText?;                                                                   // 0x0310 (size: 0x1)
    bool InitByCodeOnly?;                                                             // 0x0311 (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x0312 (size: 0x1)
    FSlateColor TextColor;                                                            // 0x0314 (size: 0x14)
    FSlateColor Inverted Text Color;                                                  // 0x0328 (size: 0x14)
    bool OverrideColorsOnly?;                                                         // 0x033C (size: 0x1)
    FSlateFontInfo CustomTextFont;                                                    // 0x0340 (size: 0x60)
    FVector2D TextShadowOffset;                                                       // 0x03A0 (size: 0x10)
    FLinearColor TextShadowColor;                                                     // 0x03B0 (size: 0x10)

    void SetText(FText InText);
    void GetText(FText& Text);
    void SwitchTextColor(bool Inverted?);
    void UpdateFontInfos(FS_CommonTextInfo TextStyling, FText Text);
    void UpdateTextStyling(FS_CommonTextInfo TextStyling);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EGUI_CommonText(int32 EntryPoint);
}; // Size: 0x3C0

#endif
