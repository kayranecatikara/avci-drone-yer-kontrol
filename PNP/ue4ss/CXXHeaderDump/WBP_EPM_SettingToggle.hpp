#ifndef UE4SS_SDK_WBP_EPM_SettingToggle_HPP
#define UE4SS_SDK_WBP_EPM_SettingToggle_HPP

class UWBP_EPM_SettingToggle_C : public UWBP_EPM_PhotoModeSettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0368 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* OffBtn;                                           // 0x0370 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* OnBtn;                                            // 0x0378 (size: 0x8)
    bool DefaultValue;                                                                // 0x0380 (size: 0x1)
    bool CurrentValue;                                                                // 0x0381 (size: 0x1)
    FWBP_EPM_SettingToggle_CSettingUpdated SettingUpdated;                            // 0x0388 (size: 0x10)
    void SettingUpdated(bool NewValue);

    void ResetToDefault();
    void InitValue(bool Value);
    void UpdateCurrentValue(bool CurrentValue, bool CallUpdate?);
    void SettingUpdateValue(bool NextValue?);
    void BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EOM_SettingToggle_OnBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EPM_SettingToggle(int32 EntryPoint);
    void SettingUpdated__DelegateSignature(bool NewValue);
}; // Size: 0x398

#endif
