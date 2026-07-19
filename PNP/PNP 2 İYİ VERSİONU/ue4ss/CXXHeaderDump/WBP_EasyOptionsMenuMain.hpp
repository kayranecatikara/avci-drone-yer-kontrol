#ifndef UE4SS_SDK_WBP_EasyOptionsMenuMain_HPP
#define UE4SS_SDK_WBP_EasyOptionsMenuMain_HPP

class UWBP_EasyOptionsMenuMain_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* AAMethodSetting;                                // 0x02D8 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* AAQualitySetting;                               // 0x02E0 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* AmbientAudioSetting;                         // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ApplyBtn;                                         // 0x02F0 (size: 0x8)
    class UWBP_EasyInputPromptDisplayer_C* ApplyBtnInput;                             // 0x02F8 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* AudioDeviceSetting;                             // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* BackBtn;                                          // 0x0308 (size: 0x8)
    class UWBP_EGUI_CommonBackgroundImage_C* BackgroundImage;                         // 0x0310 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* BenchmarkBtn;                                     // 0x0318 (size: 0x8)
    class UHorizontalBox* BenchmarkFooter;                                            // 0x0320 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* CameraFOVSetting;                            // 0x0328 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* CameraSensivitySetting;                      // 0x0330 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* ColorBlindnessCorrectionIntensitySetting;    // 0x0338 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ColorBlindnessTypeSetting;                      // 0x0340 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* ContactShadowsSetting;                            // 0x0348 (size: 0x8)
    class UVerticalBox* ControlsOptionsContainer;                                     // 0x0350 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* EffectsAudioSetting;                         // 0x0358 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* EffectsSetting;                                 // 0x0360 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* FoliageSetting;                                 // 0x0368 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* FramerateCounterSetting;                          // 0x0370 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* FramerateLimitSetting;                       // 0x0378 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* GamepadBrandSetting;                            // 0x0380 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* GamepadCameraSensivitySetting;               // 0x0388 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* GammaSetting;                                // 0x0390 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* GlobalIlluminationSetting;                      // 0x0398 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* GraphicsPresetSetting;                          // 0x03A0 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* HardwareLumenSetting;                             // 0x03A8 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* HeaderBtns;                                       // 0x03B0 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* HudScaleSetting;                             // 0x03B8 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* InvertXAxisSetting;                               // 0x03C0 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* InvertYAxisSetting;                               // 0x03C8 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* LanguageSetting;                                // 0x03D0 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* MasterAudioSetting;                          // 0x03D8 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* MotionBlurSetting;                              // 0x03E0 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* MusicAudioSetting;                           // 0x03E8 (size: 0x8)
    class UWidgetSwitcher* OptionsPanelSwitcher;                                      // 0x03F0 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* PostProcessSetting;                             // 0x03F8 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ReflectionsSetting;                             // 0x0400 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* ResetBtn;                                         // 0x0408 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* ResolutionScaleSetting;                      // 0x0410 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ResolutionSetting;                              // 0x0418 (size: 0x8)
    class UWBP_EOM_SettingSimpleButton_C* RunBenchmarkButton;                         // 0x0420 (size: 0x8)
    class UWBP_EGUI_OptionDescription_C* SettingDescription;                          // 0x0428 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ShadingSetting;                                 // 0x0430 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ShadowsSetting;                                 // 0x0438 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* TexturesFilteringSetting;                       // 0x0440 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* TexturesSetting;                                // 0x0448 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* UIAudioSetting;                              // 0x0450 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* UpscaleMethodSetting;                           // 0x0458 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* UpscaleQualitySetting;                          // 0x0460 (size: 0x8)
    class UWBP_EOM_SettingProgressBar_C* UpscaleSharpnessSetting;                     // 0x0468 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* ViewDistanceSetting;                            // 0x0470 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* VolumetricsSetting;                             // 0x0478 (size: 0x8)
    class UWBP_EOM_SettingToggle_C* VSMShadowsSetting;                                // 0x0480 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* VSyncSetting;                                   // 0x0488 (size: 0x8)
    class UWBP_EOM_SettingSelector_C* WindowModeSetting;                              // 0x0490 (size: 0x8)
    FWBP_EasyOptionsMenuMain_CApplySettings ApplySettings;                            // 0x0498 (size: 0x10)
    void ApplySettings();
    FWBP_EasyOptionsMenuMain_CResetSettings ResetSettings;                            // 0x04A8 (size: 0x10)
    void ResetSettings();
    FWBP_EasyOptionsMenuMain_COptionsMenuClosed OptionsMenuClosed;                    // 0x04B8 (size: 0x10)
    void OptionsMenuClosed();
    bool SettingsDirty?;                                                              // 0x04C8 (size: 0x1)
    class UWBP_EOM_SettingsMaster_C* FocusedSetting;                                  // 0x04D0 (size: 0x8)
    class UPanelWidget* ActivePanelWidget;                                            // 0x04D8 (size: 0x8)
    class UWBP_EGUI_CommonTooltip_C* ResetTooltip;                                    // 0x04E0 (size: 0x8)
    class APlayerController* PlayerControllerRef;                                     // 0x04E8 (size: 0x8)
    class AHUD* HUD;                                                                  // 0x04F0 (size: 0x8)
    FJsonObjectWrapper SettingsJsonFile;                                              // 0x04F8 (size: 0x20)
    TArray<FVector2D> ResolutionList;                                                 // 0x0518 (size: 0x10)
    TArray<FIntPoint> StaticResolutions;                                              // 0x0528 (size: 0x10)
    TEnumAsByte<E_AntiAliasingMethods::Type> RequestedAA Method;                      // 0x0538 (size: 0x1)
    TEnumAsByte<E_UpscalingMethods::Type> RequestedUpscalingMethod;                   // 0x0539 (size: 0x1)
    TArray<FS_GraphicsPresetsInfos> GraphicsPresets;                                  // 0x0540 (size: 0x10)
    TMap<TEnumAsByte<E_AudioClasses::Type>, double> AudioVolumes;                     // 0x0550 (size: 0x50)
    TMap<class UInputMappingContext*, class FText> MappingContexts;                   // 0x05A0 (size: 0x50)
    TEnumAsByte<E_MappingsGroupingType::Type> MappingsGroupingType;                   // 0x05F0 (size: 0x1)
    TMap<class FString, class UWBP_EOM_SettingKeybinding_C*> KeyMapsWidgetsRefs;      // 0x05F8 (size: 0x50)
    TMap<class FString, class FS_KeyMapCategoryGroupingInfos> MappingsCategories;     // 0x0648 (size: 0x50)
    TMap<class FString, class FText> MappingsCategoriesTitles;                        // 0x0698 (size: 0x50)
    TMap<class UPanelWidget*, class UWBP_EOM_SettingsMaster_C*> LastFocusedSettingForContainer; // 0x06E8 (size: 0x50)
    bool CanUpdateDescription?;                                                       // 0x0738 (size: 0x1)
    int32 PreviousGraphicPreset;                                                      // 0x073C (size: 0x4)
    bool ResolutionDirty?;                                                            // 0x0740 (size: 0x1)
    int32 BaseWindowMode;                                                             // 0x0744 (size: 0x4)
    int32 BaseResolution;                                                             // 0x0748 (size: 0x4)
    int32 CurrentAudioDeviceIndex;                                                    // 0x074C (size: 0x4)
    FString CurrentAudioDevice;                                                       // 0x0750 (size: 0x10)
    bool Use Dedicated Input for Game Benchmark?;                                     // 0x0760 (size: 0x1)
    class UEnhancedInputUserSettings* InputUserSettings;                              // 0x0768 (size: 0x8)
    bool Keybindings History?;                                                        // 0x0770 (size: 0x1)

    void InitAudioOutputDeviceSetting(const TArray<FAudioOutputDeviceInfo>& AvailableDevices);
    void SaveKeybindings();
    void RetrieveUserSettings();
    void ShowOrHideResetTooltip(bool Hide?, class UWBP_EOM_SettingsMaster_C* SettingRef);
    void CreateKeybindingWidgets(class UInputMappingContext* MappingContext);
    void CheckInputConflict(class UInputMappingContext* MappingContext, FKey KeyToCheck, const FName InstigatorMapping, bool& Forbidden?, bool& Conflict?, FName& ConflictedMappingName, FText& ConflictedMappingDisplayName, class UWBP_EOM_SettingKeybinding_C*& ConflictedMappingWidget);
    void UpdateGraphicPresetValue();
    void SetCurrentGraphicPreset(int32 NewPreset);
    void SetFocusToFirstWidget(class UPanelWidget*& Container);
    class UWidget* OverrideNavigation(EUINavigation Navigation);
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void GetCurrentGraphicPreset(int32& PresetValue);
    void UpdateAudioVolume(double NewVolume, TEnumAsByte<E_AudioClasses::Type> AudioClass);
    void GetAllAvailableResolutions(int32& CurrentResolutionIndex);
    void UpdateApplyBtnVisibility();
    class UGameUserSettings* GetUserSettings();
    void UpdateSettingDescription(FText OptionTitle, FText OptionDescription, TSoftObjectPtr<UTexture2D> ImageToDisplay, bool ForceUpdate?, bool KeybindingsHistory?);
    void Construct();
    void NewlyFocusedSetting(class UWBP_EOM_SettingsMaster_C* SettingRef);
    void OptionsMenuClosedEvent(int32 LastActiveTab);
    void BndEvt__WBP_EasyOptionsMenuMain_BenchmarkBtn_K2Node_ComponentBoundEvent_5_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void SelectInitialOptionsMenuTab(int32 TabIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_GlobalIlluminationSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_MaxResolutionScaleSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_VSyncSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_FramerateLimitSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_TexturesSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ViewDistanceSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ShadowsSetting_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_PostProcessSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_AAQualitySetting_K2Node_ComponentBoundEvent_11_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ReflectionsSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_WindowModeSetting_K2Node_ComponentBoundEvent_4_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_GammaSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ResolutionSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_FoliageSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_GraphicsPresetSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_AAMethodSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_UpscaleQualitySetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_EffectsSetting_K2Node_ComponentBoundEvent_7_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_MotionBlurSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void BndEvt__WBP_EasyOptionsMenuMain_HardwareLumenSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(bool NewValue);
    void AnyKeyPressed(FKey Key);
    void BndEvt__WBP_EasyOptionsMenuMain_VSMShadowsSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(bool NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_VolumetricsSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ShadingSetting_K2Node_ComponentBoundEvent_9_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_MasterAudioSetting_K2Node_ComponentBoundEvent_12_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_UIAudioSetting_K2Node_ComponentBoundEvent_8_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_MusicAudioSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_EffectsAudioSetting_K2Node_ComponentBoundEvent_10_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_AmbientAudioSetting_K2Node_ComponentBoundEvent_6_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_UpscaleMethodSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ContactShadowsSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(bool NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_TexturesFiltertingSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ApplyBtn_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_BackBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_HeaderBtns_K2Node_ComponentBoundEvent_4_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void BndEvt__WBP_EasyOptionsMenuMain_ResetBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_UpscaleSharpnessSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_LanguageSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void ResolutionConfirmationAction(int32 ButtonIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_CameraFOVSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ColorBlindnessCorrectionIntensitySetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(double NewValue);
    void BndEvt__WBP_EasyOptionsMenuMain_ColorBlindnessTypeSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void BndEvt__WBP_EasyOptionsMenuMain_GamepadBrandSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void RunBenchmarkAction(int32 ButtonIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_RunBenchmarkButton_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature();
    void UnsavedSettingsAction(int32 ButtonIndex);
    void GetCurrentAudioDevice(FString CurrentDevice);
    void AudioDeviceSwapped(const FSwapAudioOutputResult& SwapResult);
    void BndEvt__WBP_EasyOptionsMenuMain_AudioDeviceSetting_K2Node_ComponentBoundEvent_5_SettingUpdated__DelegateSignature(int32 ValueIndex, FText ValueDisplayName, FString CultureInvariantValue, int32 IncrementedOutputValue);
    void CloseOptionsMenu();
    void BndEvt__WBP_EasyOptionsMenuMain_WBP_EOM_SettingProgressBar_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(double NewValue);
    void ResetSettingsAction(int32 ButtonIndex);
    void BndEvt__WBP_EasyOptionsMenuMain_FramerateCounterSetting_K2Node_ComponentBoundEvent_3_SettingUpdated__DelegateSignature(bool NewValue);
    void ExecuteUbergraph_WBP_EasyOptionsMenuMain(int32 EntryPoint);
    void OptionsMenuClosed__DelegateSignature();
    void ResetSettings__DelegateSignature();
    void ApplySettings__DelegateSignature();
}; // Size: 0x771

#endif
