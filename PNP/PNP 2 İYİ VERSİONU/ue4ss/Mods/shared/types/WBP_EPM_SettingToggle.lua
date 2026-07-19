---@meta

---@class UWBP_EPM_SettingToggle_C : UWBP_EPM_PhotoModeSettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field OffBtn UWBP_EGUI_CommonButton_C
---@field OnBtn UWBP_EGUI_CommonButton_C
---@field DefaultValue boolean
---@field CurrentValue boolean
---@field SettingUpdated FWBP_EPM_SettingToggle_CSettingUpdated
local UWBP_EPM_SettingToggle_C = {}

function UWBP_EPM_SettingToggle_C:ResetToDefault() end
---@param Value boolean
function UWBP_EPM_SettingToggle_C:InitValue(Value) end
---@param CurrentValue boolean
---@param CallUpdate_ boolean
function UWBP_EPM_SettingToggle_C:UpdateCurrentValue(CurrentValue, CallUpdate_) end
---@param NextValue_ boolean
function UWBP_EPM_SettingToggle_C:SettingUpdateValue(NextValue_) end
---@param SelfIndex int32
function UWBP_EPM_SettingToggle_C:BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EPM_SettingToggle_C:BndEvt__WBP_EOM_SettingToggle_OnBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EPM_SettingToggle_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EPM_SettingToggle_C:ExecuteUbergraph_WBP_EPM_SettingToggle(EntryPoint) end
---@param NewValue boolean
function UWBP_EPM_SettingToggle_C:SettingUpdated__DelegateSignature(NewValue) end


