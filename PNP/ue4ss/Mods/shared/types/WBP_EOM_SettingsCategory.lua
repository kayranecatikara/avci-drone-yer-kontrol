---@meta

---@class UWBP_EOM_SettingsCategory_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Divider UBorder
---@field SectionName UWBP_EGUI_CommonText_C
---@field SizeBox USizeBox
---@field Name FText
---@field SizeBoxHeight float
---@field ['Text Styling'] FS_CommonTextInfo
local UWBP_EOM_SettingsCategory_C = {}

---@param IsDesignTime boolean
function UWBP_EOM_SettingsCategory_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EOM_SettingsCategory_C:ExecuteUbergraph_WBP_EOM_SettingsCategory(EntryPoint) end


