---@meta

---@class UWBP_EasyPhotoMode_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ApertureSetting UWBP_EPM_SettingProgressBar_C
---@field BrightnessSetting UWBP_EPM_SettingProgressBar_C
---@field CameraRollSetting UWBP_EPM_SettingProgressBar_C
---@field ChromaticAberrationIntensity UWBP_EPM_SettingProgressBar_C
---@field ChromaticAberrationStartOffset UWBP_EPM_SettingProgressBar_C
---@field ColorTempSetting UWBP_EPM_SettingProgressBar_C
---@field ColorTintSetting UWBP_EPM_SettingProgressBar_C
---@field ConstrainAspectRatioSetting UWBP_EPM_SettingToggle_C
---@field ContrastSetting UWBP_EPM_SettingProgressBar_C
---@field EditionOptionsHeader UWBP_EGUI_CommonHeader_C
---@field EditionOptionsHeaderNextBtn UWBP_EGUI_CommonButton_C
---@field EditionOptionsHeaderPreviousBtn UWBP_EGUI_CommonButton_C
---@field EditionOptionsSwitcher UWidgetSwitcher
---@field FocalLengthSetting UWBP_EPM_SettingProgressBar_C
---@field FocusDistanceSetting UWBP_EPM_SettingProgressBar_C
---@field GrainSetting UWBP_EPM_SettingProgressBar_C
---@field ModeSwitcher UWidgetSwitcher
---@field OptionDescription UWBP_EGUI_OptionDescription_C
---@field ResolutionMultiplierSetting UWBP_EPM_SettingProgressBar_C
---@field SaturationSetting UWBP_EPM_SettingProgressBar_C
---@field SensorHeightSetting UWBP_EPM_SettingProgressBar_C
---@field SensorWidthSetting UWBP_EPM_SettingProgressBar_C
---@field SharpnessSetting UWBP_EPM_SettingProgressBar_C
---@field TakePhotoBtn UWBP_EGUI_CommonButton_C
---@field VignetteSetting UWBP_EPM_SettingProgressBar_C
---@field PhotoModeController ABP_EPM_PhotoModeController_C
---@field CameraReference UCineCameraComponent
---@field ['EditionModeEnabled?'] boolean
---@field ClosePhotoMode FWBP_EasyPhotoMode_CClosePhotoMode
---@field ['IsUIHidden?'] boolean
---@field FocusedSetting UWBP_EPM_PhotoModeSettingsMaster_C
---@field ActivePanelWidget UPanelWidget
---@field ResetSettings FWBP_EasyPhotoMode_CResetSettings
---@field ResolutionMultiplier double
---@field BaseSharpness float
local UWBP_EasyPhotoMode_C = {}

---@param Value double
function UWBP_EasyPhotoMode_C:SetFocusToDistance(Value) end
---@param Text FText
function UWBP_EasyPhotoMode_C:UpdateDescription(Text) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EasyPhotoMode_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param Navigation EUINavigation
---@return UWidget
function UWBP_EasyPhotoMode_C:OverrideNavigation(Navigation) end
function UWBP_EasyPhotoMode_C:SetFocusToFirstWidget() end
---@param Hide_ boolean
function UWBP_EasyPhotoMode_C:ToggleUIVisibility(Hide_) end
---@param SwitchedToEditionMode_ boolean
function UWBP_EasyPhotoMode_C:SwitchMode(SwitchedToEditionMode_) end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_EditionOptionsHeader_K2Node_ComponentBoundEvent_0_NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end
---@param SelfIndex int32
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_TakePhotoBtn_K2Node_ComponentBoundEvent_21_ButtonClicked__DelegateSignature(SelfIndex) end
---@param FocusedSettingRef UWBP_EPM_PhotoModeSettingsMaster_C
function UWBP_EasyPhotoMode_C:NewlyFocusedSetting(FocusedSettingRef) end
---@param Key FKey
function UWBP_EasyPhotoMode_C:AnyKeyPressed(Key) end
---@param SelfIndex int32
function UWBP_EasyPhotoMode_C:BndEvt__WBP_PhotoMode_EditionOptionsHeaderPreviousBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param PhotoModeController ABP_EPM_PhotoModeController_C
---@param CameraReference UCineCameraComponent
function UWBP_EasyPhotoMode_C:InitPhotoModeWidget(PhotoModeController, CameraReference) end
---@param SelfIndex int32
function UWBP_EasyPhotoMode_C:BndEvt__WBP_PhotoMode_EditionOptionsHeaderNextBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EasyPhotoMode_C:NewInputActionTriggered(InputType, ActionValue) end
---@param ButtonIndex int32
function UWBP_EasyPhotoMode_C:ClosePhotoModeAction(ButtonIndex) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_SensorHeightSetting_K2Node_ComponentBoundEvent_18_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_SensorWidthSetting_K2Node_ComponentBoundEvent_17_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ResolutionMultiplierSetting_K2Node_ComponentBoundEvent_15_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_FocusDistanceSetting_K2Node_ComponentBoundEvent_13_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_FocalLengthSetting_K2Node_ComponentBoundEvent_12_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ConstrainAspectRatioSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_CameraRollSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ApertureSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_SharpnessSetting_K2Node_ComponentBoundEvent_20_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_VignetteSetting_K2Node_ComponentBoundEvent_19_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_SaturationSetting_K2Node_ComponentBoundEvent_16_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_GrainSetting_K2Node_ComponentBoundEvent_14_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ContrastSetting_K2Node_ComponentBoundEvent_11_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ColorTintSetting_K2Node_ComponentBoundEvent_9_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ColorTempSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ChromaticAberrationStartOffset_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_ChromaticAberrationIntensity_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param NewValue double
---@param IsDefaultValue_ boolean
function UWBP_EasyPhotoMode_C:BndEvt__WBP_EasyPhotoMode_BrightnessSetting_K2Node_ComponentBoundEvent_1_SettingUpdated__DelegateSignature(NewValue, IsDefaultValue_) end
---@param EntryPoint int32
function UWBP_EasyPhotoMode_C:ExecuteUbergraph_WBP_EasyPhotoMode(EntryPoint) end
function UWBP_EasyPhotoMode_C:ResetSettings__DelegateSignature() end
function UWBP_EasyPhotoMode_C:ClosePhotoMode__DelegateSignature() end


