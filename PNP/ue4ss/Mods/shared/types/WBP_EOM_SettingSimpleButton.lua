---@meta

---@class UWBP_EOM_SettingSimpleButton_C : UWBP_EOM_SettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ActionButton UWBP_EGUI_CommonButton_C
---@field SettingUpdated FWBP_EOM_SettingSimpleButton_CSettingUpdated
---@field ButtonActionText FText
---@field AdditionalDescription FS_OptionsAdditionalDescription
local UWBP_EOM_SettingSimpleButton_C = {}

---@param MyGeometry FGeometry
---@param InFocusEvent FFocusEvent
---@return FEventReply
function UWBP_EOM_SettingSimpleButton_C:OnFocusReceived(MyGeometry, InFocusEvent) end
function UWBP_EOM_SettingSimpleButton_C:UpdateButtonFocus() end
---@param Text FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EOM_SettingSimpleButton_C:GetAdditionalDescription(Text, ImageToDisplay) end
---@param SelfIndex int32
function UWBP_EOM_SettingSimpleButton_C:BndEvt__WBP_EOM_SettingToggle_OffBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EOM_SettingSimpleButton_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EOM_SettingSimpleButton_C:ExecuteUbergraph_WBP_EOM_SettingSimpleButton(EntryPoint) end
function UWBP_EOM_SettingSimpleButton_C:SettingUpdated__DelegateSignature() end


