---@meta

---@class UWBP_EPM_ThumbnailDisplayer_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field BackgroundButton UWBP_EGUI_CommonButton_C
---@field Image UImage
---@field ScaleBox UScaleBox
---@field ImageBrush FSlateBrush
---@field ScreenshotName FString
---@field ['ThumbnailLoaded?'] boolean
---@field ImageClicked FWBP_EPM_ThumbnailDisplayer_CImageClicked
---@field GalleryRef UWBP_EPM_Gallery_C
local UWBP_EPM_ThumbnailDisplayer_C = {}

---@param MyGeometry FGeometry
---@param InFocusEvent FFocusEvent
---@return FEventReply
function UWBP_EPM_ThumbnailDisplayer_C:OnFocusReceived(MyGeometry, InFocusEvent) end
---@param SelfIndex int32
function UWBP_EPM_ThumbnailDisplayer_C:BndEvt__WBP_ThumbnailDisplayer_WBP_EGUI_CommonButton_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
function UWBP_EPM_ThumbnailDisplayer_C:OnMouseEnter(MyGeometry, MouseEvent) end
function UWBP_EPM_ThumbnailDisplayer_C:Construct() end
---@param InFocusEvent FFocusEvent
function UWBP_EPM_ThumbnailDisplayer_C:OnAddedToFocusPath(InFocusEvent) end
---@param EntryPoint int32
function UWBP_EPM_ThumbnailDisplayer_C:ExecuteUbergraph_WBP_EPM_ThumbnailDisplayer(EntryPoint) end
---@param ImageRef UTexture2D
---@param ScreenshotName FString
function UWBP_EPM_ThumbnailDisplayer_C:ImageClicked__DelegateSignature(ImageRef, ScreenshotName) end


