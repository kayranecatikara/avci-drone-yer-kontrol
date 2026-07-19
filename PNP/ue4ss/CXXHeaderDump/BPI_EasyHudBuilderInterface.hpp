#ifndef UE4SS_SDK_BPI_EasyHudBuilderInterface_HPP
#define UE4SS_SDK_BPI_EasyHudBuilderInterface_HPP

class IBPI_EasyHudBuilderInterface_C : public IInterface
{

    void HudIsHidden?(bool& HudHidden?);
    void ModuleStopListenForInput(class UUserWidget* ModuleWidget);
    void NewModuleListenForInputs(class UUserWidget* ModuleWidget);
    void HideOrShowEntireHud(bool HideHud?, double FadeDuration);
    void RemoveAllModulesFromHud(bool RemoveAllManuallyAddedModules?, bool RemoveAllModulesAddedByContext?, bool OverrideFadeDuration?, double FadeOutDuration);
    void RemoveModuleFromHud(FString ModuleToRemove, bool& ModuleRemoved?);
    void SetupNewModuleOnHud(FString ModuleName, FS_HudModuleContextOverride ModuleLayoutOverride, bool ForceReinitIfAlreadyOnHud?, class UUserWidget*& WidgetReference);
    void GetAllActiveModuleWidgets(TArray<class UUserWidget*>& ActiveModules);
    void GetModuleWidgetReference(FString ModuleName, bool& ModuleActive?, class UUserWidget*& WidgetReference);
    void GetMultipleModulesWidgetReferences(TArray<FString>& ModulesName, TArray<bool>& ModulesActive?, TArray<class UUserWidget*>& WidgetsReference);
    void UpdateHudScale(float NewHudScale);
    void RevertToPreviousHudContext(bool ShowHudIfHidden?, double FadeOutDuration, bool RemoveAllActiveModules?);
    void SwitchToNewHudContext(TEnumAsByte<E_HudContexts::Type> RequestedHudContext, bool ShowHudIfHidden?, double FadeOutDuration, bool RemoveAllActiveModules?, bool& SwitchSuccess?, TEnumAsByte<E_HudContexts::Type>& OutHudContext);
    void GetCurrentHudContext(TEnumAsByte<E_HudContexts::Type> InputContextToCompare, bool& SameAsInputContext?, TEnumAsByte<E_HudContexts::Type>& CurrentHudContext, TEnumAsByte<E_HudContexts::Type>& PreviousHudContext);
}; // Size: 0x28

#endif
