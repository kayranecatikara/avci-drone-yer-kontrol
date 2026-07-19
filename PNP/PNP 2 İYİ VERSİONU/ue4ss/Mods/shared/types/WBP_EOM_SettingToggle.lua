---@meta

---@class UWBP_EOM_SettingToggle_C : UWBP_EOM_SettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field OffBtn UWBP_EGUI_CommonButton_C
---@field OnBtn UWBP_EGUI_CommonButton_C
---@field DefaultValue boolean
---@field CurrentValue boolean
---@field SettingUpdated FWBP_EOM_SettingToggle_CSettingUpdated
---@field OptionsAdditionalDescription TArray<FS_OptionsAdditionalDescription>
local UWBP_EOM_SettingToggle_C = {}

function UWBP_EOM_SettingToggle_C:CallUpdateAndSaveSetting() end
---@param Text FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EOM_SettingToggle_C:GetAdditionalDescription(Text, ImageToDisplay) end
---@param DefaultValue FText
function UWBP_EOM_SettingToggle_C:GetDefaultValueAsText(DefaultValue) end
---@param IntValue int32
function UWBP_EOM_SettingToggle_C:SetCurrentValueAsInt(IntValue) end
---@param IntValue int32
function UWBP_EOM_SettingToggle_C:GetCurrentValueAsInt(IntValue) end
function UWBP_EOM_SettingToggle_C:ResetToDefault() end
---@param UseCustomSettingSavedValue_ boolean
---@param Value boolean
function UWBP_EOM_SettingToggle_C:InitValue(UseCustomSettingSavedValue_, Value) end
---@param CurrentValue boolean
---@param CallUpdate_ boolean
function UWBP_EOM_SettingToggle_C:UpdateCurrentValue(CurrentValue, CallUpdate_) end
---@param NextValue_ boolean
function UWBP_EOM_SettingToggle_C:SettingUpdateValue(NextValue_) end
---@param SelfIndex int32
function UWBP_EOM_SettingToggle_C:BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EOM_SettingToggle_C:BndEvt__WBP_EOM_SettingToggle_OnBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EOM_SettingToggle_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EOM_SettingToggle_C:ExecuteUbergraph_WBP_EOM_SettingToggle(EntryPoint) end
---@param NewValue boolean
function UWBP_EOM_SettingToggle_C:SettingUpdated__DelegateSignature(NewValue) end


