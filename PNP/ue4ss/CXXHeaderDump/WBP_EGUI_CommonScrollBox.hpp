#ifndef UE4SS_SDK_WBP_EGUI_CommonScrollBox_HPP
#define UE4SS_SDK_WBP_EGUI_CommonScrollBox_HPP

class UWBP_EGUI_CommonScrollBox_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UNamedSlot* NamedSlot;                                                      // 0x02D8 (size: 0x8)
    class UScrollBox* ScrollBox;                                                      // 0x02E0 (size: 0x8)
    class UPanelWidget* ChildrenContainer;                                            // 0x02E8 (size: 0x8)
    FScrollBarStyle CommonScrollBarStyle;                                             // 0x02F0 (size: 0x650)
    FScrollBoxStyle GlobalStyle;                                                      // 0x0940 (size: 0x2F0)
    FScrollBarStyle ScrollBarStyle;                                                   // 0x0C30 (size: 0x650)
    bool AutoScroll?;                                                                 // 0x1280 (size: 0x1)
    double AutoScrollSpeed;                                                           // 0x1288 (size: 0x8)
    double DelayBetweenAutoScrolls;                                                   // 0x1290 (size: 0x8)
    bool AlwaysShowScrollbar?;                                                        // 0x1298 (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x1299 (size: 0x1)
    double Alpha;                                                                     // 0x12A0 (size: 0x8)
    bool Inverted?;                                                                   // 0x12A8 (size: 0x1)
    FLinearColor AccentColor;                                                         // 0x12AC (size: 0x10)

    class UWidget* DoCustomNavigation(EUINavigation Navigation);
    void BndEvt__WBP_EOM_CommonScrollBox_ScrollBox_K2Node_ComponentBoundEvent_1_OnUserScrolledEvent__DelegateSignature(float CurrentOffset);
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void Construct();
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EGUI_CommonScrollBox(int32 EntryPoint);
}; // Size: 0x12BC

#endif
