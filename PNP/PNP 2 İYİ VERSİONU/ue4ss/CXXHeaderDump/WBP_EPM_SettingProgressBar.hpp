#ifndef UE4SS_SDK_WBP_EPM_SettingProgressBar_HPP
#define UE4SS_SDK_WBP_EPM_SettingProgressBar_HPP

class UWBP_EPM_SettingProgressBar_C : public UWBP_EPM_PhotoModeSettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0368 (size: 0x8)
    class UProgressBar* ProgressBar;                                                  // 0x0370 (size: 0x8)
    class UBorder* ProgressBarBorder;                                                 // 0x0378 (size: 0x8)
    class USlider* Slider;                                                            // 0x0380 (size: 0x8)
    class USpinBox* ValueInput;                                                       // 0x0388 (size: 0x8)
    FWBP_EPM_SettingProgressBar_CSettingUpdated SettingUpdated;                       // 0x0390 (size: 0x10)
    void SettingUpdated(double NewValue, bool IsDefaultValue?);
    double MinAllowedValue;                                                           // 0x03A0 (size: 0x8)
    double MaxAllowedValue;                                                           // 0x03A8 (size: 0x8)
    double DefaultValue;                                                              // 0x03B0 (size: 0x8)
    double OffsetValue;                                                               // 0x03B8 (size: 0x8)
    int32 FractionalDigits;                                                           // 0x03C0 (size: 0x4)
    double CurrentValue;                                                              // 0x03C8 (size: 0x8)
    bool WidgetConstructed?;                                                          // 0x03D0 (size: 0x1)
    double MaxHoldMultiplier;                                                         // 0x03D8 (size: 0x8)
    bool UpdateOnValueChanged?;                                                       // 0x03E0 (size: 0x1)
    double InputInterval;                                                             // 0x03E8 (size: 0x8)
    double PreviousInputTime;                                                         // 0x03F0 (size: 0x8)
    double TicksHeld;                                                                 // 0x03F8 (size: 0x8)

    void ResetToDefault();
    void UpdateGlobalStyling();
    void InitSliderValues(double& DefaultValueClamped);
    void InitTextInputValues();
    void InitValue(double Value);
    void UpdateCurrentValue(double CurrentValue, bool CallUpdate?);
    void BndEvt__W_SettingProgress_Slider_K2Node_ComponentBoundEvent_2_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_EOM_SettingProgress_ValueInput_K2Node_ComponentBoundEvent_1_OnSpinBoxValueCommittedEvent__DelegateSignature(float InValue, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void SettingUpdateValue(bool NextValue?);
    void BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_7_OnControllerCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_8_OnMouseCaptureEndEvent__DelegateSignature();
    void Construct();
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EPM_SettingProgressBar(int32 EntryPoint);
    void SettingUpdated__DelegateSignature(double NewValue, bool IsDefaultValue?);
}; // Size: 0x400

#endif
