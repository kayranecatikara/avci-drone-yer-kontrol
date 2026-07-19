#ifndef UE4SS_SDK_WBP_EasyMainMenu_HPP
#define UE4SS_SDK_WBP_EasyMainMenu_HPP

class UWBP_EasyMainMenu_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UVerticalBox* ButtonsContainer;                                             // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ContinueBtn;                                      // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* CreditsBtn;                                       // 0x02E8 (size: 0x8)
    class UCanvasPanel* FullscreenLogoPanel;                                          // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* LoadSavegameButton;                               // 0x02F8 (size: 0x8)
    class UImage* Logo;                                                               // 0x0300 (size: 0x8)
    class UImage* Logo_1;                                                             // 0x0308 (size: 0x8)
    class UCanvasPanel* MainMenuPanel;                                                // 0x0310 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* NewGameButton;                                    // 0x0318 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* OptionsBtn;                                       // 0x0320 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* QuitBtn;                                          // 0x0328 (size: 0x8)
    class APlayerController* PlayerControllerRef;                                     // 0x0330 (size: 0x8)
    class AHUD* HUD;                                                                  // 0x0338 (size: 0x8)
    FWBP_EasyMainMenu_CMainMenuClosed MainMenuClosed;                                 // 0x0340 (size: 0x10)
    void MainMenuClosed();
    class ABP_EasyMainMenuController_C* MainMenuController;                           // 0x0350 (size: 0x8)
    bool MainMenuDisplayed?;                                                          // 0x0358 (size: 0x1)
    class UBP_EasySaveGameObject_C* NewestSaveSlot;                                   // 0x0360 (size: 0x8)
    class UWBP_EGUI_CommonTooltip_C* QuickSaveTooltip;                                // 0x0368 (size: 0x8)
    class UWidget* DefaultButtonToFocus;                                              // 0x0370 (size: 0x8)
    int32 FocusedButtonIndex;                                                         // 0x0378 (size: 0x4)
    FWBP_EasyMainMenu_CAnyButtonFocused AnyButtonFocused;                             // 0x0380 (size: 0x10)
    void AnyButtonFocused(int32 ButtonIndex);
    TArray<int32> ExclusiveButtonIndexes;                                             // 0x0390 (size: 0x10)

    void ToggleSaveButtonsIfNotAllowed();
    void GetValidButtonToRefocus(class UWidget*& ButtonToRefocus);
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void PreConstruct(bool IsDesignTime);
    void BndEvt__WBP_EasyMainMenu_NewGameButton_K2Node_ComponentBoundEvent_6_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EasyMainMenu_LoadSavegameButton_K2Node_ComponentBoundEvent_7_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void LoadSaveAction(int32 ButtonIndex);
    void BndEvt__WBP_EasyMainMenu_CreditsBtn_K2Node_ComponentBoundEvent_6_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void AnyKeyPressed(FKey Key);
    void ResetAndCloseMainMenu();
    void DisplayMainMenuPanel();
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void QuitGameAction(int32 ButtonIndex);
    void Construct();
    void BndEvt__WBP_EOM_DemoPauseMenu_QuitBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void NewButtonFocused(int32 SelfIndex);
    void BndEvt__WBP_EOM_DemoPauseMenu_OptionsBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EOM_DemoPauseMenu_ContinueBtn_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void CreditsCompleted_Event();
    void SaveManagerClosed();
    void OptionsMenuClosed();
    void ExecuteUbergraph_WBP_EasyMainMenu(int32 EntryPoint);
    void AnyButtonFocused__DelegateSignature(int32 ButtonIndex);
    void MainMenuClosed__DelegateSignature();
}; // Size: 0x3A0

#endif
