---@meta

---@class UWBP_EOM_SettingKeybinding_C : UWBP_EOM_SettingsMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field GamepadKey UInputKeySelector
---@field GamepadKeyDisplayer UWBP_EasyInputPromptDisplayer_C
---@field GamepadKeyOverlay UOverlay
---@field KeyboardKey UInputKeySelector
---@field KeyboardKeyDisplayer UWBP_EasyInputPromptDisplayer_C
---@field KeyboardKeyOverlay UOverlay
---@field KeySelectorNormalStyle FSlateBrush
---@field KeySelectorActiveStyle FSlateBrush
---@field SelectionUpdated boolean
---@field KeyboardMapping FS_KeyMappingInfos
---@field GamepadMapping FS_KeyMappingInfos
---@field MappingContext UInputMappingContext
---@field UserSettings UEnhancedInputUserSettings
local UWBP_EOM_SettingKeybinding_C = {}

---@param UserId FPlatformUserId
---@param DeviceID FInputDeviceId
function UWBP_EOM_SettingKeybinding_C:UpdateKeySelectorFocus(UserId, DeviceID) end
---@param MyGeometry FGeometry
---@param InFocusEvent FFocusEvent
---@return FEventReply
function UWBP_EOM_SettingKeybinding_C:OnFocusReceived(MyGeometry, InFocusEvent) end
---@param NewKeyMapping FS_KeyMappingInfos
function UWBP_EOM_SettingKeybinding_C:RefreshKeyMappingsValues(NewKeyMapping) end
function UWBP_EOM_SettingKeybinding_C:SetAdditionalDescription() end
---@param DefaultValue FText
function UWBP_EOM_SettingKeybinding_C:GetDefaultValueAsText(DefaultValue) end
---@param KeySelectorRef UInputKeySelector
---@param KeyDisplayerRef UWidget
function UWBP_EOM_SettingKeybinding_C:UpdateInputPromptVisibility(KeySelectorRef, KeyDisplayerRef) end
---@param NewKey FKey
---@param KeyMapping FS_KeyMappingInfos
function UWBP_EOM_SettingKeybinding_C:TryToRemapKeybindWithNewKey(NewKey, KeyMapping) end
---@param NewKeyMapping FS_KeyMappingInfos
UWBP_EOM_SettingKeybinding_C['Remap Key'] = function(self, NewKeyMapping) end
function UWBP_EOM_SettingKeybinding_C:ResetToDefault() end
function UWBP_EOM_SettingKeybinding_C:UpdateKeySelectorStyle() end
function UWBP_EOM_SettingKeybinding_C:InitValue() end
function UWBP_EOM_SettingKeybinding_C:UpdateKeymapDisplayersInfos() end
---@param SelectedKey FInputChord
function UWBP_EOM_SettingKeybinding_C:BndEvt__W_SettingKeybinding_KeyboardKey_K2Node_ComponentBoundEvent_0_OnKeySelected__DelegateSignature(SelectedKey) end
---@param SelectedKey FInputChord
function UWBP_EOM_SettingKeybinding_C:BndEvt__W_SettingKeybinding_GamepadKey_K2Node_ComponentBoundEvent_1_OnKeySelected__DelegateSignature(SelectedKey) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
function UWBP_EOM_SettingKeybinding_C:OnMouseEnter(MyGeometry, MouseEvent) end
---@param InFocusEvent FFocusEvent
function UWBP_EOM_SettingKeybinding_C:OnAddedToFocusPath(InFocusEvent) end
function UWBP_EOM_SettingKeybinding_C:Construct() end
function UWBP_EOM_SettingKeybinding_C:BndEvt__WBP_EOM_SettingKeybind_GamepadKey_K2Node_ComponentBoundEvent_4_OnIsSelectingKeyChanged__DelegateSignature() end
---@param IsDesignTime boolean
function UWBP_EOM_SettingKeybinding_C:PreConstruct(IsDesignTime) end
function UWBP_EOM_SettingKeybinding_C:MouseButtonDownEvent() end
---@param InFocusEvent FFocusEvent
function UWBP_EOM_SettingKeybinding_C:OnRemovedFromFocusPath(InFocusEvent) end
---@param MouseEvent FPointerEvent
function UWBP_EOM_SettingKeybinding_C:OnMouseLeave(MouseEvent) end
function UWBP_EOM_SettingKeybinding_C:BndEvt__WBP_EOM_SettingKeybind_KeyboardKey_K2Node_ComponentBoundEvent_3_OnIsSelectingKeyChanged__DelegateSignature() end
---@param EntryPoint int32
function UWBP_EOM_SettingKeybinding_C:ExecuteUbergraph_WBP_EOM_SettingKeybinding(EntryPoint) end


