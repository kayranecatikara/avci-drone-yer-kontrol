---@meta

---@class UWBP_EGUI_CommonBackgroundImage_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UBorder
---@field BackgroundImage UImage
---@field BackgroundScaleBox UScaleBox
---@field ['DisplayBackgroundImage?'] boolean
---@field ImageBrush FSlateBrush
---@field ['DisplayBackgroundColor?'] boolean
---@field BackgroundColorBrush FSlateBrush
local UWBP_EGUI_CommonBackgroundImage_C = {}

---@param IsDesignTime boolean
function UWBP_EGUI_CommonBackgroundImage_C:PreConstruct(IsDesignTime) end
---@param Texture UTexture2D
function UWBP_EGUI_CommonBackgroundImage_C:UpdateBackgroundImage(Texture) end
---@param EntryPoint int32
function UWBP_EGUI_CommonBackgroundImage_C:ExecuteUbergraph_WBP_EGUI_CommonBackgroundImage(EntryPoint) end


