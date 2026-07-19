---@meta

---@class UWBP_EPM_SettingProgressBar_C : UWBP_EPM_PhotoModeSettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ProgressBar UProgressBar
---@field ProgressBarBorder UBorder
---@field Slider USlider
---@field ValueInput USpinBox
---@field SettingUpdated FWBP_EPM_SettingProgressBar_CSettingUpdated
---@field MinAllowedValue double
---@field MaxAllowedValue double
---@field DefaultValue double
---@field OffsetValue double
---@field FractionalDigits int32
---@field CurrentValue double
---@field ['WidgetConstructed?'] boolean
---@field MaxHoldMultiplier double
---@field ['UpdateOnValueChanged?'] boolean
---@field InputInterval double
---@field PreviousInputTime double
---@field TicksHeld double
local UWBP_EPM_SettingProgressBar_C = {}

function UWBP_EPM_SettingProgressBar_C:ResetToDefault() end
function UWBP_EPM_SettingProgressBar_C:UpdateGlobalStyling() end
---@param DefaultValueClamped double
function UWBP_EPM_SettingProgressBar_C:InitSliderValues(DefaultValueClamped) end
function UWBP_EPM_SettingProgressBar_C:InitTextInputValues() end
---@param Value double
function UWBP_EPM_SettingProgressBar_C:InitValue(Value) end
---@param CurrentValue double
---@param CallUpdate_ boolean
function UWBP_EPM_SettingProgressBar_C:UpdateCurrentValue(CurrentValue, CallUpdate_) end
---@param Value float
function UWBP_EPM_SettingProgressBar_C:BndEvt__W_SettingProgress_Slider_K2Node_ComponentBoundEvent_2_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param InValue float
---@param CommitMethod ETextCommit::Type
function UWBP_EPM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_ValueInput_K2Node_ComponentBoundEvent_1_OnSpinBoxValueCommittedEvent__DelegateSignature(InValue, CommitMethod) end
---@param NextValue_ boolean
function UWBP_EPM_SettingProgressBar_C:SettingUpdateValue(NextValue_) end
function UWBP_EPM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_7_OnControllerCaptureEndEvent__DelegateSignature() end
function UWBP_EPM_SettingProgressBar_C:BndEvt__WBP_EOM_SettingProgress_Slider_K2Node_ComponentBoundEvent_8_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_EPM_SettingProgressBar_C:Construct() end
---@param IsDesignTime boolean
function UWBP_EPM_SettingProgressBar_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EPM_SettingProgressBar_C:ExecuteUbergraph_WBP_EPM_SettingProgressBar(EntryPoint) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EPM_SettingProgressBar_C:SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end


