---@meta

---@class UWBP_SettingsMenu_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Gate UWidgetAnimation
---@field AntiAliasingSettingsOption UWBP_SettingsOption_C
---@field BackgroundBlur UBackgroundBlur
---@field Btn_APPLY UWBP_EGUI_CommonButton_C
---@field Btn_CONFIRM UWBP_EGUI_CommonButton_C
---@field Btn_MENU UWBP_EGUI_CommonButton_C
---@field Btn_RESET UWBP_EGUI_CommonButton_C
---@field EditableText_Brightness UEditableText
---@field EditableText_FOV UEditableText
---@field EditableText_FOV_1 UEditableText
---@field EditableText_MusicVolumeSlider UEditableText
---@field EditableText_PitchAxisSpeed UEditableText
---@field EditableText_RCExpo UEditableText
---@field EditableText_RCExpo_1 UEditableText
---@field EditableText_RCExpo_2 UEditableText
---@field EditableText_RollAxisSpeed UEditableText
---@field EditableText_SFXVolumeSlider UEditableText
---@field EditableText_YawAxisSpeed UEditableText
---@field EffectsSettingsOption UWBP_SettingsOption_C
---@field FoliageSettingsOption UWBP_SettingsOption_C
---@field IlluminationSettingsOption UWBP_SettingsOption_C
---@field MusicVolumeSlider USlider
---@field OverallGraphicsSettingsOption UWBP_SettingsOption_C
---@field PostProcessingSettingsOption UWBP_SettingsOption_C
---@field ReflectionsSettingsOption UWBP_SettingsOption_C
---@field ResolutionMode UWBP_SettingsOption_C
---@field SFXVolumeSlider USlider
---@field ShadersSettingsOption UWBP_SettingsOption_C
---@field ShadowsSettingsOption UWBP_SettingsOption_C
---@field Slider_Brightness USlider
---@field Slider_Deadzone USlider
---@field Slider_FOV USlider
---@field Slider_PitchAxisSpeed USlider
---@field Slider_RCExpoPitch USlider
---@field Slider_RCExpoRoll USlider
---@field Slider_RCExpoYaw USlider
---@field Slider_RollAxisSpeed USlider
---@field Slider_YawAxisSpeed USlider
---@field TexturesSettingsOption UWBP_SettingsOption_C
---@field ['V-SYNCOption'] UWBP_SettingsOption_C
---@field ViewDistanceSettingsOption UWBP_SettingsOption_C
---@field WBP_EGUI_CommonHeader UWBP_EGUI_CommonHeader_C
---@field WidgetSwitcher UWidgetSwitcher
---@field WindowModeOption UWBP_SettingsOption_C
---@field FrameRate double
---@field Resolution FIntPoint
---@field Vsync boolean
---@field WindowMode EWindowMode::Type
---@field ShadingQuality int32
---@field ShadowQuality int32
---@field TextureQuality int32
---@field ResolutionIndex int32
---@field GraphicOptions TArray<int32>
---@field Target UWBP_SettingsOption_C
---@field ['Text Color And Opacity'] FLinearColor
---@field NewVar FText
---@field MyOptions UBP_SettingsSaveGame_C
---@field ['HUD Main Menu'] AHUD_MainMenu_C
---@field ['HUD Main Drone'] AHUD_MainUAV_C
---@field UserSettings UObject
---@field ['BPP Menu Cam'] ABPP_MenuCam_C
---@field DefaultGammaValue double
---@field GammaValueRange FVector2D
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['GM UAVBase'] AGM_UAVBase_C
local UWBP_SettingsMenu_C = {}

---@return FText
UWBP_SettingsMenu_C['Get Slider Deadzone'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider FOV'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Brightness Text'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider RC Expo Yaw Text Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider RC Expo Pitch Text Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider Yaw Axis Speed Text Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider Pitch Axis Speed Text Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider Roll Axis Speed Text Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider SFX Volume Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider Music Volume Value'] = function(self, ) end
---@return FText
UWBP_SettingsMenu_C['Set Slider RC Expo Roll Text Value'] = function(self, ) end
function UWBP_SettingsMenu_C:SetOverallGraphicsOptions() end
function UWBP_SettingsMenu_C:SaveSettings() end
---@return FText
function UWBP_SettingsMenu_C:GetFrameRate() end
---@return FText
function UWBP_SettingsMenu_C:GetVsync() end
---@return FText
function UWBP_SettingsMenu_C:GetShader() end
---@return FText
function UWBP_SettingsMenu_C:GetTexture() end
---@return FText
function UWBP_SettingsMenu_C:GetShadow() end
---@return FText
function UWBP_SettingsMenu_C:GetResolution() end
---@return FText
function UWBP_SettingsMenu_C:GetWindowMode() end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_OverallGraphicsSettingsOption_K2Node_ComponentBoundEvent_24_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_AntiAliasingSettingsOption_K2Node_ComponentBoundEvent_25_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_ShadowsSettingsOption_K2Node_ComponentBoundEvent_26_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_TexturesSettingsOption_K2Node_ComponentBoundEvent_27_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_ShadersSettingsOption_K2Node_ComponentBoundEvent_28_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_ViewDistanceSettingsOption_K2Node_ComponentBoundEvent_29_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_SFXVolumeSlider_K2Node_ComponentBoundEvent_21_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_DisplayModeSettingsOption_K2Node_ComponentBoundEvent_0_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_FoliageSettingsOption_K2Node_ComponentBoundEvent_1_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_IlluminationSettingsOption_K2Node_ComponentBoundEvent_2_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_ReflectionsSettingsOption_K2Node_ComponentBoundEvent_3_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EffectsSettingsOption_K2Node_ComponentBoundEvent_4_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_VSyncSettingsOption_K2Node_ComponentBoundEvent_7_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
function UWBP_SettingsMenu_C:OnInitialized() end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RXExpo_K2Node_ComponentBoundEvent_5_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_WindowModeOption_K2Node_ComponentBoundEvent_11_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_ResolutionMode_K2Node_ComponentBoundEvent_12_OnOptionsChanged__DelegateSignature(Option, OptionIndex) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RollAxisSpeed_K2Node_ComponentBoundEvent_6_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_PitchAxisSpeed_K2Node_ComponentBoundEvent_13_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_YawAxisSpeed_K2Node_ComponentBoundEvent_16_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_191_K2Node_ComponentBoundEvent_8_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_RollAxisSpeed_K2Node_ComponentBoundEvent_31_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_PitchAxisSpeed_K2Node_ComponentBoundEvent_35_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_YawAxisSpeed_K2Node_ComponentBoundEvent_36_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_SFXVolumeSlider_K2Node_ComponentBoundEvent_17_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RCExpo_1_K2Node_ComponentBoundEvent_41_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RCExpo_2_K2Node_ComponentBoundEvent_43_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_RCExpo_1_K2Node_ComponentBoundEvent_48_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_RCExpo_2_K2Node_ComponentBoundEvent_49_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RCExpoRoll_K2Node_ComponentBoundEvent_46_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RCExpoPitch_K2Node_ComponentBoundEvent_64_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RCExpoYaw_K2Node_ComponentBoundEvent_65_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_RollAxisSpeed_K2Node_ComponentBoundEvent_68_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_PitchAxisSpeed_K2Node_ComponentBoundEvent_69_OnMouseCaptureEndEvent__DelegateSignature() end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_YawAxisSpeed_K2Node_ComponentBoundEvent_70_OnMouseCaptureEndEvent__DelegateSignature() end
---@param Visible ESlateVisibility
function UWBP_SettingsMenu_C:SetVisibilityResetToDefaultButton(Visible) end
---@param Visibility ESlateVisibility
function UWBP_SettingsMenu_C:SetVisibilityApplyButton(Visibility) end
UWBP_SettingsMenu_C['Apply Settings And Save Settings'] = function(self, ) end
UWBP_SettingsMenu_C['Load Settings Data'] = function(self, ) end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_Brightness_K2Node_ComponentBoundEvent_0_OnFloatValueChangedEvent__DelegateSignature(Value) end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_Brightness_K2Node_ComponentBoundEvent_2_OnMouseCaptureEndEvent__DelegateSignature() end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_Brightness_K2Node_ComponentBoundEvent_52_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_FOV_K2Node_ComponentBoundEvent_51_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_FOV_K2Node_ComponentBoundEvent_54_OnMouseCaptureEndEvent__DelegateSignature() end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_FOV_K2Node_ComponentBoundEvent_56_OnFloatValueChangedEvent__DelegateSignature(Value) end
function UWBP_SettingsMenu_C:SettingsClose() end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_9_NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end
---@param SelfIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Btn_APPLY_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Btn_RESET_K2Node_ComponentBoundEvent_18_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Btn_MENU_K2Node_ComponentBoundEvent_19_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Btn_RC_K2Node_ComponentBoundEvent_23_ButtonClicked__DelegateSignature(SelfIndex) end
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_Deadzone_K2Node_ComponentBoundEvent_14_OnMouseCaptureEndEvent__DelegateSignature() end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_Slider_Deadzone_K2Node_ComponentBoundEvent_15_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_FOV_1_K2Node_ComponentBoundEvent_22_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
function UWBP_SettingsMenu_C:Construct() end
---@param Value float
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_SFXVolumeSlider_1_K2Node_ComponentBoundEvent_30_OnFloatValueChangedEvent__DelegateSignature(Value) end
---@param Text FText
---@param CommitMethod ETextCommit::Type
function UWBP_SettingsMenu_C:BndEvt__WBP_SettingsMenu_EditableText_SFXVolumeSlider_1_K2Node_ComponentBoundEvent_32_OnEditableTextCommittedEvent__DelegateSignature(Text, CommitMethod) end
---@param EntryPoint int32
function UWBP_SettingsMenu_C:ExecuteUbergraph_WBP_SettingsMenu(EntryPoint) end


