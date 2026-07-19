---@meta

---@class UWBP_EGUI_OptionDescription_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field DescriptionTextScrollBox UWBP_EGUI_CommonScrollBox_C
---@field DisplayImage UBorder
---@field DisplayImageBox UScaleBox
---@field Divider UBorder
---@field OptionTitleText UWBP_EGUI_CommonText_C
---@field RichTextDescription UWBP_EGUI_CommonRichText_C
---@field TitleTextStyling FS_CommonTextInfo
---@field DescriptionTextStyling FS_CommonTextInfo
---@field ['DescriptionOnly?'] boolean
---@field DividerHorizontalAlignment EHorizontalAlignment
---@field CurrentImageDisplayed TSoftObjectPtr<UTexture2D>
local UWBP_EGUI_OptionDescription_C = {}

---@return FText
function UWBP_EGUI_OptionDescription_C:GetDescriptionText() end
---@param OptionTitle FText
---@param OptionDescription FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EGUI_OptionDescription_C:UpdateDescription(OptionTitle, OptionDescription, ImageToDisplay) end
---@param Loaded UObject
function UWBP_EGUI_OptionDescription_C:OnLoaded_C4B73404456EE5B2D218C6963C5C63AD(Loaded) end
function UWBP_EGUI_OptionDescription_C:Construct() end
---@param IsDesignTime boolean
function UWBP_EGUI_OptionDescription_C:PreConstruct(IsDesignTime) end
---@param ImageToLoad TSoftObjectPtr<UObject>
function UWBP_EGUI_OptionDescription_C:LoadNewDescriptionImage(ImageToLoad) end
---@param EntryPoint int32
function UWBP_EGUI_OptionDescription_C:ExecuteUbergraph_WBP_EGUI_OptionDescription(EntryPoint) end


