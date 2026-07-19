#ifndef UE4SS_SDK_WBP_EasyInputPromptDisplayer_HPP
#define UE4SS_SDK_WBP_EasyInputPromptDisplayer_HPP

class UWBP_EasyInputPromptDisplayer_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* MashInteractionAnimation;                                 // 0x02D8 (size: 0x8)
    class UWidgetAnimation* ResetProgressAnimation;                                   // 0x02E0 (size: 0x8)
    class UWidgetAnimation* HoldAnimation;                                            // 0x02E8 (size: 0x8)
    class UGridPanel* GridPanel;                                                      // 0x02F0 (size: 0x8)
    class UProgressBar* InputProgressIndicator;                                       // 0x02F8 (size: 0x8)
    class UImage* Key;                                                                // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonText_C* KeyText;                                            // 0x0308 (size: 0x8)
    class UImage* MashInteractionIndicator;                                           // 0x0310 (size: 0x8)
    class URetainerBox* RetainerBox;                                                  // 0x0318 (size: 0x8)
    class UScaleBox* ScaleBox;                                                        // 0x0320 (size: 0x8)
    bool UseInputAction?;                                                             // 0x0328 (size: 0x1)
    FS_InputActionDef InputActionInfos;                                               // 0x0330 (size: 0x18)
    FKey GamepadKey;                                                                  // 0x0348 (size: 0x18)
    FKey MouseKeyboardKey;                                                            // 0x0360 (size: 0x18)
    TEnumAsByte<E_InputPromptDisplayConditions::Type> DisplayConditions;              // 0x0378 (size: 0x1)
    bool HideKeyForOtherDevices?;                                                     // 0x0379 (size: 0x1)
    double KeyImageSize;                                                              // 0x0380 (size: 0x8)
    FText TextToDisplay;                                                              // 0x0388 (size: 0x10)
    TEnumAsByte<EHorizontalAlignment> TextPosition;                                   // 0x0398 (size: 0x1)
    FMargin TextPadding;                                                              // 0x039C (size: 0x10)
    FS_CommonTextInfo TextStyling;                                                    // 0x03B0 (size: 0x18)
    bool IsUsingGamepad?;                                                             // 0x03C8 (size: 0x1)
    bool HideTextAsWell?;                                                             // 0x03C9 (size: 0x1)
    TEnumAsByte<E_InputPromptType::Type> InputPromptType;                             // 0x03CA (size: 0x1)
    bool UseStylingLocalOverride?;                                                    // 0x03CB (size: 0x1)
    FSlateColor TextColor;                                                            // 0x03CC (size: 0x14)
    FLinearColor IconColor;                                                           // 0x03E0 (size: 0x10)
    class UDataTable* CurrentGamepadKeys;                                             // 0x03F0 (size: 0x8)
    double RequiredMashPresses;                                                       // 0x03F8 (size: 0x8)
    class UMaterialInterface* OverlayMaterial;                                        // 0x0400 (size: 0x8)
    FName OverlayMaterialTextureParameterName;                                        // 0x0408 (size: 0x8)

    void SetText(FText NewText);
    void SelectNewInputType(TEnumAsByte<E_InputPromptType::Type> InputType);
    void GetCurrentGamepadBrand();
    void UpdateInputIcon();
    void UpdateStyling();
    void InputsUpdated();
    void Construct();
    void HoldInputStarted(double HoldDuration);
    void HoldInputCompleted(bool Fail?);
    void ProgressMashInput();
    void MashInputCompleted(bool Fail?);
    void MashInputStarted(int32 RequiredPresses);
    void PreConstruct(bool IsDesignTime);
    void InputMethodChanged(const FPlatformUserId UserId, const FInputDeviceId DeviceID);
    void ExecuteUbergraph_WBP_EasyInputPromptDisplayer(int32 EntryPoint);
}; // Size: 0x410

#endif
