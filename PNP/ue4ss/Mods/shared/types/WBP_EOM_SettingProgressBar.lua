---@meta

---@class UWBP_EOM_SettingProgressBar_C : UWBP_EOM_SettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ProgressBar UProgressBar
---@field ProgressBarBorder UBorder
---@field Slider USlider
---@field ValueInput USpinBox
---@field SettingUpdated FWBP_EOM_SettingProgressBar_CSettingUpdated
---@field MinAllowedValue double
---@field MaxAllowedValue double
---@field DefaultValue double
---@field OffsetValue double
---@field FractionalDigits int32
---@field CurrentValue double
---@field SettingAdditionalDescription TMap<double, FS_OptionsAdditionalDescription>
---@field PreviousInputTime double
---@field InputInterval double
---@field TicksHeld double
---@field ['WidgetConstructed?'] boolean
local UWBP_EOM_SettingProgressBar_C = {}

function UWBP_EOM_SettingProgressBar_C:CallUpdateAndSaveSetting() end
---@param Text FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EOM_SettingProgressBar_C:GetAdditionalDescription(Text, ImageToDisplay) end
---@param DefaultValue FText
function UWBP_EOM_SettingProgressBar_C:GetDefaultValueAsText(DefaultValue) end
function UWBP_EOM_SettingProgressBar_C:ResetToDefault() end
function UWBP_EOM_SettingProgressBar_C:UpdateGlobalStyling() end
---@param DefaultValueClamped double
function UWBP_EOM_SettingProgressBar_C:InitSliderValues(DefaultValueClamped) end
function UWBP_EOM_SettingProgressBar_C:InitTextInputValues() end
---@param UseCustomSettingSavedValue_ boolean
---@param Value double
function UWBP_EOM_SettingProgressBar_C:InitValue(UseCustomSettingSavedValue_, Value) end
---@param CurrentValue double
---@param CallUpdate_ boolean
function UWBP_EOM_SettingProgressBar_C:UpdateCurrentValue(CurrentValue, CallUpdate_) end
---@param Value float
function UWBP_EOM_SettingProgressBar_C:BndEvt__W_SettingProgress_Slider_K2Node_ComponentBoundEvent_2_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param InValue float
---@param CommitMethod ETextCommit::Type
function UWBP_EOM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_ValueInput_K2Node_ComponentBoundEvent_1_OnSpinBoxValueCommittedEvent__DelegateSignature(InValue, CommitMethod) end
function UWBP_EOM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_7_OnControllerCaptureEndEvent__DelegateSignature() end
function UWBP_EOM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_8_OnMouseCaptureEndEvent__DelegateSignature() end
---@param NextValue_ boolean
function UWBP_EOM_SettingProgressBar_C:SettingUpdateValue(NextValue_) end
function UWBP_EOM_SettingProgressBar_C:Construct() end
---@param IsDesignTime boolean
function UWBP_EOM_SettingProgressBar_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EOM_SettingProgressBar_C:ExecuteUbergraph_WBP_EOM_SettingProgressBar(EntryPoint) end
---@param NewValue double
function UWBP_EOM_SettingProgressBar_C:SettingUpdated__DelegateSignature(NewValue) end


