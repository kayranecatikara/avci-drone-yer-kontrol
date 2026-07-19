#ifndef UE4SS_SDK_WBP_EasyPhotoMode_HPP
#define UE4SS_SDK_WBP_EasyPhotoMode_HPP

class UWBP_EasyPhotoMode_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ApertureSetting;                             // 0x02D8 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* BrightnessSetting;                           // 0x02E0 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* CameraRollSetting;                           // 0x02E8 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ChromaticAberrationIntensity;                // 0x02F0 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ChromaticAberrationStartOffset;              // 0x02F8 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ColorTempSetting;                            // 0x0300 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ColorTintSetting;                            // 0x0308 (size: 0x8)
    class UWBP_EPM_SettingToggle_C* ConstrainAspectRatioSetting;                      // 0x0310 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ContrastSetting;                             // 0x0318 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* EditionOptionsHeader;                             // 0x0320 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* EditionOptionsHeaderNextBtn;                      // 0x0328 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* EditionOptionsHeaderPreviousBtn;                  // 0x0330 (size: 0x8)
    class UWidgetSwitcher* EditionOptionsSwitcher;                                    // 0x0338 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* FocalLengthSetting;                          // 0x0340 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* FocusDistanceSetting;                        // 0x0348 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* GrainSetting;                                // 0x0350 (size: 0x8)
    class UWidgetSwitcher* ModeSwitcher;                                              // 0x0358 (size: 0x8)
    class UWBP_EGUI_OptionDescription_C* OptionDescription;                           // 0x0360 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* ResolutionMultiplierSetting;                 // 0x0368 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* SaturationSetting;                           // 0x0370 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* SensorHeightSetting;                         // 0x0378 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* SensorWidthSetting;                          // 0x0380 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* SharpnessSetting;                            // 0x0388 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* TakePhotoBtn;                                     // 0x0390 (size: 0x8)
    class UWBP_EPM_SettingProgressBar_C* VignetteSetting;                             // 0x0398 (size: 0x8)
    class ABP_EPM_PhotoModeController_C* PhotoModeController;                         // 0x03A0 (size: 0x8)
    class UCineCameraComponent* CameraReference;                                      // 0x03A8 (size: 0x8)
    bool EditionModeEnabled?;                                                         // 0x03B0 (size: 0x1)
    FWBP_EasyPhotoMode_CClosePhotoMode ClosePhotoMode;                                // 0x03B8 (size: 0x10)
    void ClosePhotoMode();
    bool IsUIHidden?;                                                                 // 0x03C8 (size: 0x1)
    class UWBP_EPM_PhotoModeSettingsMaster_C* FocusedSetting;                         // 0x03D0 (size: 0x8)
    class UPanelWidget* ActivePanelWidget;                                            // 0x03D8 (size: 0x8)
    FWBP_EasyPhotoMode_CResetSettings ResetSettings;                                  // 0x03E0 (size: 0x10)
    void ResetSettings();
    double ResolutionMultiplier;                                                      // 0x03F0 (size: 0x8)
    float BaseSharpness;                                                              // 0x03F8 (size: 0x4)

    void SetFocusToDistance(double Value);
    void UpdateDescription(FText Text);
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    class UWidget* OverrideNavigation(EUINavigation Navigation);
    void SetFocusToFirstWidget();
    void ToggleUIVisibility(bool Hide?);
    void SwitchMode(bool& SwitchedToEditionMode?);
    void BndEvt__WBP_EasyPhotoMode_EditionOptionsHeader_K2Node_ComponentBoundEvent_0_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void BndEvt__WBP_EasyPhotoMode_TakePhotoBtn_K2Node_ComponentBoundEvent_21_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void NewlyFocusedSetting(class UWBP_EPM_PhotoModeSettingsMaster_C* FocusedSettingRef);
    void AnyKeyPressed(FKey Key);
    void BndEvt__WBP_PhotoMode_EditionOptionsHeaderPreviousBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void InitPhotoModeWidget(class ABP_EPM_PhotoModeController_C* PhotoModeController, class UCineCameraComponent* CameraReference);
    void BndEvt__WBP_PhotoMode_EditionOptionsHeaderNextBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void ClosePhotoModeAction(int32 ButtonIndex);
    void BndEvt__WBP_EasyPhotoMode_SensorHeightSetting_K2Node_ComponentBoundEvent_18_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_SensorWidthSetting_K2Node_ComponentBoundEvent_17_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ResolutionMultiplierSetting_K2Node_ComponentBoundEvent_15_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_FocusDistanceSetting_K2Node_ComponentBoundEvent_13_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_FocalLengthSetting_K2Node_ComponentBoundEvent_12_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ConstrainAspectRatioSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(bool NewValue);
    void BndEvt__WBP_EasyPhotoMode_CameraRollSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ApertureSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_SharpnessSetting_K2Node_ComponentBoundEvent_20_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_VignetteSetting_K2Node_ComponentBoundEvent_19_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_SaturationSetting_K2Node_ComponentBoundEvent_16_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_GrainSetting_K2Node_ComponentBoundEvent_14_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ContrastSetting_K2Node_ComponentBoundEvent_11_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ColorTintSetting_K2Node_ComponentBoundEvent_9_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ColorTempSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ChromaticAberrationStartOffset_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_ChromaticAberrationIntensity_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void BndEvt__WBP_EasyPhotoMode_BrightnessSetting_K2Node_ComponentBoundEvent_1_SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
    void ExecuteUbergraph_WBP_EasyPhotoMode(int32 EntryPoint);
    void ResetSettings__DelegateSignature();
    void ClosePhotoMode__DelegateSignature();
}; // Size: 0x3FC

#endif
