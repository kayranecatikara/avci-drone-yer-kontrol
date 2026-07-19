#ifndef UE4SS_SDK_WBP_EGUI_CommonBackground_HPP
#define UE4SS_SDK_WBP_EGUI_CommonBackground_HPP

class UWBP_EGUI_CommonBackground_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBorder* Background;                                                        // 0x02D8 (size: 0x8)
    class UNamedSlot* NamedSlot;                                                      // 0x02E0 (size: 0x8)
    bool InitByCodeOnly?;                                                             // 0x02E8 (size: 0x1)
    TEnumAsByte<E_BackgroundStyleSelector::Type> NormalStyleSelector;                 // 0x02E9 (size: 0x1)
    TEnumAsByte<E_BackgroundStyleSelector::Type> ActiveStyleSelector;                 // 0x02EA (size: 0x1)
    TEnumAsByte<ESlateBrushRoundingType::Type> CornerRoundingType;                    // 0x02EB (size: 0x1)
    FMargin SlotPadding;                                                              // 0x02EC (size: 0x10)
    TEnumAsByte<EHorizontalAlignment> SlotHorizontalAlignment;                        // 0x02FC (size: 0x1)
    TEnumAsByte<EVerticalAlignment> SlotVerticalAlignment;                            // 0x02FD (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x02FE (size: 0x1)
    FLinearColor NormalBackgroundColor;                                               // 0x0300 (size: 0x10)
    FLinearColor ActiveBackgroundColor;                                               // 0x0310 (size: 0x10)
    bool OutlineUseBackgroundTransparency?;                                           // 0x0320 (size: 0x1)
    bool OnlyOverrideColors?;                                                         // 0x0321 (size: 0x1)
    FSlateBrush NormalBackgroundStyling;                                              // 0x0330 (size: 0xB0)
    FSlateBrush ActiveBackgroundStyling;                                              // 0x03E0 (size: 0xB0)

    void GetBackgroundStylingFromConfig();
    void SetBackgroundNormal();
    void SetBackgroundActive();
    void PreConstruct(bool IsDesignTime);
    void InitStyling();
    void ExecuteUbergraph_WBP_EGUI_CommonBackground(int32 EntryPoint);
}; // Size: 0x490

#endif
