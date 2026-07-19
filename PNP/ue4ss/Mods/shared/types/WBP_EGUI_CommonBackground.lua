---@meta

---@class UWBP_EGUI_CommonBackground_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UBorder
---@field NamedSlot UNamedSlot
---@field ['InitByCodeOnly?'] boolean
---@field NormalStyleSelector E_BackgroundStyleSelector::Type
---@field ActiveStyleSelector E_BackgroundStyleSelector::Type
---@field CornerRoundingType ESlateBrushRoundingType::Type
---@field SlotPadding FMargin
---@field SlotHorizontalAlignment EHorizontalAlignment
---@field SlotVerticalAlignment EVerticalAlignment
---@field ['UseStylingLocalOverride?'] boolean
---@field NormalBackgroundColor FLinearColor
---@field ActiveBackgroundColor FLinearColor
---@field ['OutlineUseBackgroundTransparency?'] boolean
---@field ['OnlyOverrideColors?'] boolean
---@field NormalBackgroundStyling FSlateBrush
---@field ActiveBackgroundStyling FSlateBrush
local UWBP_EGUI_CommonBackground_C = {}

function UWBP_EGUI_CommonBackground_C:GetBackgroundStylingFromConfig() end
function UWBP_EGUI_CommonBackground_C:SetBackgroundNormal() end
function UWBP_EGUI_CommonBackground_C:SetBackgroundActive() end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonBackground_C:PreConstruct(IsDesignTime) end
function UWBP_EGUI_CommonBackground_C:InitStyling() end
---@param EntryPoint int32
function UWBP_EGUI_CommonBackground_C:ExecuteUbergraph_WBP_EGUI_CommonBackground(EntryPoint) end


