#ifndef UE4SS_SDK_WBP_ESGU_SaveFileActionBanner_HPP
#define UE4SS_SDK_WBP_ESGU_SaveFileActionBanner_HPP

class UWBP_ESGU_SaveFileActionBanner_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* ActionDescriptionText;                              // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* ActionTitleText;                                    // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* CancelButton;                                     // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ContinueButton;                                   // 0x02F0 (size: 0x8)
    class UBorder* Divider;                                                           // 0x02F8 (size: 0x8)
    class UWBP_ESGU_SaveFileCard_C* SaveFileCard;                                     // 0x0300 (size: 0x8)
    FText ActionTitle;                                                                // 0x0308 (size: 0x10)
    FText ActionDescription;                                                          // 0x0318 (size: 0x10)
    FS_SaveGameMetadatas SaveFileMetadatas;                                           // 0x0328 (size: 0x48)
    class UUserWidget* UnderlyingWidget;                                              // 0x0370 (size: 0x8)
    FS_CommonTextInfo TitleTextStyling;                                               // 0x0378 (size: 0x18)
    FS_CommonTextInfo DescriptionTextStyling;                                         // 0x0390 (size: 0x18)
    FWBP_ESGU_SaveFileActionBanner_CActionRequested ActionRequested;                  // 0x03A8 (size: 0x10)
    void ActionRequested(int32 ButtonIndex);
    class AHUD* HUD;                                                                  // 0x03B8 (size: 0x8)

    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void PreConstruct(bool IsDesignTime);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void AnyKeyPressed(FKey Key);
    void BndEvt__WBP_ESGU_SaveFileActionBanner_ContinueButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_ESGU_SaveFileActionBanner_CancelButton_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void Construct();
    void ResetSaveActionBanner(int32 ButtonIndex);
    void ExecuteUbergraph_WBP_ESGU_SaveFileActionBanner(int32 EntryPoint);
    void ActionRequested__DelegateSignature(int32 ButtonIndex);
}; // Size: 0x3C0

#endif
