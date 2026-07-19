#ifndef UE4SS_SDK_BFL_EasyFunctionUtilities_HPP
#define UE4SS_SDK_BFL_EasyFunctionUtilities_HPP

class UBFL_EasyFunctionUtilities_C : public UBlueprintFunctionLibrary
{

    void GetEasyInteractionManagerReference(class UObject* __WorldContext, class UActorComponent*& InteractionManager);
    void GetEasyHudBuilderManagerReference(class UObject* __WorldContext, class UActorComponent*& HudBuilderManager);
    void EnableAllInputsOnCharacterAndController(class UObject* __WorldContext);
    void DisableAllInputsOnCharacterAndController(class UObject* __WorldContext);
    void IsLevelReferenceCurrentLevel?(const TSoftObjectPtr<UObject>& LevelReference, FName CurrentLevel, class UObject* __WorldContext, bool& IsCurrentLevel);
    void GetLevelNameFromReference(const TSoftObjectPtr<UObject>& LevelReference, class UObject* __WorldContext, FName& LevelName);
    bool IsUsingGamepad?(class UObject* __WorldContext);
    void GetConfigDataAsset(class UObject* __WorldContext, class UDA_EGUI_GlobalConfig_C*& ConfigDataAsset);
    void SafeCreateWidget(TSubclassOf<class UUserWidget> WidgetClass, int32 ZOrder, bool AddToViewport?, class UObject* __WorldContext, class UUserWidget*& WidgetRef);
    void InitGameInstanceSettings(FJsonObjectWrapper InitialUserSettings, bool UserSettingsValid?, class UObject* __WorldContext);
    void ApplyAA AndUpscalingMethod(const FJsonObjectWrapper& SettingJsonFile, class UObject* __WorldContext);
    void DisableUpscalings(class UObject* __WorldContext);
    void SetAA AndUpscalingMethods(TEnumAsByte<E_UpscalingMethods::Type> RequestedUpscalingMethod, TEnumAsByte<E_AntiAliasingMethods::Type> RequestedAA Method, const FJsonObjectWrapper& SettingJsonFile, bool DisableAppliedUpscaling?, class UObject* __WorldContext, TEnumAsByte<E_UpscalingMethods::Type>& NewUpscalingMethod, TEnumAsByte<E_AntiAliasingMethods::Type>& NewAA Method);
    void UpdateFontSize(FSlateFontInfo& Font, double NewSize, bool FixFontScaling?, class UObject* __WorldContext, FSlateFontInfo& UpdatedFont);
    void UpdateTintFromSlateBrush(const FSlateBrush& SlateBrush, FLinearColor& NewColor, double Alpha, class UObject* __WorldContext, FSlateBrush& SlateBrushOut);
    void SetResolutionScaleValue(float NewScaleValue, FJsonObjectWrapper SettingJsonFile, class UObject* __WorldContext);
    void SetAllAudioVolumes(TMap<TEnumAsByte<E_AudioClasses::Type>, double> AudioVolumes, class UObject* __WorldContext);
    void SetAudioVolume(float Volume, TEnumAsByte<E_AudioClasses::Type> AudioClass, class UObject* __WorldContext);
    void SetTextureFiltering(int32 Index, class UObject* __WorldContext);
    void SetMotionBlurQuality(int32 Value, class UObject* __WorldContext);
    void SetContactShadows(bool Enabled?, class UObject* __WorldContext);
    void SetVirtualShadowMaps(bool Enabled?, class UObject* __WorldContext);
    void SetLumenHardwareRT(bool Enabled?, class UObject* __WorldContext);
    void SetSharpness(double Value, class UObject* __WorldContext);
    void SetGamma(double Value, class UObject* __WorldContext);
    void SetVSyncInterval(int32 Value, class UObject* __WorldContext);
    void SetVolumetricsQuality(int32 Value, class UObject* __WorldContext);
    void ExecuteMultipleConsoleCommands(TArray<FString>& Commands, class UObject* __WorldContext);
    void GetSettingsFilePath(class UObject* __WorldContext, FFilePath& FilePath);
}; // Size: 0x28

#endif
