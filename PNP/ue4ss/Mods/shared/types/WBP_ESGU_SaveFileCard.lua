---@meta

---@class UWBP_ESGU_SaveFileCard_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UWBP_EGUI_CommonBackground_C
---@field DisplayName UWBP_EGUI_CommonText_C
---@field GameVersion UWBP_EGUI_CommonText_C
---@field PlayTime UWBP_EGUI_CommonText_C
---@field SaveDate UWBP_EGUI_CommonText_C
---@field UniqueName UWBP_EGUI_CommonText_C
---@field SaveGamesUIRef UWBP_ESGU_SavesManagerUI_C
---@field Thumbnail UTexture2D
---@field MetaDatas FS_SaveGameMetadatas
---@field ['SaveFileIncompatible?'] boolean
local UWBP_ESGU_SaveFileCard_C = {}

---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_ESGU_SaveFileCard_C:OnMouseButtonDown(MyGeometry, MouseEvent) end
---@param MetaDatas FS_SaveGameMetadatas
function UWBP_ESGU_SaveFileCard_C:RefreshMetadatas(MetaDatas) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
function UWBP_ESGU_SaveFileCard_C:OnMouseEnter(MyGeometry, MouseEvent) end
---@param InFocusEvent FFocusEvent
function UWBP_ESGU_SaveFileCard_C:OnAddedToFocusPath(InFocusEvent) end
function UWBP_ESGU_SaveFileCard_C:Construct() end
---@param EntryPoint int32
function UWBP_ESGU_SaveFileCard_C:ExecuteUbergraph_WBP_ESGU_SaveFileCard(EntryPoint) end


