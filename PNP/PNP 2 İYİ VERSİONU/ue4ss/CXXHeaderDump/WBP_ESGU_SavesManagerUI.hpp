#ifndef UE4SS_SDK_WBP_ESGU_SavesManagerUI_HPP
#define UE4SS_SDK_WBP_ESGU_SavesManagerUI_HPP

class UWBP_ESGU_SavesManagerUI_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonBackgroundImage_C* Background;                              // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* DeleteSlotBtn;                                    // 0x02E0 (size: 0x8)
    class UBorder* Divider;                                                           // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* NavBackBtn;                                       // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* NewSaveButton;                                    // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonBackground_C* SaveFileDetailsBackground;                    // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SaveFileDisplayName;                                // 0x0308 (size: 0x8)
    class UImage* SaveFileThumbnail;                                                  // 0x0310 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* SaveOrLoadBtn;                                    // 0x0318 (size: 0x8)
    class UVerticalBox* SavesContainer;                                               // 0x0320 (size: 0x8)
    TArray<class UWBP_ESGU_SaveFileCard_C*> SaveFilesCards;                           // 0x0328 (size: 0x10)
    class UWBP_ESGU_SaveFileCard_C* FocusedSaveFile;                                  // 0x0338 (size: 0x8)
    class UUserWidget* FocusedWidget;                                                 // 0x0340 (size: 0x8)
    class APlayerController* PlayerControllerRef;                                     // 0x0348 (size: 0x8)
    FWBP_ESGU_SavesManagerUI_CSaveManagerMenuClosed SaveManagerMenuClosed;            // 0x0350 (size: 0x10)
    void SaveManagerMenuClosed();
    class AHUD* HUD;                                                                  // 0x0360 (size: 0x8)
    TEnumAsByte<E_SaveGameOperationType::Type> Operation Type;                        // 0x0368 (size: 0x1)
    class ABP_EasySaveGameOperationsManager_C* OperationsManager;                     // 0x0370 (size: 0x8)
    FS_SaveOperationInfos RequestedSaveGameOperation;                                 // 0x0378 (size: 0x18)

    void SaveGameOperationEnded(FS_SaveOperationInfos Operation);
    void UpdateSlotTitleAndThumbnail(class UTexture2D* Thumbnail, class UWBP_ESGU_SaveFileCard_C* SaveSlotCardRef);
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void SetFocusToFirstWidget();
    void SortSaveFilesByDate(TArray<class UWBP_ESGU_SaveFileCard_C*>& SaveFiles);
    void BndEvt__WBP_SavesManagerUI_CreateSaveBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SavesManagerUI_DeleteSaveBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SavesManagerUI_NavBackBtn_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void DeleteSlotAction(int32 ButtonIndex);
    void OverwriteSlotAction(int32 ButtonIndex);
    void InitWidget(TEnumAsByte<E_SaveGameOperationType::Type> OperationType);
    void BndEvt__WBP_SaveGamesUI_NewSaveButton_K2Node_ComponentBoundEvent_1_ButtonFocused__DelegateSignature(int32 SelfIndex);
    void AnyKeyPressed(FKey Key);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void NewlyFocusedSaveFile(class UWBP_ESGU_SaveFileCard_C* SaveSlotCardRef);
    void RefreshFilesList();
    void BndEvt__WBP_SaveGamesUI_NewSaveButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void PreConstruct(bool IsDesignTime);
    void Construct();
    void LoadSaveAction(int32 ButtonIndex);
    void TriggerSaveOrLoad();
    void ExecuteUbergraph_WBP_ESGU_SavesManagerUI(int32 EntryPoint);
    void SaveManagerMenuClosed__DelegateSignature();
}; // Size: 0x390

#endif
