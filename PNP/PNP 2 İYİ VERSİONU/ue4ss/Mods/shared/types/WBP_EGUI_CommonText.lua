---@meta

---@class UWBP_EGUI_CommonText_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field TextWidget UTextBlock
---@field Text FText
---@field TextStyling FS_CommonTextInfo
---@field FontMaterialOverride UMaterialInterface
---@field ['WrapText?'] boolean
---@field ['InitByCodeOnly?'] boolean
---@field ['UseStylingLocalOverride?'] boolean
---@field TextColor FSlateColor
---@field ['Inverted Text Color'] FSlateColor
---@field ['OverrideColorsOnly?'] boolean
---@field CustomTextFont FSlateFontInfo
---@field TextShadowOffset FVector2D
---@field TextShadowColor FLinearColor
local UWBP_EGUI_CommonText_C = {}

---@param InText FText
function UWBP_EGUI_CommonText_C:SetText(InText) end
---@param Text FText
function UWBP_EGUI_CommonText_C:GetText(Text) end
---@param Inverted_ boolean
function UWBP_EGUI_CommonText_C:SwitchTextColor(Inverted_) end
---@param TextStyling FS_CommonTextInfo
---@param Text FText
function UWBP_EGUI_CommonText_C:UpdateFontInfos(TextStyling, Text) end
---@param TextStyling FS_CommonTextInfo
function UWBP_EGUI_CommonText_C:UpdateTextStyling(TextStyling) end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonText_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EGUI_CommonText_C:ExecuteUbergraph_WBP_EGUI_CommonText(EntryPoint) end


