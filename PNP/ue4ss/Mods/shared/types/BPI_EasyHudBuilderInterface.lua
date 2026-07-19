---@meta

---@class IBPI_EasyHudBuilderInterface_C : IInterface
local IBPI_EasyHudBuilderInterface_C = {}

---@param HudHidden_ boolean
IBPI_EasyHudBuilderInterface_C['HudIsHidden?'] = function(self, HudHidden_) end
---@param ModuleWidget UUserWidget
function IBPI_EasyHudBuilderInterface_C:ModuleStopListenForInput(ModuleWidget) end
---@param ModuleWidget UUserWidget
function IBPI_EasyHudBuilderInterface_C:NewModuleListenForInputs(ModuleWidget) end
---@param HideHud_ boolean
---@param FadeDuration double
function IBPI_EasyHudBuilderInterface_C:HideOrShowEntireHud(HideHud_, FadeDuration) end
---@param RemoveAllManuallyAddedModules_ boolean
---@param RemoveAllModulesAddedByContext_ boolean
---@param OverrideFadeDuration_ boolean
---@param FadeOutDuration double
function IBPI_EasyHudBuilderInterface_C:RemoveAllModulesFromHud(RemoveAllManuallyAddedModules_, RemoveAllModulesAddedByContext_, OverrideFadeDuration_, FadeOutDuration) end
---@param ModuleToRemove FString
---@param ModuleRemoved_ boolean
function IBPI_EasyHudBuilderInterface_C:RemoveModuleFromHud(ModuleToRemove, ModuleRemoved_) end
---@param ModuleName FString
---@param ModuleLayoutOverride FS_HudModuleContextOverride
---@param ForceReinitIfAlreadyOnHud_ boolean
---@param WidgetReference UUserWidget
function IBPI_EasyHudBuilderInterface_C:SetupNewModuleOnHud(ModuleName, ModuleLayoutOverride, ForceReinitIfAlreadyOnHud_, WidgetReference) end
---@param ActiveModules TArray<UUserWidget>
function IBPI_EasyHudBuilderInterface_C:GetAllActiveModuleWidgets(ActiveModules) end
---@param ModuleName FString
---@param ModuleActive_ boolean
---@param WidgetReference UUserWidget
function IBPI_EasyHudBuilderInterface_C:GetModuleWidgetReference(ModuleName, ModuleActive_, WidgetReference) end
---@param ModulesName TArray<FString>
---@param ModulesActive_ TArray<boolean>
---@param WidgetsReference TArray<UUserWidget>
function IBPI_EasyHudBuilderInterface_C:GetMultipleModulesWidgetReferences(ModulesName, ModulesActive_, WidgetsReference) end
---@param NewHudScale float
function IBPI_EasyHudBuilderInterface_C:UpdateHudScale(NewHudScale) end
---@param ShowHudIfHidden_ boolean
---@param FadeOutDuration double
---@param RemoveAllActiveModules_ boolean
function IBPI_EasyHudBuilderInterface_C:RevertToPreviousHudContext(ShowHudIfHidden_, FadeOutDuration, RemoveAllActiveModules_) end
---@param RequestedHudContext E_HudContexts::Type
---@param ShowHudIfHidden_ boolean
---@param FadeOutDuration double
---@param RemoveAllActiveModules_ boolean
---@param SwitchSuccess_ boolean
---@param OutHudContext E_HudContexts::Type
function IBPI_EasyHudBuilderInterface_C:SwitchToNewHudContext(RequestedHudContext, ShowHudIfHidden_, FadeOutDuration, RemoveAllActiveModules_, SwitchSuccess_, OutHudContext) end
---@param InputContextToCompare E_HudContexts::Type
---@param SameAsInputContext_ boolean
---@param CurrentHudContext E_HudContexts::Type
---@param PreviousHudContext E_HudContexts::Type
function IBPI_EasyHudBuilderInterface_C:GetCurrentHudContext(InputContextToCompare, SameAsInputContext_, CurrentHudContext, PreviousHudContext) end


