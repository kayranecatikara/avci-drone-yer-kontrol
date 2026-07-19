---@meta

---@class UWBP_EOM_SettingsMaster_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UWBP_EGUI_CommonBackground_C
---@field DirtyIndicator UBorder
---@field NamedSlot UNamedSlot
---@field ResetSetting UWBP_EGUI_CommonButton_C
---@field SettingName UWBP_EGUI_CommonText_C
---@field SizeBox USizeBox
---@field OptionsMenuRef UWBP_EasyOptionsMenuMain_C
---@field ActivationConditions TArray<FS_SettingActivationConditions>
---@field ActivationConditionsState TMap<UWBP_EOM_SettingsMaster_C, boolean>
---@field ['SettingEnabled?'] boolean
---@field OptionTitle FText
---@field ['UseStylingLocalOverride?'] boolean
---@field OptionTitleTextStyling FS_CommonTextInfo
---@field OptionDescription FText
---@field ['ApplyOnEdit?'] boolean
---@field ['ShowResetButton?'] boolean
---@field ['SaveCurrentValueToCustomSettings?'] boolean
---@field CustomSettingFieldName FString
---@field ['Dirty?'] boolean
---@field OptionValueTextStyling FS_CommonTextInfo
---@field SizeBoxHeight float
local UWBP_EOM_SettingsMaster_C = {}

---@param bIsSettingEnabled_ boolean
function UWBP_EOM_SettingsMaster_C:SetSettingEnabled(bIsSettingEnabled_) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EOM_SettingsMaster_C:OnMouseButtonDown(MyGeometry, MouseEvent) end
function UWBP_EOM_SettingsMaster_C:CallUpdateAndSaveSetting() end
function UWBP_EOM_SettingsMaster_C:SetAdditionalDescription() end
---@param Text FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
function UWBP_EOM_SettingsMaster_C:GetAdditionalDescription(Text, ImageToDisplay) end
---@param IsDefaultValue_ boolean
function UWBP_EOM_SettingsMaster_C:HandleResetButtonVisibility(IsDefaultValue_) end
---@param DefaultValue FText
function UWBP_EOM_SettingsMaster_C:GetDefaultValueAsText(DefaultValue) end
---@param ControllerWidget UWBP_EOM_SettingsMaster_C
---@param Values_to_Toggle_Setting_Activation TArray<int32>
---@param New_Activation_State boolean
function UWBP_EOM_SettingsMaster_C:AddActivationCondition(ControllerWidget, Values_to_Toggle_Setting_Activation, New_Activation_State) end
---@param ParentCondition UWBP_EOM_SettingsMaster_C
---@param NewState boolean
function UWBP_EOM_SettingsMaster_C:UpdateSettingActivation(ParentCondition, NewState) end
function UWBP_EOM_SettingsMaster_C:ControlSettingsActivationOnConditions() end
---@param IntValue int32
function UWBP_EOM_SettingsMaster_C:SetCurrentValueAsInt(IntValue) end
---@param IntValue int32
function UWBP_EOM_SettingsMaster_C:GetCurrentValueAsInt(IntValue) end
function UWBP_EOM_SettingsMaster_C:ApplySetting() end
---@param IsDirty_ boolean
function UWBP_EOM_SettingsMaster_C:SetSettingDirty(IsDirty_) end
function UWBP_EOM_SettingsMaster_C:ResetToDefault() end
---@param InFocusEvent FFocusEvent
function UWBP_EOM_SettingsMaster_C:OnAddedToFocusPath(InFocusEvent) end
---@param InFocusEvent FFocusEvent
function UWBP_EOM_SettingsMaster_C:OnRemovedFromFocusPath(InFocusEvent) end
---@param NextValue_ boolean
function UWBP_EOM_SettingsMaster_C:SettingUpdateValue(NextValue_) end
---@param IsDesignTime boolean
function UWBP_EOM_SettingsMaster_C:PreConstruct(IsDesignTime) end
---@param SelfIndex int32
function UWBP_EOM_SettingsMaster_C:BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EOM_SettingsMaster_C:BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_1_ButtonFocused__DelegateSignature(SelfIndex) end
function UWBP_EOM_SettingsMaster_C:BndEvt__WBP_EOM_SettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_4_ButtonUnfocused__DelegateSignature() end
function UWBP_EOM_SettingsMaster_C:MouseButtonDownEvent() end
---@param MouseEvent FPointerEvent
function UWBP_EOM_SettingsMaster_C:OnMouseLeave(MouseEvent) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
function UWBP_EOM_SettingsMaster_C:OnMouseEnter(MyGeometry, MouseEvent) end
function UWBP_EOM_SettingsMaster_C:Construct() end
---@param EntryPoint int32
function UWBP_EOM_SettingsMaster_C:ExecuteUbergraph_WBP_EOM_SettingsMaster(EntryPoint) end


