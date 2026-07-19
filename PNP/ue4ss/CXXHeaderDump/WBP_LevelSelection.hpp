#ifndef UE4SS_SDK_WBP_LevelSelection_HPP
#define UE4SS_SDK_WBP_LevelSelection_HPP

class UWBP_LevelSelection_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UScrollBox* ScrollBox_Attack;                                               // 0x02D8 (size: 0x8)
    class UScrollBox* ScrollBox_Fiber;                                                // 0x02E0 (size: 0x8)
    class UScrollBox* ScrollBox_Race;                                                 // 0x02E8 (size: 0x8)
    class UScrollBox* ScrollBox_Training;                                             // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* WBP_EGUI_CommonHeader;                            // 0x02F8 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_AcroArea;                                      // 0x0300 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Beach;                                         // 0x0308 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Jungle;                                        // 0x0310 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_KartingCircuits;                               // 0x0318 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_MilitaryAirport;                               // 0x0320 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_NetRural;                                      // 0x0328 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Peak;                                          // 0x0330 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Pole;                                          // 0x0338 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_RuinedCity;                                    // 0x0340 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Rural;                                         // 0x0348 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Teknofest;                                     // 0x0350 (size: 0x8)
    class UWBP_MenuCard_C* WBP_MapCard_Trench;                                        // 0x0358 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher;                                            // 0x0360 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0368 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0370 (size: 0x8)
    FWBP_LevelSelection_COnClickAnyButton OnClickAnyButton;                           // 0x0378 (size: 0x10)
    void OnClickAnyButton();
    FWBP_LevelSelection_COnClickAnyScoreButton OnClickAnyScoreButton;                 // 0x0388 (size: 0x10)
    void OnClickAnyScoreButton();
    TArray<class UWBP_MenuCard_C*> ChildCardElements;                                 // 0x0398 (size: 0x10)

    void ShowGlitchEffect();
    void Construct();
    void BndEvt__WBP_LevelSelection_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_3_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void BndEvt__WBP_LevelSelection_WBP_MapCard_K2Node_ComponentBoundEvent_0_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_1_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_2_K2Node_ComponentBoundEvent_2_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_3_K2Node_ComponentBoundEvent_4_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_4_K2Node_ComponentBoundEvent_5_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_5_K2Node_ComponentBoundEvent_6_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_6_K2Node_ComponentBoundEvent_7_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_7_K2Node_ComponentBoundEvent_8_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_8_K2Node_ComponentBoundEvent_9_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_9_K2Node_ComponentBoundEvent_10_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_10_K2Node_ComponentBoundEvent_11_OnClicked__DelegateSignature();
    void BndEvt__WBP_LevelSelection_WBP_MapCard_11_K2Node_ComponentBoundEvent_12_OnClicked__DelegateSignature();
    void SetSelectedButton();
    void CreateMenuCardList();
    void ExecuteUbergraph_WBP_LevelSelection(int32 EntryPoint);
    void OnClickAnyScoreButton__DelegateSignature();
    void OnClickAnyButton__DelegateSignature();
}; // Size: 0x3A8

#endif
