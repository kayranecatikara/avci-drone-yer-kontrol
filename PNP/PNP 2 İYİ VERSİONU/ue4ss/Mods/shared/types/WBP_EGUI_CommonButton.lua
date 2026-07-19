---@meta

---@class UWBP_EGUI_CommonButton_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SelectionIndicatorFadeInOut UWidgetAnimation
---@field Button UButton
---@field ButtonText UWBP_EGUI_CommonText_C
---@field SelectionIndicator UImage
---@field ButtonList TArray<UWBP_EGUI_CommonButton_C>
---@field Text FText
---@field ['Text Styling'] FS_CommonTextInfo
---@field TextPadding FMargin
---@field ButtonHorizontalAlignment EHorizontalAlignment
---@field ButtonVerticalAlignment EVerticalAlignment
---@field ['IsActive?'] boolean
---@field ['AlwaysResetActiveState?'] boolean
---@field ['SearchForSiblings?'] boolean
---@field SelectionIndicatorPosition E_SelectionIndicatorPosition::Type
---@field ButtonStyle E_ButtonStyleSelector::Type
---@field ['UseStylingLocalOverride?'] boolean
---@field PreferedRoundingType ESlateBrushRoundingType::Type
---@field NormalButtonStyle FSlateBrush
---@field HoveredButtonStyle FSlateBrush
---@field PressedButtonStyle FSlateBrush
---@field SelfIndex int32
---@field ButtonClicked FWBP_EGUI_CommonButton_CButtonClicked
---@field ButtonPressed FWBP_EGUI_CommonButton_CButtonPressed
---@field ButtonReleased FWBP_EGUI_CommonButton_CButtonReleased
---@field ButtonFocused FWBP_EGUI_CommonButton_CButtonFocused
---@field ButtonUnfocused FWBP_EGUI_CommonButton_CButtonUnfocused
---@field ['InitByCodeOnly?'] boolean
---@field ['In Is Enabled'] boolean
local UWBP_EGUI_CommonButton_C = {}

---@param MyGeometry FGeometry
---@param InFocusEvent FFocusEvent
---@return FEventReply
function UWBP_EGUI_CommonButton_C:OnFocusReceived(MyGeometry, InFocusEvent) end
---@param UpdateTextColor_ boolean
function UWBP_EGUI_CommonButton_C:SetHoverStylingState(UpdateTextColor_) end
---@param UpdateTextColor_ boolean
function UWBP_EGUI_CommonButton_C:SetActiveStylingState(UpdateTextColor_) end
---@param UpdateTextColor_ boolean
function UWBP_EGUI_CommonButton_C:SetNormalStylingState(UpdateTextColor_) end
function UWBP_EGUI_CommonButton_C:InitButtonStyling() end
function UWBP_EGUI_CommonButton_C:InitTextStyling() end
function UWBP_EGUI_CommonButton_C:InitSelectionIndicator() end
function UWBP_EGUI_CommonButton_C:GetSiblingsButtons() end
function UWBP_EGUI_CommonButton_C:BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature() end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonButton_C:PreConstruct(IsDesignTime) end
function UWBP_EGUI_CommonButton_C:BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_4_OnButtonPressedEvent__DelegateSignature() end
function UWBP_EGUI_CommonButton_C:BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_5_OnButtonReleasedEvent__DelegateSignature() end
function UWBP_EGUI_CommonButton_C:BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature() end
function UWBP_EGUI_CommonButton_C:BndEvt__W_Button_Button_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature() end
---@param InFocusEvent FFocusEvent
function UWBP_EGUI_CommonButton_C:OnAddedToFocusPath(InFocusEvent) end
---@param InFocusEvent FFocusEvent
function UWBP_EGUI_CommonButton_C:OnRemovedFromFocusPath(InFocusEvent) end
function UWBP_EGUI_CommonButton_C:TriggerClickEvent() end
function UWBP_EGUI_CommonButton_C:Construct() end
function UWBP_EGUI_CommonButton_C:InitButton() end
---@param EntryPoint int32
function UWBP_EGUI_CommonButton_C:ExecuteUbergraph_WBP_EGUI_CommonButton(EntryPoint) end
function UWBP_EGUI_CommonButton_C:ButtonUnfocused__DelegateSignature() end
---@param SelfIndex int32
function UWBP_EGUI_CommonButton_C:ButtonFocused__DelegateSignature(SelfIndex) end
function UWBP_EGUI_CommonButton_C:ButtonReleased__DelegateSignature() end
function UWBP_EGUI_CommonButton_C:ButtonPressed__DelegateSignature() end
---@param SelfIndex int32
function UWBP_EGUI_CommonButton_C:ButtonClicked__DelegateSignature(SelfIndex) end


