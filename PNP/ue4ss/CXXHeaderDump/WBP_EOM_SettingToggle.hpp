#ifndef UE4SS_SDK_WBP_EOM_SettingToggle_HPP
#define UE4SS_SDK_WBP_EOM_SettingToggle_HPP

class UWBP_EOM_SettingToggle_C : public UWBP_EOM_SettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* OffBtn;                                           // 0x0400 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* OnBtn;                                            // 0x0408 (size: 0x8)
    bool DefaultValue;                                                                // 0x0410 (size: 0x1)
    bool CurrentValue;                                                                // 0x0411 (size: 0x1)
    FWBP_EOM_SettingToggle_CSettingUpdated SettingUpdated;                            // 0x0418 (size: 0x10)
    void SettingUpdated(bool NewValue);
    TArray<FS_OptionsAdditionalDescription> OptionsAdditionalDescription;             // 0x0428 (size: 0x10)

    void CallUpdateAndSaveSetting();
    void GetAdditionalDescription(FText& Text, TSoftObjectPtr<UTexture2D>& ImageToDisplay);
    void GetDefaultValueAsText(FText& DefaultValue);
    void SetCurrentValueAsInt(int32 IntValue);
    void GetCurrentValueAsInt(int32& IntValue);
    void ResetToDefault();
    void InitValue(bool UseCustomSettingSavedValue?, bool Value);
    void UpdateCurrentValue(bool CurrentValue, bool CallUpdate?);
    void SettingUpdateValue(bool NextValue?);
    void BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EOM_SettingToggle_OnBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EOM_SettingToggle(int32 EntryPoint);
    void SettingUpdated__DelegateSignature(bool NewValue);
}; // Size: 0x438

#endif
