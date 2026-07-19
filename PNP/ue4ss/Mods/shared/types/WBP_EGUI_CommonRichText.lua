---@meta

---@class UWBP_EGUI_CommonRichText_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field RichText URichTextBlock
---@field Text FText
---@field TextStyling FS_CommonTextInfo
---@field RichTextStyleSet UDataTable
---@field RichTextDecoratorClasses TArray<TSubclassOf<URichTextBlockDecorator>>
---@field ['WrapText?'] boolean
---@field ['InitByCodeOnly?'] boolean
---@field ['UseStylingLocalOverride?'] boolean
---@field TextColor FSlateColor
---@field ['OverrideColorsOnly?'] boolean
---@field CustomRichTextStyle FTextBlockStyle
local UWBP_EGUI_CommonRichText_C = {}

---@param InText FText
function UWBP_EGUI_CommonRichText_C:SetText(InText) end
---@param Text FText
function UWBP_EGUI_CommonRichText_C:GetText(Text) end
---@param TextStyling FS_CommonTextInfo
---@param Text FText
function UWBP_EGUI_CommonRichText_C:UpdateFontInfos(TextStyling, Text) end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonRichText_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EGUI_CommonRichText_C:ExecuteUbergraph_WBP_EGUI_CommonRichText(EntryPoint) end


