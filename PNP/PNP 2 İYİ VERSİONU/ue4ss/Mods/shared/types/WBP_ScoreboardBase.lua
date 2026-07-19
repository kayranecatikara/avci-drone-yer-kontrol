---@meta

---@class UWBP_ScoreboardBase_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Gate UWidgetAnimation
---@field Image_Line UImage
---@field WBP_EGUI_CommonText UWBP_EGUI_CommonText_C
---@field WBP_ScoreboardPanel UWBP_ScoreboardPanel_C
local UWBP_ScoreboardBase_C = {}

---@param InVisibility ESlateVisibility
function UWBP_ScoreboardBase_C:ShowNoDataText(InVisibility) end
---@param EntryPoint int32
function UWBP_ScoreboardBase_C:ExecuteUbergraph_WBP_ScoreboardBase(EntryPoint) end


