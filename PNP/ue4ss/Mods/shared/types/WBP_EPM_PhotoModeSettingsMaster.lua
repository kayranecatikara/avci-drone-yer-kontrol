---@meta

---@class UWBP_EPM_PhotoModeSettingsMaster_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UWBP_EGUI_CommonBackground_C
---@field NamedSlot UNamedSlot
---@field ResetSetting UWBP_EGUI_CommonButton_C
---@field SettingName UWBP_EGUI_CommonText_C
---@field SizeBox USizeBox
---@field EasyPhotoModeRef UWBP_EasyPhotoMode_C
---@field OptionTitle FText
---@field ['UseStylingLocalOverride?'] boolean
---@field OptionTitleTextStyling FS_CommonTextInfo
---@field OptionValueTextStyling FS_CommonTextInfo
---@field SizeBoxHeight float
---@field OptionDescription FText
local UWBP_EPM_PhotoModeSettingsMaster_C = {}

---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EPM_PhotoModeSettingsMaster_C:OnMouseButtonDown(MyGeometry, MouseEvent) end
function UWBP_EPM_PhotoModeSettingsMaster_C:ResetToDefault() end
---@param InFocusEvent FFocusEvent
function UWBP_EPM_PhotoModeSettingsMaster_C:OnAddedToFocusPath(InFocusEvent) end
---@param InFocusEvent FFocusEvent
function UWBP_EPM_PhotoModeSettingsMaster_C:OnRemovedFromFocusPath(InFocusEvent) end
---@param NextValue_ boolean
function UWBP_EPM_PhotoModeSettingsMaster_C:SettingUpdateValue(NextValue_) end
---@param IsDesignTime boolean
function UWBP_EPM_PhotoModeSettingsMaster_C:PreConstruct(IsDesignTime) end
---@param SelfIndex int32
function UWBP_EPM_PhotoModeSettingsMaster_C:BndEvt__WBP_EPM_PhotoModeSettingsMaster_ResetSetting_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param MouseEvent FPointerEvent
function UWBP_EPM_PhotoModeSettingsMaster_C:OnMouseLeave(MouseEvent) end
function UWBP_EPM_PhotoModeSettingsMaster_C:MouseButtonDownEvent() end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
function UWBP_EPM_PhotoModeSettingsMaster_C:OnMouseEnter(MyGeometry, MouseEvent) end
function UWBP_EPM_PhotoModeSettingsMaster_C:Construct() end
---@param EntryPoint int32
function UWBP_EPM_PhotoModeSettingsMaster_C:ExecuteUbergraph_WBP_EPM_PhotoModeSettingsMaster(EntryPoint) end


