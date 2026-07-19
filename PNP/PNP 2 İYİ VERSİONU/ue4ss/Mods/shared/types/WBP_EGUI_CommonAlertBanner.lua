---@meta

---@class UWBP_EGUI_CommonAlertBanner_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ButtonContainer UHorizontalBox
---@field Divider UBorder
---@field OptionDescription UWBP_EGUI_CommonText_C
---@field AlertBannerSetupInfos FS_AlertBannerSetupInfos
---@field DescriptionTextStyling FS_CommonTextInfo
---@field ButtonTextStyling FS_CommonTextInfo
---@field ButtonTextPadding FMargin
---@field ActionRequested FWBP_EGUI_CommonAlertBanner_CActionRequested
---@field ButtonToExecuteAfterDelay UWBP_EGUI_CommonButton_C
---@field ActionDescription FText
---@field OptionsButtons TArray<FText>
---@field ButtonsSizeRule ESlateSizeRule::Type
---@field DelayBeforeAutomaticAction int32
---@field ActionToExecuteAfterDelay int32
---@field ['DelayCompleted?'] boolean
---@field ['AllowBackInputToTriggerAction?'] boolean
---@field ActionToExecuteOnBackInputFired int32
---@field HUD AHUD
local UWBP_EGUI_CommonAlertBanner_C = {}

---@param AlertBannerSetupInfos FS_AlertBannerSetupInfos
---@param ButtonToFocus UWidget
function UWBP_EGUI_CommonAlertBanner_C:SetupWidget(AlertBannerSetupInfos, ButtonToFocus) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EGUI_CommonAlertBanner_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param ButtonTitle FText
---@param CurrentIndex int32
function UWBP_EGUI_CommonAlertBanner_C:CreateNewButton(ButtonTitle, CurrentIndex) end
---@param SelfIndex int32
function UWBP_EGUI_CommonAlertBanner_C:ButtonClicked(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonAlertBanner_C:PreConstruct(IsDesignTime) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EGUI_CommonAlertBanner_C:NewInputActionTriggered(InputType, ActionValue) end
function UWBP_EGUI_CommonAlertBanner_C:InitDelayBeforeAutomaticAction() end
---@param Key FKey
function UWBP_EGUI_CommonAlertBanner_C:AnyKeyPressed(Key) end
function UWBP_EGUI_CommonAlertBanner_C:NextCountdown() end
---@param EntryPoint int32
function UWBP_EGUI_CommonAlertBanner_C:ExecuteUbergraph_WBP_EGUI_CommonAlertBanner(EntryPoint) end
---@param ButtonIndex int32
function UWBP_EGUI_CommonAlertBanner_C:ActionRequested__DelegateSignature(ButtonIndex) end


