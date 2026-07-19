---@meta

---@class UBFL_EasyFunctionUtilities_C : UBlueprintFunctionLibrary
local UBFL_EasyFunctionUtilities_C = {}

---@param __WorldContext UObject
---@param InteractionManager UActorComponent
function UBFL_EasyFunctionUtilities_C:GetEasyInteractionManagerReference(__WorldContext, InteractionManager) end
---@param __WorldContext UObject
---@param HudBuilderManager UActorComponent
function UBFL_EasyFunctionUtilities_C:GetEasyHudBuilderManagerReference(__WorldContext, HudBuilderManager) end
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:EnableAllInputsOnCharacterAndController(__WorldContext) end
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:DisableAllInputsOnCharacterAndController(__WorldContext) end
---@param LevelReference TSoftObjectPtr<UObject>
---@param CurrentLevel FName
---@param __WorldContext UObject
---@param IsCurrentLevel boolean
UBFL_EasyFunctionUtilities_C['IsLevelReferenceCurrentLevel?'] = function(self, LevelReference, CurrentLevel, __WorldContext, IsCurrentLevel) end
---@param LevelReference TSoftObjectPtr<UObject>
---@param __WorldContext UObject
---@param LevelName FName
function UBFL_EasyFunctionUtilities_C:GetLevelNameFromReference(LevelReference, __WorldContext, LevelName) end
---@param __WorldContext UObject
---@return boolean
UBFL_EasyFunctionUtilities_C['IsUsingGamepad?'] = function(self, __WorldContext) end
---@param __WorldContext UObject
---@param ConfigDataAsset UDA_EGUI_GlobalConfig_C
function UBFL_EasyFunctionUtilities_C:GetConfigDataAsset(__WorldContext, ConfigDataAsset) end
---@param WidgetClass TSubclassOf<UUserWidget>
---@param ZOrder int32
---@param AddToViewport_ boolean
---@param __WorldContext UObject
---@param WidgetRef UUserWidget
function UBFL_EasyFunctionUtilities_C:SafeCreateWidget(WidgetClass, ZOrder, AddToViewport_, __WorldContext, WidgetRef) end
---@param InitialUserSettings FJsonObjectWrapper
---@param UserSettingsValid_ boolean
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:InitGameInstanceSettings(InitialUserSettings, UserSettingsValid_, __WorldContext) end
---@param SettingJsonFile FJsonObjectWrapper
---@param __WorldContext UObject
UBFL_EasyFunctionUtilities_C['ApplyAA AndUpscalingMethod'] = function(self, SettingJsonFile, __WorldContext) end
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:DisableUpscalings(__WorldContext) end
---@param RequestedUpscalingMethod E_UpscalingMethods::Type
---@param RequestedAA_Method E_AntiAliasingMethods::Type
---@param SettingJsonFile FJsonObjectWrapper
---@param DisableAppliedUpscaling_ boolean
---@param __WorldContext UObject
---@param NewUpscalingMethod E_UpscalingMethods::Type
---@param NewAA_Method E_AntiAliasingMethods::Type
UBFL_EasyFunctionUtilities_C['SetAA AndUpscalingMethods'] = function(self, RequestedUpscalingMethod, RequestedAA_Method, SettingJsonFile, DisableAppliedUpscaling_, __WorldContext, NewUpscalingMethod, NewAA_Method) end
---@param Font FSlateFontInfo
---@param NewSize double
---@param FixFontScaling_ boolean
---@param __WorldContext UObject
---@param UpdatedFont FSlateFontInfo
function UBFL_EasyFunctionUtilities_C:UpdateFontSize(Font, NewSize, FixFontScaling_, __WorldContext, UpdatedFont) end
---@param SlateBrush FSlateBrush
---@param NewColor FLinearColor
---@param Alpha double
---@param __WorldContext UObject
---@param SlateBrushOut FSlateBrush
function UBFL_EasyFunctionUtilities_C:UpdateTintFromSlateBrush(SlateBrush, NewColor, Alpha, __WorldContext, SlateBrushOut) end
---@param NewScaleValue float
---@param SettingJsonFile FJsonObjectWrapper
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetResolutionScaleValue(NewScaleValue, SettingJsonFile, __WorldContext) end
---@param AudioVolumes TMap<E_AudioClasses::Type, double>
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetAllAudioVolumes(AudioVolumes, __WorldContext) end
---@param Volume float
---@param AudioClass E_AudioClasses::Type
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetAudioVolume(Volume, AudioClass, __WorldContext) end
---@param Index int32
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetTextureFiltering(Index, __WorldContext) end
---@param Value int32
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetMotionBlurQuality(Value, __WorldContext) end
---@param Enabled_ boolean
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetContactShadows(Enabled_, __WorldContext) end
---@param Enabled_ boolean
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetVirtualShadowMaps(Enabled_, __WorldContext) end
---@param Enabled_ boolean
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetLumenHardwareRT(Enabled_, __WorldContext) end
---@param Value double
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetSharpness(Value, __WorldContext) end
---@param Value double
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetGamma(Value, __WorldContext) end
---@param Value int32
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetVSyncInterval(Value, __WorldContext) end
---@param Value int32
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:SetVolumetricsQuality(Value, __WorldContext) end
---@param Commands TArray<FString>
---@param __WorldContext UObject
function UBFL_EasyFunctionUtilities_C:ExecuteMultipleConsoleCommands(Commands, __WorldContext) end
---@param __WorldContext UObject
---@param FilePath FFilePath
function UBFL_EasyFunctionUtilities_C:GetSettingsFilePath(__WorldContext, FilePath) end


