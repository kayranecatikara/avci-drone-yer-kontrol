---@meta

---@class UWBP_GlobalUI_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field VerticalBox_AmmunationInformation UVerticalBox
---@field WBP_KillFeedPanel UWBP_KillFeedPanel_C
---@field Text_InfoAmmo FText
---@field Text_InfoFiberRope FText
local UWBP_GlobalUI_C = {}

function UWBP_GlobalUI_C:ShowAmmunitionInfo() end
function UWBP_GlobalUI_C:ShowFiberRopeInfo() end
---@param EntryPoint int32
function UWBP_GlobalUI_C:ExecuteUbergraph_WBP_GlobalUI(EntryPoint) end


