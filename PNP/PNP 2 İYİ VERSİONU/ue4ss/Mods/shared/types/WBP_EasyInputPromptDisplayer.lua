---@meta

---@class UWBP_EasyInputPromptDisplayer_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field MashInteractionAnimation UWidgetAnimation
---@field ResetProgressAnimation UWidgetAnimation
---@field HoldAnimation UWidgetAnimation
---@field GridPanel UGridPanel
---@field InputProgressIndicator UProgressBar
---@field Key UImage
---@field KeyText UWBP_EGUI_CommonText_C
---@field MashInteractionIndicator UImage
---@field RetainerBox URetainerBox
---@field ScaleBox UScaleBox
---@field ['UseInputAction?'] boolean
---@field InputActionInfos FS_InputActionDef
---@field GamepadKey FKey
---@field MouseKeyboardKey FKey
---@field DisplayConditions E_InputPromptDisplayConditions::Type
---@field ['HideKeyForOtherDevices?'] boolean
---@field KeyImageSize double
---@field TextToDisplay FText
---@field TextPosition EHorizontalAlignment
---@field TextPadding FMargin
---@field TextStyling FS_CommonTextInfo
---@field ['IsUsingGamepad?'] boolean
---@field ['HideTextAsWell?'] boolean
---@field InputPromptType E_InputPromptType::Type
---@field ['UseStylingLocalOverride?'] boolean
---@field TextColor FSlateColor
---@field IconColor FLinearColor
---@field CurrentGamepadKeys UDataTable
---@field RequiredMashPresses double
---@field OverlayMaterial UMaterialInterface
---@field OverlayMaterialTextureParameterName FName
local UWBP_EasyInputPromptDisplayer_C = {}

---@param NewText FText
function UWBP_EasyInputPromptDisplayer_C:SetText(NewText) end
---@param InputType E_InputPromptType::Type
function UWBP_EasyInputPromptDisplayer_C:SelectNewInputType(InputType) end
function UWBP_EasyInputPromptDisplayer_C:GetCurrentGamepadBrand() end
function UWBP_EasyInputPromptDisplayer_C:UpdateInputIcon() end
function UWBP_EasyInputPromptDisplayer_C:UpdateStyling() end
function UWBP_EasyInputPromptDisplayer_C:InputsUpdated() end
function UWBP_EasyInputPromptDisplayer_C:Construct() end
---@param HoldDuration double
function UWBP_EasyInputPromptDisplayer_C:HoldInputStarted(HoldDuration) end
---@param Fail_ boolean
function UWBP_EasyInputPromptDisplayer_C:HoldInputCompleted(Fail_) end
function UWBP_EasyInputPromptDisplayer_C:ProgressMashInput() end
---@param Fail_ boolean
function UWBP_EasyInputPromptDisplayer_C:MashInputCompleted(Fail_) end
---@param RequiredPresses int32
function UWBP_EasyInputPromptDisplayer_C:MashInputStarted(RequiredPresses) end
---@param IsDesignTime boolean
function UWBP_EasyInputPromptDisplayer_C:PreConstruct(IsDesignTime) end
---@param UserId FPlatformUserId
---@param DeviceID FInputDeviceId
function UWBP_EasyInputPromptDisplayer_C:InputMethodChanged(UserId, DeviceID) end
---@param EntryPoint int32
function UWBP_EasyInputPromptDisplayer_C:ExecuteUbergraph_WBP_EasyInputPromptDisplayer(EntryPoint) end


