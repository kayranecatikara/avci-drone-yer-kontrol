#ifndef UE4SS_SDK_WBP_EPM_PhotoModeSettingsMaster_HPP
#define UE4SS_SDK_WBP_EPM_PhotoModeSettingsMaster_HPP

class UWBP_EPM_PhotoModeSettingsMaster_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonBackground_C* Background;                                   // 0x02D8 (size: 0x8)
    class UNamedSlot* NamedSlot;                                                      // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ResetSetting;                                     // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SettingName;                                        // 0x02F0 (size: 0x8)
    class USizeBox* SizeBox;                                                          // 0x02F8 (size: 0x8)
    class UWBP_EasyPhotoMode_C* EasyPhotoModeRef;                                     // 0x0300 (size: 0x8)
    FText OptionTitle;                                                                // 0x0308 (size: 0x10)
    bool UseStylingLocalOverride?;                                                    // 0x0318 (size: 0x1)
    FS_CommonTextInfo OptionTitleTextStyling;                                         // 0x0320 (size: 0x18)
    FS_CommonTextInfo OptionValueTextStyling;                                         // 0x0338 (size: 0x18)
    float SizeBoxHeight;                                                              // 0x0350 (size: 0x4)
    FText OptionDescription;                                                          // 0x0358 (size: 0x10)

    FEventReply OnMouseButtonDown(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void ResetToDefault();
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void OnRemovedFromFocusPath(FFocusEvent InFocusEvent);
    void SettingUpdateValue(bool NextValue?);
    void PreConstruct(bool IsDesignTime);
    void BndEvt__WBP_EPM_PhotoModeSettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void OnMouseLeave(const FPointerEvent& MouseEvent);
    void MouseButtonDownEvent();
    void OnMouseEnter(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void Construct();
    void ExecuteUbergraph_WBP_EPM_PhotoModeSettingsMaster(int32 EntryPoint);
}; // Size: 0x368

#endif
