---@meta

---@class UWBP_SettingsRows_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Row UButton
---@field RowName UTextBlock
---@field HoveredColor FLinearColor
---@field RowText FText
---@field UnhoveredColor FLinearColor
local UWBP_SettingsRows_C = {}

---@param IsDesignTime boolean
function UWBP_SettingsRows_C:PreConstruct(IsDesignTime) end
function UWBP_SettingsRows_C:BndEvt__WBP_SettingsRows_Row_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature() end
function UWBP_SettingsRows_C:SetRow() end
function UWBP_SettingsRows_C:BndEvt__WBP_SettingsRows_Row_K2Node_ComponentBoundEvent_1_OnButtonHoverEvent__DelegateSignature() end
---@param EntryPoint int32
function UWBP_SettingsRows_C:ExecuteUbergraph_WBP_SettingsRows(EntryPoint) end


