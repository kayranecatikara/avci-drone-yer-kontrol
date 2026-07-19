---@meta

---@class UWBP_KillFeedItem_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ItemAnim UWidgetAnimation
---@field Image_Icon UImage
---@field TextBlock_Enemy UTextBlock
---@field TextBlock_EnemyCount UTextBlock
---@field TextBlock_PlayerName UTextBlock
---@field Text_PlayerName FText
---@field Text_EnemyName FText
---@field Text_EnemyCount FText
---@field KamikazeBrush FSlateBrush
---@field isNet boolean
---@field NetBrush FSlateBrush
---@field isFail boolean
local UWBP_KillFeedItem_C = {}

function UWBP_KillFeedItem_C:Finished_E9E0132B40781F5947424DBB6884375C() end
function UWBP_KillFeedItem_C:Construct() end
---@param EntryPoint int32
function UWBP_KillFeedItem_C:ExecuteUbergraph_WBP_KillFeedItem(EntryPoint) end


