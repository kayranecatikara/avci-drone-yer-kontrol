#ifndef UE4SS_SDK_WBP_EPM_Gallery_HPP
#define UE4SS_SDK_WBP_EPM_Gallery_HPP

class UWBP_EPM_Gallery_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* BackBtn;                                          // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* BackFromFullscreenBtn;                            // 0x02E0 (size: 0x8)
    class UWidgetSwitcher* FullscreenDisplayer;                                       // 0x02E8 (size: 0x8)
    class UImage* FullscreenImage;                                                    // 0x02F0 (size: 0x8)
    class UWidgetSwitcher* GalleryThumbnails;                                         // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* LocateFolderButton;                               // 0x0300 (size: 0x8)
    class UOverlay* NextPageOverlay;                                                  // 0x0308 (size: 0x8)
    class UWBP_EGUI_CommonSelectorButton_C* NextPageSelectorBtn;                      // 0x0310 (size: 0x8)
    class UWBP_EGUI_CommonText_C* PageIndicatorText;                                  // 0x0318 (size: 0x8)
    class UOverlay* PrevPageOverlay;                                                  // 0x0320 (size: 0x8)
    class UWBP_EGUI_CommonSelectorButton_C* PrevPageSelectorBtn;                      // 0x0328 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ShowFullscreenBtn;                                // 0x0330 (size: 0x8)
    TArray<FString> ScreenshotsList;                                                  // 0x0338 (size: 0x10)
    int32 TotalLoadedPhotos;                                                          // 0x0348 (size: 0x4)
    FString ScreenshotsDirectory;                                                     // 0x0350 (size: 0x10)
    FMargin GridPanelInnerPaddings;                                                   // 0x0360 (size: 0x10)
    bool FullScreenImageDisplayed?;                                                   // 0x0370 (size: 0x1)
    int32 Columns;                                                                    // 0x0374 (size: 0x4)
    int32 Rows;                                                                       // 0x0378 (size: 0x4)
    class ABP_EPM_PhotoModeController_C* PhotoModeController;                         // 0x0380 (size: 0x8)
    class UWBP_EPM_ThumbnailDisplayer_C* FocusedThumbnail;                            // 0x0388 (size: 0x8)
    FWBP_EPM_Gallery_CGalleryUIClosed GalleryUIClosed;                                // 0x0390 (size: 0x10)
    void GalleryUIClosed();
    bool FullyLoaded?;                                                                // 0x03A0 (size: 0x1)

    void SetNewPageIndicator(int32 CurrentPage);
    class UWidget* GetFirstThumbnailToFocus();
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void MakeImageBrush(class UTexture2D* ImageTexture, FSlateBrush& SlateBrush);
    void DisplayFullScreenImage(class UTexture2D* ImageRef, FString ScreenshotName);
    void CreateThumbnails(class UUniformGridPanel* GridPanel, TArray<FString>& Array);
    void LoadNewPhotoPage(bool& LoadedNewPage?);
    void InpActEvt_IA_LocatePhotosFolder_K2Node_EnhancedInputActionEvent_0(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void SetupGallery(FString ScreenshotsDirectory, class ABP_EPM_PhotoModeController_C* PhotoModeController);
    void BndEvt__WBP_EPM_Gallery_BackFromFullscreenBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void NewlyFocusedThumbnail(class UWBP_EPM_ThumbnailDisplayer_C* ThumbRef);
    void BndEvt__WBP_EPM_Gallery_LocateFolderButton_K2Node_ComponentBoundEvent_11_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EPM_Gallery_ShowFullscreenBtn_K2Node_ComponentBoundEvent_8_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EPM_Gallery_BackBtn_K2Node_ComponentBoundEvent_7_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void AnyKeyPressed(FKey Key);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void BndEvt__WBP_EPM_Gallery_WBP_CommonSelectorButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature();
    void BndEvt__WBP_EPM_Gallery_PrevPageSelectorBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature();
    void ExecuteUbergraph_WBP_EPM_Gallery(int32 EntryPoint);
    void GalleryUIClosed__DelegateSignature();
}; // Size: 0x3A1

#endif
