#ifndef UE4SS_SDK_WBP_MainMenu_HPP
#define UE4SS_SDK_WBP_MainMenu_HPP

class UWBP_MainMenu_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBackgroundBlur* BackgroundBlur_Empty;                                      // 0x02D8 (size: 0x8)
    class UBackgroundBlur* BackgroundBlur_Full;                                       // 0x02E0 (size: 0x8)
    class UBackgroundBlur* BackgroundBlur_Half;                                       // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_CONTROLS;                                     // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_FLY;                                          // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_Maps;                                         // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_MENU;                                         // 0x0308 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_SETTINGS;                                     // 0x0310 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_UAV;                                          // 0x0318 (size: 0x8)
    class UVerticalBox* ButtonsContainer;                                             // 0x0320 (size: 0x8)
    class UImage* Image_Empty;                                                        // 0x0328 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* QuitBtn;                                          // 0x0330 (size: 0x8)
    class UWBP_ControlMenu_C* WBP_ControlMenu;                                        // 0x0338 (size: 0x8)
    class UWBP_LevelSelection_C* WBP_LevelSelection;                                  // 0x0340 (size: 0x8)
    class UWBP_ScoreboardBase_C* WBP_ScoreboardBase;                                  // 0x0348 (size: 0x8)
    class UWBP_SelectedOptions_C* WBP_SelectedOptions;                                // 0x0350 (size: 0x8)
    class UWBP_SettingsMenu_C* WBP_SettingsMenu;                                      // 0x0358 (size: 0x8)
    class UWBP_UAVSelection_C* WBP_UAVSelection;                                      // 0x0360 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher_Blur;                                       // 0x0368 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher_Panels;                                     // 0x0370 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0378 (size: 0x8)
    class ABPP_UAV_C* BPP Main Drone;                                                 // 0x0380 (size: 0x8)
    class UBP_SaveGame_Player_C* BP Save Game Player;                                 // 0x0388 (size: 0x8)
    class USaveGame* SaveRef;                                                         // 0x0390 (size: 0x8)
    FText PlayerNickname;                                                             // 0x0398 (size: 0x10)
    class ABPP_MenuCam_C* BPP Menu Cam;                                               // 0x03A8 (size: 0x8)
    class ABPP_Tablet_C* BPP Tablet;                                                  // 0x03B0 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x03B8 (size: 0x8)
    class AGM_MainMenu_C* GM Main Menu;                                               // 0x03C0 (size: 0x8)
    class ABPP_CustomizableUAV_C* BPPCustomizableUAV;                                 // 0x03C8 (size: 0x8)

    void Construct();
    void BndEvt__WBP_MainMenu_Btn_FLY_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_Btn_SETTINGS_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_Btn_CONTROLS_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_QuitBtn_K2Node_ComponentBoundEvent_8_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_Btn_MENU_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_Btn_FLY_1_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_WBP_LevelSelection_K2Node_ComponentBoundEvent_6_OnClickAnyButton__DelegateSignature();
    void BndEvt__WBP_MainMenu_WBP_UAVSelection_K2Node_ComponentBoundEvent_7_OnClickAnyButton__DelegateSignature();
    void BndEvt__WBP_MainMenu_Btn_FLY_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_MainMenu_WBP_SelectedOptions_K2Node_ComponentBoundEvent_12_OnClickedScoreboard__DelegateSignature();
    void LoadScoreboardData();
    void ExecuteUbergraph_WBP_MainMenu(int32 EntryPoint);
}; // Size: 0x3D0

#endif
