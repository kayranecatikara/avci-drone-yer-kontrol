---@meta

---@class UWBP_EOM_SettingSelector_C : UWBP_EOM_SettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ActiveItemIndicator UHorizontalBox
---@field SelectNextBtn UWBP_EGUI_CommonSelectorButton_C
---@field SelectPreviousBtn UWBP_EGUI_CommonSelectorButton_C
---@field SettingBorder UBorder
---@field TextValueDisplay UWBP_EGUI_CommonText_C
---@field SelectionIndicators TArray<UWBP_ActiveSelectIndicator_C>
---@field DefaultValue int32
---@field OptionsValues TArray<FS_CultureInvariantOptionsValues>
---@field OptionIntIncrement int32
---@field CurrentValue int32
---@field SettingUpdated FWBP_EOM_SettingSelector_CSettingUpdated
local UWBP_EOM_SettingSelector_C = {}

function UWBP_EOM_SettingSelector_C:CallUpdateAndSaveSetting() end
---@param Text FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EOM_SettingSelector_C:GetAdditionalDescription(Text, ImageToDisplay) end
---@param DefaultValue FText
function UWBP_EOM_SettingSelector_C:GetDefaultValueAsText(DefaultValue) end
---@param IntValue int32
function UWBP_EOM_SettingSelector_C:SetCurrentValueAsInt(IntValue) end
---@param IntValue int32
function UWBP_EOM_SettingSelector_C:GetCurrentValueAsInt(IntValue) end
function UWBP_EOM_SettingSelector_C:ResetToDefault() end
---@param UseCustomSettingSavedValue_ boolean
---@param Value int32
---@param RefreshOptions_ boolean
function UWBP_EOM_SettingSelector_C:InitValue(UseCustomSettingSavedValue_, Value, RefreshOptions_) end
---@param StringValue FString
---@param SearchCultureInvariantValue_ boolean
---@return int32
function UWBP_EOM_SettingSelector_C:FindValueFromString(StringValue, SearchCultureInvariantValue_) end
---@param Length int32
---@param LastIndex int32
function UWBP_EOM_SettingSelector_C:GetArrayInfos(Length, LastIndex) end
function UWBP_EOM_SettingSelector_C:RefreshSelectionIndicators() end
---@param CurrentValue int32
---@param CallUpdate_ boolean
function UWBP_EOM_SettingSelector_C:UpdateCurrentValue(CurrentValue, CallUpdate_) end
---@param IsDesignTime boolean
function UWBP_EOM_SettingSelector_C:PreConstruct(IsDesignTime) end
---@param NextValue_ boolean
function UWBP_EOM_SettingSelector_C:SettingUpdateValue(NextValue_) end
function UWBP_EOM_SettingSelector_C:ReInitOptions() end
function UWBP_EOM_SettingSelector_C:BndEvt__WBP_EOM_SettingSelector_WBP_CommonSelectorButton_103_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature() end
function UWBP_EOM_SettingSelector_C:BndEvt__WBP_EOM_SettingSelector_SelectNextBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature() end
---@param EntryPoint int32
function UWBP_EOM_SettingSelector_C:ExecuteUbergraph_WBP_EOM_SettingSelector(EntryPoint) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EOM_SettingSelector_C:SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end


