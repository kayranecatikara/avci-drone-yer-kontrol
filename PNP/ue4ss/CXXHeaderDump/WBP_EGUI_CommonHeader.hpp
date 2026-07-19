#ifndef UE4SS_SDK_WBP_EGUI_CommonHeader_HPP
#define UE4SS_SDK_WBP_EGUI_CommonHeader_HPP

class UWBP_EGUI_CommonHeader_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UHorizontalBox* ActiveTabIndicator;                                         // 0x02D8 (size: 0x8)
    class UHorizontalBox* Header;                                                     // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* TitleText;                                          // 0x02E8 (size: 0x8)
    TArray<class UWBP_EGUI_CommonButton_C*> ButtonsReferences;                        // 0x02F0 (size: 0x10)
    TArray<FS_CultureInvariantOptionsValues> TabsDefinition;                          // 0x0300 (size: 0x10)
    int32 DefaultActiveTab;                                                           // 0x0310 (size: 0x4)
    bool ManuallySelectInitialTab?;                                                   // 0x0314 (size: 0x1)
    class UWidgetSwitcher* WidgetSwitcherRef;                                         // 0x0318 (size: 0x8)
    bool DisplayTitleOnly?;                                                           // 0x0320 (size: 0x1)
    bool DisplayActiveTabIndicator?;                                                  // 0x0321 (size: 0x1)
    FMargin TabIndicatorsPadding;                                                     // 0x0324 (size: 0x10)
    FS_CommonTextInfo ButtonsTextStyling;                                             // 0x0338 (size: 0x18)
    double ButtonsSpacing;                                                            // 0x0350 (size: 0x8)
    TEnumAsByte<E_ButtonStyleSelector::Type> ButtonsStyle;                            // 0x0358 (size: 0x1)
    FMargin ButtonsTextPadding;                                                       // 0x035C (size: 0x10)
    TEnumAsByte<E_SelectionIndicatorPosition::Type> ButtonSelectionIndicatorPosition; // 0x036C (size: 0x1)
    FS_CommonTextInfo TitleTextStyling;                                               // 0x0370 (size: 0x18)
    FWBP_EGUI_CommonHeader_CNewTabSelected NewTabSelected;                            // 0x0388 (size: 0x10)
    void NewTabSelected(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    int32 CurrentTab;                                                                 // 0x0398 (size: 0x4)
    TArray<class UWBP_ActiveSelectIndicator_C*> SelectionIndicators;                  // 0x03A0 (size: 0x10)

    void RefreshSelectionIndicators();
    void GetTabName(int32 ButtonIndex, FText& Text, FString& Text Culture Invariant);
    void GoToPreviousOrNextTab(bool Next?);
    void CreateNewButton(FText ButtonTitle, int32 CurrentIndex);
    void ButtonClicked_Event(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void Construct();
    void SelectInitialTab(int32 TabIndex);
    void ExecuteUbergraph_WBP_EGUI_CommonHeader(int32 EntryPoint);
    void NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
}; // Size: 0x3B0

#endif
