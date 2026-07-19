#ifndef UE4SS_SDK_WBP_EOM_SettingsMaster_HPP
#define UE4SS_SDK_WBP_EOM_SettingsMaster_HPP

class UWBP_EOM_SettingsMaster_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonBackground_C* Background;                                   // 0x02D8 (size: 0x8)
    class UBorder* DirtyIndicator;                                                    // 0x02E0 (size: 0x8)
    class UNamedSlot* NamedSlot;                                                      // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ResetSetting;                                     // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SettingName;                                        // 0x02F8 (size: 0x8)
    class USizeBox* SizeBox;                                                          // 0x0300 (size: 0x8)
    class UWBP_EasyOptionsMenuMain_C* OptionsMenuRef;                                 // 0x0308 (size: 0x8)
    TArray<FS_SettingActivationConditions> ActivationConditions;                      // 0x0310 (size: 0x10)
    TMap<class UWBP_EOM_SettingsMaster_C*, class bool> ActivationConditionsState;     // 0x0320 (size: 0x50)
    bool SettingEnabled?;                                                             // 0x0370 (size: 0x1)
    FText OptionTitle;                                                                // 0x0378 (size: 0x10)
    bool UseStylingLocalOverride?;                                                    // 0x0388 (size: 0x1)
    FS_CommonTextInfo OptionTitleTextStyling;                                         // 0x0390 (size: 0x18)
    FText OptionDescription;                                                          // 0x03A8 (size: 0x10)
    bool ApplyOnEdit?;                                                                // 0x03B8 (size: 0x1)
    bool ShowResetButton?;                                                            // 0x03B9 (size: 0x1)
    bool SaveCurrentValueToCustomSettings?;                                           // 0x03BA (size: 0x1)
    FString CustomSettingFieldName;                                                   // 0x03C0 (size: 0x10)
    bool Dirty?;                                                                      // 0x03D0 (size: 0x1)
    FS_CommonTextInfo OptionValueTextStyling;                                         // 0x03D8 (size: 0x18)
    float SizeBoxHeight;                                                              // 0x03F0 (size: 0x4)

    void SetSettingEnabled(bool bIsSettingEnabled?);
    FEventReply OnMouseButtonDown(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void CallUpdateAndSaveSetting();
    void SetAdditionalDescription();
    void GetAdditionalDescription(FText& Text, TSoftObjectPtr<UTexture2D>& ImageToDisplay);
    void HandleResetButtonVisibility(bool IsDefaultValue?);
    void GetDefaultValueAsText(FText& DefaultValue);
    void AddActivationCondition(class UWBP_EOM_SettingsMaster_C* ControllerWidget, TArray<int32>& Values to Toggle Setting Activation, bool New Activation State);
    void UpdateSettingActivation(class UWBP_EOM_SettingsMaster_C* ParentCondition, bool NewState);
    void ControlSettingsActivationOnConditions();
    void SetCurrentValueAsInt(int32 IntValue);
    void GetCurrentValueAsInt(int32& IntValue);
    void ApplySetting();
    void SetSettingDirty(bool IsDirty?);
    void ResetToDefault();
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void OnRemovedFromFocusPath(FFocusEvent InFocusEvent);
    void SettingUpdateValue(bool NextValue?);
    void PreConstruct(bool IsDesignTime);
    void BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_1_ButtonFocused__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_4_ButtonUnfocused__DelegateSignature();
    void MouseButtonDownEvent();
    void OnMouseLeave(const FPointerEvent& MouseEvent);
    void OnMouseEnter(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void Construct();
    void ExecuteUbergraph_WBP_EOM_SettingsMaster(int32 EntryPoint);
}; // Size: 0x3F4

#endif
