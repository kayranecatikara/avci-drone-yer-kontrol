---@meta

---@class UWBP_EasyMultiInputPromptDisplayer_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Container UHorizontalBox
---@field ['UseInputAction?'] boolean
---@field InputAction UInputAction
---@field InputMappingContext UInputMappingContext
---@field ['MNK Keys'] TArray<FKey>
---@field ['Gamepad Keys'] TArray<FKey>
---@field ['Key Image Size'] double
---@field ['Text to Display'] FText
---@field ['Text Position'] EHorizontalAlignment
---@field ['Text Padding'] FMargin
---@field ['Text Styling'] FS_CommonTextInfo
---@field Spacing double
---@field LastIndex int32
---@field ['Hide Key for Other Devices?'] boolean
---@field ['HideTextAsWell?'] boolean
---@field ['Use Styling Local Override?'] boolean
---@field ['Text Color'] FSlateColor
---@field ['Icon Color'] FLinearColor
---@field InputPromptsReferences TArray<UWBP_EasyInputPromptDisplayer_C>
local UWBP_EasyMultiInputPromptDisplayer_C = {}

---@param Array TArray<FKey>
function UWBP_EasyMultiInputPromptDisplayer_C:CreateInputPromptsWidgets(Array) end
function UWBP_EasyMultiInputPromptDisplayer_C:RefreshInputPrompts() end
---@param IsDesignTime boolean
function UWBP_EasyMultiInputPromptDisplayer_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EasyMultiInputPromptDisplayer_C:ExecuteUbergraph_WBP_EasyMultiInputPromptDisplayer(EntryPoint) end


