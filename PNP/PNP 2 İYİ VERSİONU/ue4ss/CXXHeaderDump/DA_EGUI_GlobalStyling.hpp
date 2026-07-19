#ifndef UE4SS_SDK_DA_EGUI_GlobalStyling_HPP
#define UE4SS_SDK_DA_EGUI_GlobalStyling_HPP

class UDA_EGUI_GlobalStyling_C : public UPrimaryDataAsset
{
    FLinearColor AccentColor;                                                         // 0x0030 (size: 0x10)
    FLinearColor InputPromptIconColor;                                                // 0x0040 (size: 0x10)
    FSlateColor PrimaryTextColor;                                                     // 0x0050 (size: 0x14)
    FSlateColor InvertedTextColor;                                                    // 0x0064 (size: 0x14)
    TMap<TEnumAsByte<E_FontTypeFaces::Type>, FS_FontsStylingInfos> Fonts;             // 0x0078 (size: 0x50)
    FButtonStyle DefaultButtonStyle;                                                  // 0x00D0 (size: 0x370)
    FButtonStyle SecondaryButtonStyle;                                                // 0x0440 (size: 0x370)
    FScrollBoxStyle CommonScrollBoxStyle;                                             // 0x07B0 (size: 0x2F0)
    FScrollBarStyle CommonScrollBarStyle;                                             // 0x0AA0 (size: 0x650)
    TEnumAsByte<E_BackgroundStyleSelector::Type> SettingBackgroundStyle;              // 0x10F0 (size: 0x1)
    TEnumAsByte<E_BackgroundStyleSelector::Type> SettingBackgroundActiveStyle;        // 0x10F1 (size: 0x1)
    TEnumAsByte<E_BackgroundStyleSelector::Type> OptionsSelectorsBackgroundStyle;     // 0x10F2 (size: 0x1)
    TEnumAsByte<E_ButtonStyleSelector::Type> SettingToggleButtonsStyle;               // 0x10F3 (size: 0x1)
    TEnumAsByte<E_ButtonStyleSelector::Type> ResetSettingButtonStyle;                 // 0x10F4 (size: 0x1)
    FProgressBarStyle ProgressBarStyle;                                               // 0x1100 (size: 0x230)
    FSpinBoxStyle SpinBoxStyle;                                                       // 0x1330 (size: 0x520)
    bool UseInvertedTextColorInSpinBox?;                                              // 0x1850 (size: 0x1)
    FSlateBrush KeySelectorNormalStyle;                                               // 0x1860 (size: 0xB0)
    FSlateBrush KeySelectorActiveStyle;                                               // 0x1910 (size: 0xB0)
    FSlateBrush SettingDirtyIndicatorBrush;                                           // 0x19C0 (size: 0xB0)
    FS_CommonTextInfo EOMSettingTitleTextStyle;                                       // 0x1A70 (size: 0x18)
    FMargin SettingDirtyIndicatorPadding;                                             // 0x1A88 (size: 0x10)
    FButtonStyle Alternative01ButtonStyle;                                            // 0x1AA0 (size: 0x370)
    FButtonStyle Alternative02ButtonStyle;                                            // 0x1E10 (size: 0x370)
    class UTexture2D* GameLogo;                                                       // 0x2180 (size: 0x8)
    TMap<TEnumAsByte<EMouseCursor::Type>, TSoftClassPtr<UUserWidget>> GlobalCursorStyling; // 0x2188 (size: 0x50)
    TEnumAsByte<E_GamepadBrand::Type> DefaultGamepadKeysBrand;                        // 0x21D8 (size: 0x1)
    TMap<TEnumAsByte<E_BackgroundStyleSelector::Type>, FSlateBrush> CommonBackgroundStyles; // 0x21E0 (size: 0x50)
    TEnumAsByte<E_GamepadBrand::Type> ActiveGamepadKeysBrand;                         // 0x2230 (size: 0x1)
    FButtonStyle Alternative03ButtonStyle;                                            // 0x2240 (size: 0x370)
    FButtonStyle Alternative04ButtonStyle;                                            // 0x25B0 (size: 0x370)
    FButtonStyle Alternative05ButtonStyle;                                            // 0x2920 (size: 0x370)
    TSoftObjectPtr<UTexture2D> SelectorArrowTexture;                                  // 0x2C90 (size: 0x28)
    bool UseAccentColorOnSelectorArrow?;                                              // 0x2CB8 (size: 0x1)
    FS_CreditsTextStyling SectionTitleStyle;                                          // 0x2CC0 (size: 0x38)
    FS_CreditsTextStyling TextSectionRoleStyle;                                       // 0x2CF8 (size: 0x38)
    FS_CreditsTextStyling TextSectionNamesStyle;                                      // 0x2D30 (size: 0x38)
    FMargin TextSectionOuterMargin;                                                   // 0x2D68 (size: 0x10)
    FS_CommonTextInfo EOMOptionsValuesTextStyle;                                      // 0x2D78 (size: 0x18)
    class UMaterialInterface* InputPromptOverlayMaterial;                             // 0x2D90 (size: 0x8)
    FName InputPromptOverlayMaterialParameterName;                                    // 0x2D98 (size: 0x8)
    FS_CommonTextInfo EPMSettingTitleTextStyle;                                       // 0x2DA0 (size: 0x18)
    FS_CommonTextInfo EPMOptionsValuesTextStyle;                                      // 0x2DB8 (size: 0x18)

    void UpdateSlateBrushRoundingValues(const FSlateBrush& SlateBrush, FVector4 Corner Radii, TEnumAsByte<ESlateBrushRoundingType::Type> Rounding Type, FSlateBrush& SlateBrushOut);
    void GetDefaultBackgroundRoundingValues(FVector4& Corner Radii, TEnumAsByte<ESlateBrushRoundingType::Type>& Rounding Type);
    void GetBackgroundStyling(TEnumAsByte<E_BackgroundStyleSelector::Type> StyleSelector, TEnumAsByte<ESlateBrushRoundingType::Type> RequestedRoundingType, FSlateBrush& BackgroundStyling);
    void GetButtonStyling(TEnumAsByte<E_ButtonStyleSelector::Type> ButtonStyle, TEnumAsByte<ESlateBrushRoundingType::Type> PreferedRoundingType, FButtonStyle& OutButtonStyle);
    void GetFont(FS_FontSelector FontInfos, bool FixFontScaling?, FSlateFontInfo& Font, FVector2D& Shadow offset, FLinearColor& Shadow Color);
}; // Size: 0x2DD0

#endif
