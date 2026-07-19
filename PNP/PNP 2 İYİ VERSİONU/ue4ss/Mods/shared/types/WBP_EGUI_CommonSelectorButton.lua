---@meta

---@class UWBP_EGUI_CommonSelectorButton_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Button UWBP_EGUI_CommonButton_C
---@field SelectorImage UImage
---@field ImageSize FVector2D
---@field SelectorRotationAngle float
---@field ImagePadding FMargin
---@field ButtonStyle E_ButtonStyleSelector::Type
---@field SelectionIndicatorPosition E_SelectionIndicatorPosition::Type
---@field PreferedRoundingType ESlateBrushRoundingType::Type
---@field ButtonClicked FWBP_EGUI_CommonSelectorButton_CButtonClicked
local UWBP_EGUI_CommonSelectorButton_C = {}

---@param Loaded UObject
function UWBP_EGUI_CommonSelectorButton_C:OnLoaded_F753DC434E4BB979AC9A8DA34EADA30F(Loaded) end
---@param SelfIndex int32
function UWBP_EGUI_CommonSelectorButton_C:BndEvt__WBP_CommonSelectorButton_Button_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonSelectorButton_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EGUI_CommonSelectorButton_C:ExecuteUbergraph_WBP_EGUI_CommonSelectorButton(EntryPoint) end
function UWBP_EGUI_CommonSelectorButton_C:ButtonClicked__DelegateSignature() end


