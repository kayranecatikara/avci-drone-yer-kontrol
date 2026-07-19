#ifndef UE4SS_SDK_WBP_SettingsMenu_HPP
#define UE4SS_SDK_WBP_SettingsMenu_HPP

class UWBP_SettingsMenu_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* Gate;                                                     // 0x02D8 (size: 0x8)
    class UWBP_SettingsOption_C* AntiAliasingSettingsOption;                          // 0x02E0 (size: 0x8)
    class UBackgroundBlur* BackgroundBlur;                                            // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_APPLY;                                        // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_CONFIRM;                                      // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_MENU;                                         // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_Reset;                                        // 0x0308 (size: 0x8)
    class UEditableText* EditableText_Brightness;                                     // 0x0310 (size: 0x8)
    class UEditableText* EditableText_FOV;                                            // 0x0318 (size: 0x8)
    class UEditableText* EditableText_FOV_1;                                          // 0x0320 (size: 0x8)
    class UEditableText* EditableText_MusicVolumeSlider;                              // 0x0328 (size: 0x8)
    class UEditableText* EditableText_PitchAxisSpeed;                                 // 0x0330 (size: 0x8)
    class UEditableText* EditableText_RCExpo;                                         // 0x0338 (size: 0x8)
    class UEditableText* EditableText_RCExpo_1;                                       // 0x0340 (size: 0x8)
    class UEditableText* EditableText_RCExpo_2;                                       // 0x0348 (size: 0x8)
    class UEditableText* EditableText_RollAxisSpeed;                                  // 0x0350 (size: 0x8)
    class UEditableText* EditableText_SFXVolumeSlider;                                // 0x0358 (size: 0x8)
    class UEditableText* EditableText_YawAxisSpeed;                                   // 0x0360 (size: 0x8)
    class UWBP_SettingsOption_C* EffectsSettingsOption;                               // 0x0368 (size: 0x8)
    class UWBP_SettingsOption_C* FoliageSettingsOption;                               // 0x0370 (size: 0x8)
    class UWBP_SettingsOption_C* IlluminationSettingsOption;                          // 0x0378 (size: 0x8)
    class USlider* MusicVolumeSlider;                                                 // 0x0380 (size: 0x8)
    class UWBP_SettingsOption_C* OverallGraphicsSettingsOption;                       // 0x0388 (size: 0x8)
    class UWBP_SettingsOption_C* PostProcessingSettingsOption;                        // 0x0390 (size: 0x8)
    class UWBP_SettingsOption_C* ReflectionsSettingsOption;                           // 0x0398 (size: 0x8)
    class UWBP_SettingsOption_C* ResolutionMode;                                      // 0x03A0 (size: 0x8)
    class USlider* SFXVolumeSlider;                                                   // 0x03A8 (size: 0x8)
    class UWBP_SettingsOption_C* ShadersSettingsOption;                               // 0x03B0 (size: 0x8)
    class UWBP_SettingsOption_C* ShadowsSettingsOption;                               // 0x03B8 (size: 0x8)
    class USlider* Slider_Brightness;                                                 // 0x03C0 (size: 0x8)
    class USlider* Slider_Deadzone;                                                   // 0x03C8 (size: 0x8)
    class USlider* Slider_FOV;                                                        // 0x03D0 (size: 0x8)
    class USlider* Slider_PitchAxisSpeed;                                             // 0x03D8 (size: 0x8)
    class USlider* Slider_RCExpoPitch;                                                // 0x03E0 (size: 0x8)
    class USlider* Slider_RCExpoRoll;                                                 // 0x03E8 (size: 0x8)
    class USlider* Slider_RCExpoYaw;                                                  // 0x03F0 (size: 0x8)
    class USlider* Slider_RollAxisSpeed;                                              // 0x03F8 (size: 0x8)
    class USlider* Slider_YawAxisSpeed;                                               // 0x0400 (size: 0x8)
    class UWBP_SettingsOption_C* TexturesSettingsOption;                              // 0x0408 (size: 0x8)
    class UWBP_SettingsOption_C* V-SYNCOption;                                        // 0x0410 (size: 0x8)
    class UWBP_SettingsOption_C* ViewDistanceSettingsOption;                          // 0x0418 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* WBP_EGUI_CommonHeader;                            // 0x0420 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher;                                            // 0x0428 (size: 0x8)
    class UWBP_SettingsOption_C* WindowModeOption;                                    // 0x0430 (size: 0x8)
    double FrameRate;                                                                 // 0x0438 (size: 0x8)
    FIntPoint Resolution;                                                             // 0x0440 (size: 0x8)
    bool Vsync;                                                                       // 0x0448 (size: 0x1)
    TEnumAsByte<EWindowMode::Type> WindowMode;                                        // 0x0449 (size: 0x1)
    int32 ShadingQuality;                                                             // 0x044C (size: 0x4)
    int32 ShadowQuality;                                                              // 0x0450 (size: 0x4)
    int32 TextureQuality;                                                             // 0x0454 (size: 0x4)
    int32 ResolutionIndex;                                                            // 0x0458 (size: 0x4)
    TArray<int32> GraphicOptions;                                                     // 0x0460 (size: 0x10)
    class UWBP_SettingsOption_C* Target;                                              // 0x0470 (size: 0x8)
    FLinearColor Text Color And Opacity;                                              // 0x0478 (size: 0x10)
    FText NewVar;                                                                     // 0x0488 (size: 0x10)
    class UBP_SettingsSaveGame_C* MyOptions;                                          // 0x0498 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x04A0 (size: 0x8)
    class AHUD_MainUAV_C* HUD Main Drone;                                             // 0x04A8 (size: 0x8)
    class UObject* UserSettings;                                                      // 0x04B0 (size: 0x8)
    class ABPP_MenuCam_C* BPP Menu Cam;                                               // 0x04B8 (size: 0x8)
    double DefaultGammaValue;                                                         // 0x04C0 (size: 0x8)
    FVector2D GammaValueRange;                                                        // 0x04C8 (size: 0x10)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x04D8 (size: 0x8)
    class AGM_UAVBase_C* GM UAVBase;                                                  // 0x04E0 (size: 0x8)

    FText Get Slider Deadzone();
    FText Set Slider FOV();
    FText Set Brightness Text();
    FText Set Slider RC Expo Yaw Text Value();
    FText Set Slider RC Expo Pitch Text Value();
    FText Set Slider Yaw Axis Speed Text Value();
    FText Set Slider Pitch Axis Speed Text Value();
    FText Set Slider Roll Axis Speed Text Value();
    FText Set Slider SFX Volume Value();
    FText Set Slider Music Volume Value();
    FText Set Slider RC Expo Roll Text Value();
    void SetOverallGraphicsOptions();
    void SaveSettings();
    FText GetFrameRate();
    FText GetVsync();
    FText GetShader();
    FText GetTexture();
    FText GetShadow();
    FText GetResolution();
    FText GetWindowMode();
    void BndEvt__WBP_SettingsMenu_OverallGraphicsSettingsOption_K2Node_ComponentBoundEvent_24_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_AntiAliasingSettingsOption_K2Node_ComponentBoundEvent_25_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_ShadowsSettingsOption_K2Node_ComponentBoundEvent_26_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_TexturesSettingsOption_K2Node_ComponentBoundEvent_27_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_ShadersSettingsOption_K2Node_ComponentBoundEvent_28_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_ViewDistanceSettingsOption_K2Node_ComponentBoundEvent_29_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_SFXVolumeSlider_K2Node_ComponentBoundEvent_21_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_DisplayModeSettingsOption_K2Node_ComponentBoundEvent_0_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_FoliageSettingsOption_K2Node_ComponentBoundEvent_1_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_IlluminationSettingsOption_K2Node_ComponentBoundEvent_2_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_ReflectionsSettingsOption_K2Node_ComponentBoundEvent_3_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_EffectsSettingsOption_K2Node_ComponentBoundEvent_4_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_VSyncSettingsOption_K2Node_ComponentBoundEvent_7_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void OnInitialized();
    void BndEvt__WBP_SettingsMenu_Slider_RXExpo_K2Node_ComponentBoundEvent_5_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_WindowModeOption_K2Node_ComponentBoundEvent_11_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_ResolutionMode_K2Node_ComponentBoundEvent_12_OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
    void BndEvt__WBP_SettingsMenu_Slider_RollAxisSpeed_K2Node_ComponentBoundEvent_6_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_Slider_PitchAxisSpeed_K2Node_ComponentBoundEvent_13_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_Slider_YawAxisSpeed_K2Node_ComponentBoundEvent_16_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_EditableText_191_K2Node_ComponentBoundEvent_8_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_RollAxisSpeed_K2Node_ComponentBoundEvent_31_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_PitchAxisSpeed_K2Node_ComponentBoundEvent_35_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_YawAxisSpeed_K2Node_ComponentBoundEvent_36_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_SFXVolumeSlider_K2Node_ComponentBoundEvent_17_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_Slider_RCExpo_1_K2Node_ComponentBoundEvent_41_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_Slider_RCExpo_2_K2Node_ComponentBoundEvent_43_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_EditableText_RCExpo_1_K2Node_ComponentBoundEvent_48_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_RCExpo_2_K2Node_ComponentBoundEvent_49_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_Slider_RCExpoRoll_K2Node_ComponentBoundEvent_46_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_RCExpoPitch_K2Node_ComponentBoundEvent_64_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_RCExpoYaw_K2Node_ComponentBoundEvent_65_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_RollAxisSpeed_K2Node_ComponentBoundEvent_68_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_PitchAxisSpeed_K2Node_ComponentBoundEvent_69_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_YawAxisSpeed_K2Node_ComponentBoundEvent_70_OnMouseCaptureEndEvent__DelegateSignature();
    void SetVisibilityResetToDefaultButton(ESlateVisibility Visible);
    void SetVisibilityApplyButton(ESlateVisibility Visibility);
    void Apply Settings And Save Settings();
    void Load Settings Data();
    void BndEvt__WBP_SettingsMenu_Slider_Brightness_K2Node_ComponentBoundEvent_0_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_Slider_Brightness_K2Node_ComponentBoundEvent_2_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_EditableText_Brightness_K2Node_ComponentBoundEvent_52_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_EditableText_FOV_K2Node_ComponentBoundEvent_51_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void BndEvt__WBP_SettingsMenu_Slider_FOV_K2Node_ComponentBoundEvent_54_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_FOV_K2Node_ComponentBoundEvent_56_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void SettingsClose();
    void BndEvt__WBP_SettingsMenu_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_9_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void BndEvt__WBP_SettingsMenu_Btn_APPLY_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SettingsMenu_Btn_RESET_K2Node_ComponentBoundEvent_18_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SettingsMenu_Btn_MENU_K2Node_ComponentBoundEvent_19_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SettingsMenu_Btn_RC_K2Node_ComponentBoundEvent_23_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_SettingsMenu_Slider_Deadzone_K2Node_ComponentBoundEvent_14_OnMouseCaptureEndEvent__DelegateSignature();
    void BndEvt__WBP_SettingsMenu_Slider_Deadzone_K2Node_ComponentBoundEvent_15_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_EditableText_FOV_1_K2Node_ComponentBoundEvent_22_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void Construct();
    void BndEvt__WBP_SettingsMenu_SFXVolumeSlider_1_K2Node_ComponentBoundEvent_30_OnFloatValueChangedEvent__DelegateSignature(float Value);
    void BndEvt__WBP_SettingsMenu_EditableText_SFXVolumeSlider_1_K2Node_ComponentBoundEvent_32_OnEditableTextCommittedEvent__DelegateSignature(const FText& Text, TEnumAsByte<ETextCommit::Type> CommitMethod);
    void ExecuteUbergraph_WBP_SettingsMenu(int32 EntryPoint);
}; // Size: 0x4E8

#endif
