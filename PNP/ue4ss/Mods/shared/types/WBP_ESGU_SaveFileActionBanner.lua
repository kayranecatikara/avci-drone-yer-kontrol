---@meta

---@class UWBP_ESGU_SaveFileActionBanner_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ActionDescriptionText UWBP_EGUI_CommonText_C
---@field ActionTitleText UWBP_EGUI_CommonText_C
---@field CancelButton UWBP_EGUI_CommonButton_C
---@field ContinueButton UWBP_EGUI_CommonButton_C
---@field Divider UBorder
---@field SaveFileCard UWBP_ESGU_SaveFileCard_C
---@field ActionTitle FText
---@field ActionDescription FText
---@field SaveFileMetadatas FS_SaveGameMetadatas
---@field UnderlyingWidget UUserWidget
---@field TitleTextStyling FS_CommonTextInfo
---@field DescriptionTextStyling FS_CommonTextInfo
---@field ActionRequested FWBP_ESGU_SaveFileActionBanner_CActionRequested
---@field HUD AHUD
local UWBP_ESGU_SaveFileActionBanner_C = {}

---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_ESGU_SaveFileActionBanner_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param IsDesignTime boolean
function UWBP_ESGU_SaveFileActionBanner_C:PreConstruct(IsDesignTime) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_ESGU_SaveFileActionBanner_C:NewInputActionTriggered(InputType, ActionValue) end
---@param Key FKey
function UWBP_ESGU_SaveFileActionBanner_C:AnyKeyPressed(Key) end
---@param SelfIndex int32
function UWBP_ESGU_SaveFileActionBanner_C:BndEvt__WBP_ESGU_SaveFileActionBanner_ContinueButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_ESGU_SaveFileActionBanner_C:BndEvt__WBP_ESGU_SaveFileActionBanner_CancelButton_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
function UWBP_ESGU_SaveFileActionBanner_C:Construct() end
---@param ButtonIndex int32
function UWBP_ESGU_SaveFileActionBanner_C:ResetSaveActionBanner(ButtonIndex) end
---@param EntryPoint int32
function UWBP_ESGU_SaveFileActionBanner_C:ExecuteUbergraph_WBP_ESGU_SaveFileActionBanner(EntryPoint) end
---@param ButtonIndex int32
function UWBP_ESGU_SaveFileActionBanner_C:ActionRequested__DelegateSignature(ButtonIndex) end


