---@meta

---@class UWBP_EGUI_CommonTooltip_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UWBP_EGUI_CommonBackground_C
---@field RichText UWBP_EGUI_CommonRichText_C
---@field TextStyling FS_CommonTextInfo
local UWBP_EGUI_CommonTooltip_C = {}

function UWBP_EGUI_CommonTooltip_C:Construct() end
---@param InText FText
function UWBP_EGUI_CommonTooltip_C:UpdateText(InText) end
---@param EntryPoint int32
function UWBP_EGUI_CommonTooltip_C:ExecuteUbergraph_WBP_EGUI_CommonTooltip(EntryPoint) end


