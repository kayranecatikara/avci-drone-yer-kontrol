#ifndef UE4SS_SDK_WBP_EOM_SettingProgressBar_HPP
#define UE4SS_SDK_WBP_EOM_SettingProgressBar_HPP

class UWBP_EOM_SettingProgressBar_C : public UWBP_EOM_SettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03F8 (size: 0x8)
    class UProgressBar* ProgressBar;                                                  // 0x0400 (size: 0x8)
    class UBorder* ProgressBarBorder;                                                 // 0x0408 (size: 0x8)
    class USlider* Slider;                                                            // 0x0410 (size: 0x8)
    class USpinBox* ValueInput;                                                       // 0x0418 (size: 0x8)
    FWBP_EOM_SettingProgressBar_CSettingUpdated SettingUpdated;                       // 0x0420 (size: 0x10)
    void SettingUpdated(double NewValue);
    double MinAllowedValue;                                                           // 0x0430 (size: 0x8)
    double MaxAllowedValue;                                                           // 0x0438 (size: 0x8)
    double DefaultValue;                                                              // 0x0440 (size: 0x8)
    double OffsetValue;                                                               // 0x0448 (size: 0x8)
    int32 FractionalDigits;                                                           // 0x0450 (size: 0x4)
    double CurrentValue;                                                              // 0x0458 (size: 0x8)
    TMap<double, FS_OptionsAdditionalDescription> SettingAdditionalDescription;       // 0x0460 (size: 0x50)
    double PreviousInputTime;                                                         // 0x04B0 (size: 0x8)
    double InputInterval;                                                             // 0x04B8 (size: 0x8)
    double TicksHeld;                                                                 // 0x04C0 (size: 0x8)
    bool WidgetConstructed?;                                                          // 0x04C8 (size: 0x1)

    void CallUpdateAndSaveSetting();
    void GetAdditionalDescription(FText& Text, TSoftObjectPtr<UTexture2D>& ImageToDisplay);
    void GetDefaultValueAsText(FText& DefaultValue);
    void ResetToDefault();
    void UpdateGlobalStyling();
    void InitSliderValues(double& DefaultValueClamped);
    void InitTextInputValues();
    void InitValue(bool UseCustomSettingSavedValue?, double Value);
    void UpdateCurrentValue(double CurrentValue, bool CallUpdate?);
    void BndEvt__W_SettingProgress_Slider_K2Node_ComponentBoundEvent_2_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_EOM_SettingProgress_ValueInput_K2Node_ComponentBoundEvent_1_OnSpinBoxValueCommittedEvent__DelegateSignature(float InValue, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_7_OnControllerCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_8_OnMouseCaptureEndEvent__DelegateSignature();
    void SettingUpdateValue(bool NextValue?);
    void Construct();
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EOM_SettingProgressBar(int32 EntryPoint);
    void SettingUpdated__DelegateSignature(double NewValue);
}; // Size: 0x4C9

#endif
