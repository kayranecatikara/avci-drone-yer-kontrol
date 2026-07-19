#ifndef UE4SS_SDK_WBP_MenuCard_HPP
#define UE4SS_SDK_WBP_MenuCard_HPP

class UWBP_MenuCard_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UButton* Button;                                                            // 0x02D8 (size: 0x8)
    class UButton* Button_Selected;                                                   // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SaveFileDisplayName;                                // 0x02E8 (size: 0x8)
    class UImage* SaveFileThumbnail;                                                  // 0x02F0 (size: 0x8)
    FWBP_MenuCard_COnClicked OnClicked;                                               // 0x02F8 (size: 0x10)
    void OnClicked();
    FWBP_MenuCard_COnHover OnHover;                                                   // 0x0308 (size: 0x10)
    void OnHover();
    class UTexture2D* Image;                                                          // 0x0318 (size: 0x8)
    FText Text;                                                                       // 0x0320 (size: 0x10)
    FWBP_MenuCard_COnUnhover OnUnhover;                                               // 0x0330 (size: 0x10)
    void OnUnhover();
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0340 (size: 0x8)
    bool canSwitchButton;                                                             // 0x0348 (size: 0x1)

    void BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature();
    void BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature();
    void Construct();
    void BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature();
    void SetSelectButton(bool IsSelected);
    void ExecuteUbergraph_WBP_MenuCard(int32 EntryPoint);
    void OnUnhover__DelegateSignature();
    void OnClicked__DelegateSignature();
    void OnHover__DelegateSignature();
}; // Size: 0x349

#endif
