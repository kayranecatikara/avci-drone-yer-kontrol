---@meta

---@class UWBP_ScoreboardItem_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ItemAnim UWidgetAnimation
---@field TextBlock_Date UTextBlock
---@field TextBlock_DateTime UTextBlock
---@field TextBlock_FailCrash UTextBlock
---@field TextBlock_SuccessScore UTextBlock
---@field TextBlock_TotalCrash UTextBlock
---@field TextBlock_TotalTime UTextBlock
---@field Text_FailScore FText
---@field Text_SuccessScore FText
---@field Text_TotalScore FText
---@field Text_TotalTime FText
---@field Text_Date FText
---@field Text_DateTime FText
local UWBP_ScoreboardItem_C = {}

function UWBP_ScoreboardItem_C:Construct() end
---@param EntryPoint int32
function UWBP_ScoreboardItem_C:ExecuteUbergraph_WBP_ScoreboardItem(EntryPoint) end


