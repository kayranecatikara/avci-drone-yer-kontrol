---@meta

---@class UWBP_EPM_Gallery_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field BackBtn UWBP_EGUI_CommonButton_C
---@field BackFromFullscreenBtn UWBP_EGUI_CommonButton_C
---@field FullscreenDisplayer UWidgetSwitcher
---@field FullscreenImage UImage
---@field GalleryThumbnails UWidgetSwitcher
---@field LocateFolderButton UWBP_EGUI_CommonButton_C
---@field NextPageOverlay UOverlay
---@field NextPageSelectorBtn UWBP_EGUI_CommonSelectorButton_C
---@field PageIndicatorText UWBP_EGUI_CommonText_C
---@field PrevPageOverlay UOverlay
---@field PrevPageSelectorBtn UWBP_EGUI_CommonSelectorButton_C
---@field ShowFullscreenBtn UWBP_EGUI_CommonButton_C
---@field ScreenshotsList TArray<FString>
---@field TotalLoadedPhotos int32
---@field ScreenshotsDirectory FString
---@field GridPanelInnerPaddings FMargin
---@field ['FullScreenImageDisplayed?'] boolean
---@field Columns int32
---@field Rows int32
---@field PhotoModeController ABP_EPM_PhotoModeController_C
---@field FocusedThumbnail UWBP_EPM_ThumbnailDisplayer_C
---@field GalleryUIClosed FWBP_EPM_Gallery_CGalleryUIClosed
---@field ['FullyLoaded?'] boolean
local UWBP_EPM_Gallery_C = {}

---@param CurrentPage int32
function UWBP_EPM_Gallery_C:SetNewPageIndicator(CurrentPage) end
---@return UWidget
function UWBP_EPM_Gallery_C:GetFirstThumbnailToFocus() end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EPM_Gallery_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param ImageTexture UTexture2D
---@param SlateBrush FSlateBrush
function UWBP_EPM_Gallery_C:MakeImageBrush(ImageTexture, SlateBrush) end
---@param ImageRef UTexture2D
---@param ScreenshotName FString
function UWBP_EPM_Gallery_C:DisplayFullScreenImage(ImageRef, ScreenshotName) end
---@param GridPanel UUniformGridPanel
---@param Array TArray<FString>
function UWBP_EPM_Gallery_C:CreateThumbnails(GridPanel, Array) end
---@param LoadedNewPage_ boolean
function UWBP_EPM_Gallery_C:LoadNewPhotoPage(LoadedNewPage_) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function UWBP_EPM_Gallery_C:InpActEvt_IA_LocatePhotosFolder_K2Node_EnhancedInputActionEvent_0(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ScreenshotsDirectory FString
---@param PhotoModeController ABP_EPM_PhotoModeController_C
function UWBP_EPM_Gallery_C:SetupGallery(ScreenshotsDirectory, PhotoModeController) end
---@param SelfIndex int32
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_BackFromFullscreenBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param ThumbRef UWBP_EPM_ThumbnailDisplayer_C
function UWBP_EPM_Gallery_C:NewlyFocusedThumbnail(ThumbRef) end
---@param SelfIndex int32
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_LocateFolderButton_K2Node_ComponentBoundEvent_11_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_ShowFullscreenBtn_K2Node_ComponentBoundEvent_8_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_BackBtn_K2Node_ComponentBoundEvent_7_ButtonClicked__DelegateSignature(SelfIndex) end
---@param Key FKey
function UWBP_EPM_Gallery_C:AnyKeyPressed(Key) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EPM_Gallery_C:NewInputActionTriggered(InputType, ActionValue) end
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_WBP_CommonSelectorButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature() end
function UWBP_EPM_Gallery_C:BndEvt__WBP_EPM_Gallery_PrevPageSelectorBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature() end
---@param EntryPoint int32
function UWBP_EPM_Gallery_C:ExecuteUbergraph_WBP_EPM_Gallery(EntryPoint) end
function UWBP_EPM_Gallery_C:GalleryUIClosed__DelegateSignature() end


