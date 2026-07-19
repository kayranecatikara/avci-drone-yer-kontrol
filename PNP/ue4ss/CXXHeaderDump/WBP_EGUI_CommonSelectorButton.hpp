#ifndef UE4SS_SDK_WBP_EGUI_CommonSelectorButton_HPP
#define UE4SS_SDK_WBP_EGUI_CommonSelectorButton_HPP

class UWBP_EGUI_CommonSelectorButton_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Button;                                           // 0x02D8 (size: 0x8)
    class UImage* SelectorImage;                                                      // 0x02E0 (size: 0x8)
    FVector2D ImageSize;                                                              // 0x02E8 (size: 0x10)
    float SelectorRotationAngle;                                                      // 0x02F8 (size: 0x4)
    FMargin ImagePadding;                                                             // 0x02FC (size: 0x10)
    TEnumAsByte<E_ButtonStyleSelector::Type> ButtonStyle;                             // 0x030C (size: 0x1)
    TEnumAsByte<E_SelectionIndicatorPosition::Type> SelectionIndicatorPosition;       // 0x030D (size: 0x1)
    TEnumAsByte<ESlateBrushRoundingType::Type> PreferedRoundingType;                  // 0x030E (size: 0x1)
    FWBP_EGUI_CommonSelectorButton_CButtonClicked ButtonClicked;                      // 0x0310 (size: 0x10)
    void ButtonClicked();

    void OnLoaded_F753DC434E4BB979AC9A8DA34EADA30F(class UObject* Loaded);
    void BndEvt__WBP_CommonSelectorButton_Button_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EGUI_CommonSelectorButton(int32 EntryPoint);
    void ButtonClicked__DelegateSignature();
}; // Size: 0x320

#endif
