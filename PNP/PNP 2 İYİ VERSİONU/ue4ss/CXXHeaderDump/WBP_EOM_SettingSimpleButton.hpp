#ifndef UE4SS_SDK_WBP_EOM_SettingSimpleButton_HPP
#define UE4SS_SDK_WBP_EOM_SettingSimpleButton_HPP

class UWBP_EOM_SettingSimpleButton_C : public UWBP_EOM_SettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ActionButton;                                     // 0x0400 (size: 0x8)
    FWBP_EOM_SettingSimpleButton_CSettingUpdated SettingUpdated;                      // 0x0408 (size: 0x10)
    void SettingUpdated();
    FText ButtonActionText;                                                           // 0x0418 (size: 0x10)
    FS_OptionsAdditionalDescription AdditionalDescription;                            // 0x0428 (size: 0x38)

    FEventReply OnFocusReceived(FGeometry MyGeometry, FFocusEvent InFocusEvent);
    void UpdateButtonFocus();
    void GetAdditionalDescription(FText& Text, TSoftObjectPtr<UTexture2D>& ImageToDisplay);
    void BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EOM_SettingSimpleButton(int32 EntryPoint);
    void SettingUpdated__DelegateSignature();
}; // Size: 0x460

#endif
