---@meta

---@class UWBP_ActiveSelectIndicator_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Border UBorder
---@field ['IsActive?'] boolean
---@field AccentColor FLinearColor
local UWBP_ActiveSelectIndicator_C = {}

---@param Active_ boolean
function UWBP_ActiveSelectIndicator_C:UpdateState(Active_) end
function UWBP_ActiveSelectIndicator_C:Construct() end
---@param EntryPoint int32
function UWBP_ActiveSelectIndicator_C:ExecuteUbergraph_WBP_ActiveSelectIndicator(EntryPoint) end


