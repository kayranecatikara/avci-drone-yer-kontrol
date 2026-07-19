---@meta

---@class UWBP_Compass_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Image_Compass UImage
---@field OverlayPanel UOverlay
---@field ['As BPP Spectator'] ABPP_Spectator_C
---@field CompassMaterial UMaterialInstanceDynamic
local UWBP_Compass_C = {}

---@param IsDesignTime boolean
function UWBP_Compass_C:PreConstruct(IsDesignTime) end
function UWBP_Compass_C:CompassRotation() end
---@param EntryPoint int32
function UWBP_Compass_C:ExecuteUbergraph_WBP_Compass(EntryPoint) end


