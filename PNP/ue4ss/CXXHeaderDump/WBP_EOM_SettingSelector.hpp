#ifndef UE4SS_SDK_WBP_EOM_SettingSelector_HPP
#define UE4SS_SDK_WBP_EOM_SettingSelector_HPP

class UWBP_EOM_SettingSelector_C : public UWBP_EOM_SettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03F8 (size: 0x8)
    class UHorizontalBox* ActiveItemIndicator;                                        // 0x0400 (size: 0x8)
    class UWBP_EGUI_CommonSelectorButton_C* SelectNextBtn;                            // 0x0408 (size: 0x8)
    class UWBP_EGUI_CommonSelectorButton_C* SelectPreviousBtn;                        // 0x0410 (size: 0x8)
    class UBorder* SettingBorder;                                                     // 0x0418 (size: 0x8)
    class UWBP_EGUI_CommonText_C* TextValueDisplay;                                   // 0x0420 (size: 0x8)
    TArray<class UWBP_ActiveSelectIndicator_C*> SelectionIndicators;                  // 0x0428 (size: 0x10)
    int32 DefaultValue;                                                               // 0x0438 (size: 0x4)
    TArray<FS_CultureInvariantOptionsValues> OptionsValues;                           // 0x0440 (size: 0x10)
    int32 OptionIntIncrement;                                                         // 0x0450 (size: 0x4)
    int32 CurrentValue;                                                               // 0x0454 (size: 0x4)
    FWBP_EOM_SettingSelector_CSettingUpdated SettingUpdated;                          // 0x0458 (size: 0x10)
    void SettingUpdated(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);

    void CallUpdateAndSaveSetting();
    void GetAdditionalDescription(FText& Text, TSoftObjectPtr<UTexture2D>& ImageToDisplay);
    void GetDefaultValueAsText(FText& DefaultValue);
    void SetCurrentValueAsInt(int32 IntValue);
    void GetCurrentValueAsInt(int32& IntValue);
    void ResetToDefault();
    void InitValue(bool UseCustomSettingSavedValue?, int32 Value, bool RefreshOptions?);
    int32 FindValueFromString(FString StringValue, bool SearchCultureInvariantValue?);
    void GetArrayInfos(int32& Length, int32& LastIndex);
    void RefreshSelectionIndicators();
    void UpdateCurrentValue(int32 CurrentValue, bool CallUpdate?);
    void PreConstruct(bool IsDesignTime);
    void SettingUpdateValue(bool NextValue?);
    void ReInitOptions();
    void BndEvt__WBP_EOM_SettingSelector_WBP_CommonSelectorButton_103_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature();
    void BndEvt__WBP_EOM_SettingSelector_SelectNextBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature();
    void ExecuteUbergraph_WBP_EOM_SettingSelector(int32 EntryPoint);
    void SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
}; // Size: 0x468

#endif
