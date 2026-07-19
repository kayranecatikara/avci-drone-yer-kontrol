#ifndef UE4SS_SDK_WBP_UAVSelection_HPP
#define UE4SS_SDK_WBP_UAVSelection_HPP

class UWBP_UAVSelection_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* Gate;                                                     // 0x02D8 (size: 0x8)
    class UCanvasPanel* CanvasPanel_Main;                                             // 0x02E0 (size: 0x8)
    class UImage* Image_ExtraVideo;                                                   // 0x02E8 (size: 0x8)
    class UImage* Image_Outline;                                                      // 0x02F0 (size: 0x8)
    class UOverlay* Overlay_HoverCardVideo;                                           // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* WBP_EGUI_CommonHeader;                            // 0x0300 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Big;                                           // 0x0308 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Heavy;                                         // 0x0310 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Kargu;                                         // 0x0318 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_LockKit;                                       // 0x0320 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Normal;                                        // 0x0328 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Personal;                                      // 0x0330 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_PushImpact;                                    // 0x0338 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_SD10;                                          // 0x0340 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_SD15;                                          // 0x0348 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_SD15+;                                         // 0x0350 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_SD7;                                           // 0x0358 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_SDMINI;                                        // 0x0360 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Skydagger;                                     // 0x0368 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Small;                                         // 0x0370 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Thermal;                                       // 0x0378 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_TOYCA;                                         // 0x0380 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher;                                            // 0x0388 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0390 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0398 (size: 0x8)
    class ABPP_CustomizableUAV_C* BPP Customizable Drone;                             // 0x03A0 (size: 0x8)
    bool isOnThermal;                                                                 // 0x03A8 (size: 0x1)
    bool isOnLockKit;                                                                 // 0x03A9 (size: 0x1)
    bool isOnPushImpact;                                                              // 0x03AA (size: 0x1)
    bool canFollowMouseGIF;                                                           // 0x03AB (size: 0x1)
    class UMediaPlayer* MediaPlayerThermal;                                           // 0x03B0 (size: 0x8)
    class UMediaPlayer* MediaPlayerLockKit;                                           // 0x03B8 (size: 0x8)
    FWBP_UAVSelection_COnClickAnyButton OnClickAnyButton;                             // 0x03C0 (size: 0x10)
    void OnClickAnyButton();
    class UMediaPlayer* MediaPlayerPushImpactPersonal;                                // 0x03D0 (size: 0x8)
    class UMediaPlayer* MediaPlayerPushImpactHeavy;                                   // 0x03D8 (size: 0x8)

    void Construct();
    void SetLockKitOnOff(bool IsOn);
    void SetThermalOnOff(bool IsOn);
    void Set Drone Type(TEnumAsByte<E_UAV::Type> E UAV);
    void SetPushImpactOnOff(bool IsOn);
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void BndEvt__WBP_UAVSelection_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_24_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void BndEvt__WBP_UAVSelection_WBP_MapCard_11_K2Node_ComponentBoundEvent_0_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_9_K2Node_ComponentBoundEvent_4_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_K2Node_ComponentBoundEvent_26_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_1_K2Node_ComponentBoundEvent_27_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_2_K2Node_ComponentBoundEvent_28_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_3_K2Node_ComponentBoundEvent_29_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_4_K2Node_ComponentBoundEvent_34_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_5_K2Node_ComponentBoundEvent_35_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_38_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_39_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_40_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_44_OnUnhover__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_45_OnHover__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_46_OnHover__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_47_OnUnhover__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_Heavy_K2Node_ComponentBoundEvent_52_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_Personal_K2Node_ComponentBoundEvent_53_OnClicked__DelegateSignature();
    void LoadInformation();
    void CheckPushImpact();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_SD15+_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_SDMINI_K2Node_ComponentBoundEvent_2_OnClicked__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_TOYCA_K2Node_ComponentBoundEvent_3_OnClicked__DelegateSignature();
    void ShowGlitchEffect();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_5_OnHover__DelegateSignature();
    void BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_6_OnUnhover__DelegateSignature();
    void SetSelectedOption(TArray<class UWBP_MenuCard_C*>& MenuCard, uint8 Type);
    void SetSelectedUAV();
    void SetSelectedController();
    void SetSelectedAmmunition();
    void SetSelectedFiber();
    void InitializeSetSelectedExtra();
    void SetAllSelectedOptions();
    void ExecuteUbergraph_WBP_UAVSelection(int32 EntryPoint);
    void OnClickAnyButton__DelegateSignature();
}; // Size: 0x3E0

#endif
