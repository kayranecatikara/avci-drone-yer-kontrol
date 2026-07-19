---@meta

---@class UWBP_EasyOptionsMenuMain_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field AAMethodSetting UWBP_EOM_SettingSelector_C
---@field AAQualitySetting UWBP_EOM_SettingSelector_C
---@field AmbientAudioSetting UWBP_EOM_SettingProgressBar_C
---@field ApplyBtn UWBP_EGUI_CommonButton_C
---@field ApplyBtnInput UWBP_EasyInputPromptDisplayer_C
---@field AudioDeviceSetting UWBP_EOM_SettingSelector_C
---@field BackBtn UWBP_EGUI_CommonButton_C
---@field BackgroundImage UWBP_EGUI_CommonBackgroundImage_C
---@field BenchmarkBtn UWBP_EGUI_CommonButton_C
---@field BenchmarkFooter UHorizontalBox
---@field CameraFOVSetting UWBP_EOM_SettingProgressBar_C
---@field CameraSensivitySetting UWBP_EOM_SettingProgressBar_C
---@field ColorBlindnessCorrectionIntensitySetting UWBP_EOM_SettingProgressBar_C
---@field ColorBlindnessTypeSetting UWBP_EOM_SettingSelector_C
---@field ContactShadowsSetting UWBP_EOM_SettingToggle_C
---@field ControlsOptionsContainer UVerticalBox
---@field EffectsAudioSetting UWBP_EOM_SettingProgressBar_C
---@field EffectsSetting UWBP_EOM_SettingSelector_C
---@field FoliageSetting UWBP_EOM_SettingSelector_C
---@field FramerateCounterSetting UWBP_EOM_SettingToggle_C
---@field FramerateLimitSetting UWBP_EOM_SettingProgressBar_C
---@field GamepadBrandSetting UWBP_EOM_SettingSelector_C
---@field GamepadCameraSensivitySetting UWBP_EOM_SettingProgressBar_C
---@field GammaSetting UWBP_EOM_SettingProgressBar_C
---@field GlobalIlluminationSetting UWBP_EOM_SettingSelector_C
---@field GraphicsPresetSetting UWBP_EOM_SettingSelector_C
---@field HardwareLumenSetting UWBP_EOM_SettingToggle_C
---@field HeaderBtns UWBP_EGUI_CommonHeader_C
---@field HudScaleSetting UWBP_EOM_SettingProgressBar_C
---@field InvertXAxisSetting UWBP_EOM_SettingToggle_C
---@field InvertYAxisSetting UWBP_EOM_SettingToggle_C
---@field LanguageSetting UWBP_EOM_SettingSelector_C
---@field MasterAudioSetting UWBP_EOM_SettingProgressBar_C
---@field MotionBlurSetting UWBP_EOM_SettingSelector_C
---@field MusicAudioSetting UWBP_EOM_SettingProgressBar_C
---@field OptionsPanelSwitcher UWidgetSwitcher
---@field PostProcessSetting UWBP_EOM_SettingSelector_C
---@field ReflectionsSetting UWBP_EOM_SettingSelector_C
---@field ResetBtn UWBP_EGUI_CommonButton_C
---@field ResolutionScaleSetting UWBP_EOM_SettingProgressBar_C
---@field ResolutionSetting UWBP_EOM_SettingSelector_C
---@field RunBenchmarkButton UWBP_EOM_SettingSimpleButton_C
---@field SettingDescription UWBP_EGUI_OptionDescription_C
---@field ShadingSetting UWBP_EOM_SettingSelector_C
---@field ShadowsSetting UWBP_EOM_SettingSelector_C
---@field TexturesFilteringSetting UWBP_EOM_SettingSelector_C
---@field TexturesSetting UWBP_EOM_SettingSelector_C
---@field UIAudioSetting UWBP_EOM_SettingProgressBar_C
---@field UpscaleMethodSetting UWBP_EOM_SettingSelector_C
---@field UpscaleQualitySetting UWBP_EOM_SettingSelector_C
---@field UpscaleSharpnessSetting UWBP_EOM_SettingProgressBar_C
---@field ViewDistanceSetting UWBP_EOM_SettingSelector_C
---@field VolumetricsSetting UWBP_EOM_SettingSelector_C
---@field VSMShadowsSetting UWBP_EOM_SettingToggle_C
---@field VSyncSetting UWBP_EOM_SettingSelector_C
---@field WindowModeSetting UWBP_EOM_SettingSelector_C
---@field ApplySettings FWBP_EasyOptionsMenuMain_CApplySettings
---@field ResetSettings FWBP_EasyOptionsMenuMain_CResetSettings
---@field OptionsMenuClosed FWBP_EasyOptionsMenuMain_COptionsMenuClosed
---@field ['SettingsDirty?'] boolean
---@field FocusedSetting UWBP_EOM_SettingsMaster_C
---@field ActivePanelWidget UPanelWidget
---@field ResetTooltip UWBP_EGUI_CommonTooltip_C
---@field PlayerControllerRef APlayerController
---@field HUD AHUD
---@field SettingsJsonFile FJsonObjectWrapper
---@field ResolutionList TArray<FVector2D>
---@field StaticResolutions TArray<FIntPoint>
---@field ['RequestedAA Method'] E_AntiAliasingMethods::Type
---@field RequestedUpscalingMethod E_UpscalingMethods::Type
---@field GraphicsPresets TArray<FS_GraphicsPresetsInfos>
---@field AudioVolumes TMap<E_AudioClasses::Type, double>
---@field MappingContexts TMap<UInputMappingContext, FText>
---@field MappingsGroupingType E_MappingsGroupingType::Type
---@field KeyMapsWidgetsRefs TMap<FString, UWBP_EOM_SettingKeybinding_C>
---@field MappingsCategories TMap<FString, FS_KeyMapCategoryGroupingInfos>
---@field MappingsCategoriesTitles TMap<FString, FText>
---@field LastFocusedSettingForContainer TMap<UPanelWidget, UWBP_EOM_SettingsMaster_C>
---@field ['CanUpdateDescription?'] boolean
---@field PreviousGraphicPreset int32
---@field ['ResolutionDirty?'] boolean
---@field BaseWindowMode int32
---@field BaseResolution int32
---@field CurrentAudioDeviceIndex int32
---@field CurrentAudioDevice FString
---@field ['Use Dedicated Input for Game Benchmark?'] boolean
---@field InputUserSettings UEnhancedInputUserSettings
---@field ['Keybindings History?'] boolean
local UWBP_EasyOptionsMenuMain_C = {}

---@param AvailableDevices TArray<FAudioOutputDeviceInfo>
function UWBP_EasyOptionsMenuMain_C:InitAudioOutputDeviceSetting(AvailableDevices) end
function UWBP_EasyOptionsMenuMain_C:SaveKeybindings() end
function UWBP_EasyOptionsMenuMain_C:RetrieveUserSettings() end
---@param Hide_ boolean
---@param SettingRef UWBP_EOM_SettingsMaster_C
function UWBP_EasyOptionsMenuMain_C:ShowOrHideResetTooltip(Hide_, SettingRef) end
---@param MappingContext UInputMappingContext
function UWBP_EasyOptionsMenuMain_C:CreateKeybindingWidgets(MappingContext) end
---@param MappingContext UInputMappingContext
---@param KeyToCheck FKey
---@param InstigatorMapping FName
---@param Forbidden_ boolean
---@param Conflict_ boolean
---@param ConflictedMappingName FName
---@param ConflictedMappingDisplayName FText
---@param ConflictedMappingWidget UWBP_EOM_SettingKeybinding_C
function UWBP_EasyOptionsMenuMain_C:CheckInputConflict(MappingContext, KeyToCheck, InstigatorMapping, Forbidden_, Conflict_, ConflictedMappingName, ConflictedMappingDisplayName, ConflictedMappingWidget) end
function UWBP_EasyOptionsMenuMain_C:UpdateGraphicPresetValue() end
---@param NewPreset int32
function UWBP_EasyOptionsMenuMain_C:SetCurrentGraphicPreset(NewPreset) end
---@param Container UPanelWidget
function UWBP_EasyOptionsMenuMain_C:SetFocusToFirstWidget(Container) end
---@param Navigation EUINavigation
---@return UWidget
function UWBP_EasyOptionsMenuMain_C:OverrideNavigation(Navigation) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EasyOptionsMenuMain_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param PresetValue int32
function UWBP_EasyOptionsMenuMain_C:GetCurrentGraphicPreset(PresetValue) end
---@param NewVolume double
---@param AudioClass E_AudioClasses::Type
function UWBP_EasyOptionsMenuMain_C:UpdateAudioVolume(NewVolume, AudioClass) end
---@param CurrentResolutionIndex int32
function UWBP_EasyOptionsMenuMain_C:GetAllAvailableResolutions(CurrentResolutionIndex) end
function UWBP_EasyOptionsMenuMain_C:UpdateApplyBtnVisibility() end
---@return UGameUserSettings
function UWBP_EasyOptionsMenuMain_C:GetUserSettings() end
---@param OptionTitle FText
---@param OptionDescription FText
---@param ImageToDisplay TSoftObjectPtr<UTexture2D>
---@param ForceUpdate_ boolean
---@param KeybindingsHistory_ boolean
function UWBP_EasyOptionsMenuMain_C:UpdateSettingDescription(OptionTitle, OptionDescription, ImageToDisplay, ForceUpdate_, KeybindingsHistory_) end
function UWBP_EasyOptionsMenuMain_C:Construct() end
---@param SettingRef UWBP_EOM_SettingsMaster_C
function UWBP_EasyOptionsMenuMain_C:NewlyFocusedSetting(SettingRef) end
---@param LastActiveTab int32
function UWBP_EasyOptionsMenuMain_C:OptionsMenuClosedEvent(LastActiveTab) end
---@param SelfIndex int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_BenchmarkBtn_K2Node_ComponentBoundEvent_5_ButtonClicked__DelegateSignature(SelfIndex) end
---@param TabIndex int32
function UWBP_EasyOptionsMenuMain_C:SelectInitialOptionsMenuTab(TabIndex) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_GlobalIlluminationSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_MaxResolutionScaleSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_VSyncSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_FramerateLimitSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_TexturesSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ViewDistanceSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ShadowsSetting_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_PostProcessSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_AAQualitySetting_K2Node_ComponentBoundEvent_11_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ReflectionsSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_WindowModeSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_GammaSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ResolutionSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_FoliageSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_GraphicsPresetSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_AAMethodSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_UpscaleQualitySetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_EffectsSetting_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_MotionBlurSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EasyOptionsMenuMain_C:NewInputActionTriggered(InputType, ActionValue) end
---@param NewValue boolean
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_HardwareLumenSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param Key FKey
function UWBP_EasyOptionsMenuMain_C:AnyKeyPressed(Key) end
---@param NewValue boolean
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_VSMShadowsSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_VolumetricsSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ShadingSetting_K2Node_ComponentBoundEvent_9_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_MasterAudioSetting_K2Node_ComponentBoundEvent_12_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_UIAudioSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_MusicAudioSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_EffectsAudioSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_AmbientAudioSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_UpscaleMethodSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param NewValue boolean
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ContactShadowsSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_TexturesFiltertingSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param SelfIndex int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ApplyBtn_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_BackBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_HeaderBtns_K2Node_ComponentBoundEvent_4_NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end
---@param SelfIndex int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ResetBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_UpscaleSharpnessSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_LanguageSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ButtonIndex int32
function UWBP_EasyOptionsMenuMain_C:ResolutionConfirmationAction(ButtonIndex) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_CameraFOVSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ColorBlindnessCorrectionIntensitySetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(NewValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_ColorBlindnessTypeSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_GamepadBrandSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
---@param ButtonIndex int32
function UWBP_EasyOptionsMenuMain_C:RunBenchmarkAction(ButtonIndex) end
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_RunBenchmarkButton_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature() end
---@param ButtonIndex int32
function UWBP_EasyOptionsMenuMain_C:UnsavedSettingsAction(ButtonIndex) end
---@param CurrentDevice FString
function UWBP_EasyOptionsMenuMain_C:GetCurrentAudioDevice(CurrentDevice) end
---@param SwapResult FSwapAudioOutputResult
function UWBP_EasyOptionsMenuMain_C:AudioDeviceSwapped(SwapResult) end
---@param ValueIndex int32
---@param ValueDisplayName FText
---@param CultureInvariantValue FString
---@param IncrementedOutputValue int32
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_AudioDeviceSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(ValueIndex, ValueDisplayName, CultureInvariantValue, IncrementedOutputValue) end
function UWBP_EasyOptionsMenuMain_C:CloseOptionsMenu() end
---@param NewValue double
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_WBP_EOM_SettingProgressBar_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param ButtonIndex int32
function UWBP_EasyOptionsMenuMain_C:ResetSettingsAction(ButtonIndex) end
---@param NewValue boolean
function UWBP_EasyOptionsMenuMain_C:BndEvt__WBP_EasyOptionsMenuMain_FramerateCounterSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(NewValue) end
---@param EntryPoint int32
function UWBP_EasyOptionsMenuMain_C:ExecuteUbergraph_WBP_EasyOptionsMenuMain(EntryPoint) end
function UWBP_EasyOptionsMenuMain_C:OptionsMenuClosed__DelegateSignature() end
function UWBP_EasyOptionsMenuMain_C:ResetSettings__DelegateSignature() end
function UWBP_EasyOptionsMenuMain_C:ApplySettings__DelegateSignature() end


