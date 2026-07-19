#ifndef UE4SS_SDK_WBP_EOM_SettingKeybinding_HPP
#define UE4SS_SDK_WBP_EOM_SettingKeybinding_HPP

class UWBP_EOM_SettingKeybinding_C : public UWBP_EOM_SettingsMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03F8 (size: 0x8)
    class UInputKeySelector* GamepadKey;                                              // 0x0400 (size: 0x8)
    class UWBP_EasyInputPromptDisplayer_C* GamepadKeyDisplayer;                       // 0x0408 (size: 0x8)
    class UOverlay* GamepadKeyOverlay;                                                // 0x0410 (size: 0x8)
    class UInputKeySelector* KeyboardKey;                                             // 0x0418 (size: 0x8)
    class UWBP_EasyInputPromptDisplayer_C* KeyboardKeyDisplayer;                      // 0x0420 (size: 0x8)
    class UOverlay* KeyboardKeyOverlay;                                               // 0x0428 (size: 0x8)
    FSlateBrush KeySelectorNormalStyle;                                               // 0x0430 (size: 0xB0)
    FSlateBrush KeySelectorActiveStyle;                                               // 0x04E0 (size: 0xB0)
    bool SelectionUpdated;                                                            // 0x0590 (size: 0x1)
    FS_KeyMappingInfos KeyboardMapping;                                               // 0x0598 (size: 0x48)
    FS_KeyMappingInfos GamepadMapping;                                                // 0x05E0 (size: 0x48)
    class UInputMappingContext* MappingContext;                                       // 0x0628 (size: 0x8)
    class UEnhancedInputUserSettings* UserSettings;                                   // 0x0630 (size: 0x8)

    void UpdateKeySelectorFocus(const FPlatformUserId UserId, const FInputDeviceId DeviceID);
    FEventReply OnFocusReceived(FGeometry MyGeometry, FFocusEvent InFocusEvent);
    void RefreshKeyMappingsValues(FS_KeyMappingInfos NewKeyMapping);
    void SetAdditionalDescription();
    void GetDefaultValueAsText(FText& DefaultValue);
    void UpdateInputPromptVisibility(class UInputKeySelector* KeySelectorRef, class UWidget* KeyDisplayerRef);
    void TryToRemapKeybindWithNewKey(FKey NewKey, const FS_KeyMappingInfos& KeyMapping);
    void Remap Key(FS_KeyMappingInfos NewKeyMapping);
    void ResetToDefault();
    void UpdateKeySelectorStyle();
    void InitValue();
    void UpdateKeymapDisplayersInfos();
    void BndEvt__W_SettingKeybinding_KeyboardKey_K2Node_ComponentBoundEvent_0_OnKeySelected__DelegateSignature(FInputChord SelectedKey);
    void BndEvt__W_SettingKeybinding_GamepadKey_K2Node_ComponentBoundEvent_1_OnKeySelected__DelegateSignature(FInputChord SelectedKey);
    void OnMouseEnter(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void Construct();
    void BndEvt__WBP_EOM_SettingKeybind_GamepadKey_K2Node_ComponentBoundEvent_4_OnIsSelectingKeyChanged__DelegateSignature();
    void PreConstruct(bool IsDesignTime);
    void MouseButtonDownEvent();
    void OnRemovedFromFocusPath(FFocusEvent InFocusEvent);
    void OnMouseLeave(const FPointerEvent& MouseEvent);
    void BndEvt__WBP_EOM_SettingKeybind_KeyboardKey_K2Node_ComponentBoundEvent_3_OnIsSelectingKeyChanged__DelegateSignature();
    void ExecuteUbergraph_WBP_EOM_SettingKeybinding(int32 EntryPoint);
}; // Size: 0x638

#endif
