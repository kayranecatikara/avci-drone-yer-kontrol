---@meta

---@class UWBP_LoadingScreenSelf_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Image_Background UImage
---@field ProgressBar_0 UProgressBar
---@field Text_LoadingPercent UTextBlock
---@field TextBlock_MapName UTextBlock
---@field ['As BP Game Instance'] UBP_GameInstance_C
---@field DTMaps UDataTable
local UWBP_LoadingScreenSelf_C = {}

---@param Percent double
function UWBP_LoadingScreenSelf_C:UpdateProgressBarValue(Percent) end
function UWBP_LoadingScreenSelf_C:Construct() end
---@param EntryPoint int32
function UWBP_LoadingScreenSelf_C:ExecuteUbergraph_WBP_LoadingScreenSelf(EntryPoint) end


