---@meta

---@class UWBP_MenuCard_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Button UButton
---@field Button_Selected UButton
---@field SaveFileDisplayName UWBP_EGUI_CommonText_C
---@field SaveFileThumbnail UImage
---@field OnClicked FWBP_MenuCard_COnClicked
---@field OnHover FWBP_MenuCard_COnHover
---@field Image UTexture2D
---@field Text FText
---@field OnUnhover FWBP_MenuCard_COnUnhover
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field canSwitchButton boolean
local UWBP_MenuCard_C = {}

function UWBP_MenuCard_C:BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature() end
function UWBP_MenuCard_C:BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature() end
function UWBP_MenuCard_C:Construct() end
function UWBP_MenuCard_C:BndEvt__WBP_MapCard_Button_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature() end
---@param IsSelected boolean
function UWBP_MenuCard_C:SetSelectButton(IsSelected) end
---@param EntryPoint int32
function UWBP_MenuCard_C:ExecuteUbergraph_WBP_MenuCard(EntryPoint) end
function UWBP_MenuCard_C:OnUnhover__DelegateSignature() end
function UWBP_MenuCard_C:OnClicked__DelegateSignature() end
function UWBP_MenuCard_C:OnHover__DelegateSignature() end


