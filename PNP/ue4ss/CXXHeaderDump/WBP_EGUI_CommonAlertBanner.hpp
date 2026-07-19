#ifndef UE4SS_SDK_WBP_EGUI_CommonAlertBanner_HPP
#define UE4SS_SDK_WBP_EGUI_CommonAlertBanner_HPP

class UWBP_EGUI_CommonAlertBanner_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UHorizontalBox* ButtonContainer;                                            // 0x02D8 (size: 0x8)
    class UBorder* Divider;                                                           // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* OptionDescription;                                  // 0x02E8 (size: 0x8)
    FS_AlertBannerSetupInfos AlertBannerSetupInfos;                                   // 0x02F0 (size: 0x38)
    FS_CommonTextInfo DescriptionTextStyling;                                         // 0x0328 (size: 0x18)
    FS_CommonTextInfo ButtonTextStyling;                                              // 0x0340 (size: 0x18)
    FMargin ButtonTextPadding;                                                        // 0x0358 (size: 0x10)
    FWBP_EGUI_CommonAlertBanner_CActionRequested ActionRequested;                     // 0x0368 (size: 0x10)
    void ActionRequested(int32 ButtonIndex);
    class UWBP_EGUI_CommonButton_C* ButtonToExecuteAfterDelay;                        // 0x0378 (size: 0x8)
    FText ActionDescription;                                                          // 0x0380 (size: 0x10)
    TArray<FText> OptionsButtons;                                                     // 0x0390 (size: 0x10)
    TEnumAsByte<ESlateSizeRule::Type> ButtonsSizeRule;                                // 0x03A0 (size: 0x1)
    int32 DelayBeforeAutomaticAction;                                                 // 0x03A4 (size: 0x4)
    int32 ActionToExecuteAfterDelay;                                                  // 0x03A8 (size: 0x4)
    bool DelayCompleted?;                                                             // 0x03AC (size: 0x1)
    bool AllowBackInputToTriggerAction?;                                              // 0x03AD (size: 0x1)
    int32 ActionToExecuteOnBackInputFired;                                            // 0x03B0 (size: 0x4)
    class AHUD* HUD;                                                                  // 0x03B8 (size: 0x8)

    void SetupWidget(FS_AlertBannerSetupInfos AlertBannerSetupInfos, class UWidget*& ButtonToFocus);
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void CreateNewButton(FText ButtonTitle, int32 CurrentIndex);
    void ButtonClicked(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void InitDelayBeforeAutomaticAction();
    void AnyKeyPressed(FKey Key);
    void NextCountdown();
    void ExecuteUbergraph_WBP_EGUI_CommonAlertBanner(int32 EntryPoint);
    void ActionRequested__DelegateSignature(int32 ButtonIndex);
}; // Size: 0x3C0

#endif
