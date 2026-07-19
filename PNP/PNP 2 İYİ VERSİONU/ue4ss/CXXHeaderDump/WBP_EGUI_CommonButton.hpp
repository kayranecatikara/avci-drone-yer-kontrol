#ifndef UE4SS_SDK_WBP_EGUI_CommonButton_HPP
#define UE4SS_SDK_WBP_EGUI_CommonButton_HPP

class UWBP_EGUI_CommonButton_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* SelectionIndicatorFadeInOut;                              // 0x02D8 (size: 0x8)
    class UButton* Button;                                                            // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* ButtonText;                                         // 0x02E8 (size: 0x8)
    class UImage* SelectionIndicator;                                                 // 0x02F0 (size: 0x8)
    TArray<class UWBP_EGUI_CommonButton_C*> ButtonList;                               // 0x02F8 (size: 0x10)
    FText Text;                                                                       // 0x0308 (size: 0x10)
    FS_CommonTextInfo Text Styling;                                                   // 0x0318 (size: 0x18)
    FMargin TextPadding;                                                              // 0x0330 (size: 0x10)
    TEnumAsByte<EHorizontalAlignment> ButtonHorizontalAlignment;                      // 0x0340 (size: 0x1)
    TEnumAsByte<EVerticalAlignment> ButtonVerticalAlignment;                          // 0x0341 (size: 0x1)
    bool IsActive?;                                                                   // 0x0342 (size: 0x1)
    bool AlwaysResetActiveState?;                                                     // 0x0343 (size: 0x1)
    bool SearchForSiblings?;                                                          // 0x0344 (size: 0x1)
    TEnumAsByte<E_SelectionIndicatorPosition::Type> SelectionIndicatorPosition;       // 0x0345 (size: 0x1)
    TEnumAsByte<E_ButtonStyleSelector::Type> ButtonStyle;                             // 0x0346 (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x0347 (size: 0x1)
    TEnumAsByte<ESlateBrushRoundingType::Type> PreferedRoundingType;                  // 0x0348 (size: 0x1)
    FSlateBrush NormalButtonStyle;                                                    // 0x0350 (size: 0xB0)
    FSlateBrush HoveredButtonStyle;                                                   // 0x0400 (size: 0xB0)
    FSlateBrush PressedButtonStyle;                                                   // 0x04B0 (size: 0xB0)
    int32 SelfIndex;                                                                  // 0x0560 (size: 0x4)
    FWBP_EGUI_CommonButton_CButtonClicked ButtonClicked;                              // 0x0568 (size: 0x10)
    void ButtonClicked(int32 SelfIndex);
    FWBP_EGUI_CommonButton_CButtonPressed ButtonPressed;                              // 0x0578 (size: 0x10)
    void ButtonPressed();
    FWBP_EGUI_CommonButton_CButtonReleased ButtonReleased;                            // 0x0588 (size: 0x10)
    void ButtonReleased();
    FWBP_EGUI_CommonButton_CButtonFocused ButtonFocused;                              // 0x0598 (size: 0x10)
    void ButtonFocused(int32 SelfIndex);
    FWBP_EGUI_CommonButton_CButtonUnfocused ButtonUnfocused;                          // 0x05A8 (size: 0x10)
    void ButtonUnfocused();
    bool InitByCodeOnly?;                                                             // 0x05B8 (size: 0x1)
    bool In Is Enabled;                                                               // 0x05B9 (size: 0x1)

    FEventReply OnFocusReceived(FGeometry MyGeometry, FFocusEvent InFocusEvent);
    void SetHoverStylingState(bool UpdateTextColor?);
    void SetActiveStylingState(bool UpdateTextColor?);
    void SetNormalStylingState(bool UpdateTextColor?);
    void InitButtonStyling();
    void InitTextStyling();
    void InitSelectionIndicator();
    void GetSiblingsButtons();
    void BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature();
    void PreConstruct(bool IsDesignTime);
    void BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_4_OnButtonPressedEvent__DelegateSignature();
    void BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_5_OnButtonReleasedEvent__DelegateSignature();
    void BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature();
    void BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature();
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void OnRemovedFromFocusPath(FFocusEvent InFocusEvent);
    void TriggerClickEvent();
    void Construct();
    void InitButton();
    void ExecuteUbergraph_WBP_EGUI_CommonButton(int32 EntryPoint);
    void ButtonUnfocused__DelegateSignature();
    void ButtonFocused__DelegateSignature(int32 SelfIndex);
    void ButtonReleased__DelegateSignature();
    void ButtonPressed__DelegateSignature();
    void ButtonClicked__DelegateSignature(int32 SelfIndex);
}; // Size: 0x5BA

#endif
