---@meta

---@class IBPI_EasyHudModulesInterface_C : IInterface
local IBPI_EasyHudModulesInterface_C = {}

---@param InputName FString
---@param TriggerEvent ETriggerEvent
function IBPI_EasyHudModulesInterface_C:HudInputTriggered(InputName, TriggerEvent) end
---@param bHasCanvasSlot_ boolean
IBPI_EasyHudModulesInterface_C['HasCanvasSlot?'] = function(self, bHasCanvasSlot_) end
---@param CurrentModuleLayout FS_HudModuleLayoutSettings
function IBPI_EasyHudModulesInterface_C:GetCurrentModuleLayout(CurrentModuleLayout) end
---@param ModuleName FString
function IBPI_EasyHudModulesInterface_C:GetModuleName(ModuleName) end
---@param ModuleActive_ boolean
IBPI_EasyHudModulesInterface_C['IsModuleActive?'] = function(self, ModuleActive_) end
function IBPI_EasyHudModulesInterface_C:ClearSkillConsumableSlot() end
function IBPI_EasyHudModulesInterface_C:ClearFramerateCounter() end
---@param RefreshInterval double
function IBPI_EasyHudModulesInterface_C:DisplayFramerateCounter(RefreshInterval) end
function IBPI_EasyHudModulesInterface_C:ClearActiveWeapon() end
---@param HasInfiniteCurrentAmmunitions_ boolean
---@param HasInfiniteMaxAmmunitions_ boolean
function IBPI_EasyHudModulesInterface_C:UpdateInfiniteAmmunitions(HasInfiniteCurrentAmmunitions_, HasInfiniteMaxAmmunitions_) end
---@param OverrideFadeDuration_ boolean
---@param FadeOutDuration double
function IBPI_EasyHudModulesInterface_C:ClearModule(OverrideFadeDuration_, FadeOutDuration) end
---@param ModuleName FString
---@param HudBuilderManagerRef UActorComponent
---@param CanvasPanelSlot UCanvasPanelSlot
---@param ModuleLayout FS_HudModuleLayoutSettings
function IBPI_EasyHudModulesInterface_C:InitModule(ModuleName, HudBuilderManagerRef, CanvasPanelSlot, ModuleLayout) end
---@param ClearOnlyIfAllObjectivesHaveBeenDone_ boolean
---@param ClearWithDelay_ boolean
---@param ClearDelay double
function IBPI_EasyHudModulesInterface_C:ClearCurrentQuest(ClearOnlyIfAllObjectivesHaveBeenDone_, ClearWithDelay_, ClearDelay) end
function IBPI_EasyHudModulesInterface_C:ClearCurrentQuestObjectives() end
---@param ClearAllCurrentObjectives_ boolean
---@param NewQuestObjectives TArray<FS_QuestObjectiveDefinition>
function IBPI_EasyHudModulesInterface_C:UpdateQuestObjectivesList(ClearAllCurrentObjectives_, NewQuestObjectives) end
---@param ObjectiveUniqueName FName
---@param NewDescription FText
---@param NewIsOptional_ boolean
function IBPI_EasyHudModulesInterface_C:UpdateQuestObjectiveDescription(ObjectiveUniqueName, NewDescription, NewIsOptional_) end
---@param ObjectiveUniqueName FName
---@param NewState E_QuestObjectiveState::Type
---@param ClearAfterDelay_ boolean
---@param ClearDelay double
function IBPI_EasyHudModulesInterface_C:UpdateQuestObjectiveState(ObjectiveUniqueName, NewState, ClearAfterDelay_, ClearDelay) end
---@param QuestDisplayName FText
---@param QuestInitialObjectives TArray<FS_QuestObjectiveDefinition>
function IBPI_EasyHudModulesInterface_C:DisplayNewQuest(QuestDisplayName, QuestInitialObjectives) end
function IBPI_EasyHudModulesInterface_C:ClearAllTutorials() end
function IBPI_EasyHudModulesInterface_C:ClearCurrentTutorial() end
---@param TutorialDefinition FS_TutorialDefinition
function IBPI_EasyHudModulesInterface_C:DisplayNewTutorial(TutorialDefinition) end
function IBPI_EasyHudModulesInterface_C:ClearAllImportantAlerts() end
function IBPI_EasyHudModulesInterface_C:ClearCurrentImportantAlert() end
---@param ImportantAlertDefinition FS_ImportantAlertDefinition
function IBPI_EasyHudModulesInterface_C:DisplayNewImportantAlert(ImportantAlertDefinition) end
function IBPI_EasyHudModulesInterface_C:ClearPersistentExperienceProgressNotification() end
---@param ClearPersistentProgressNotification_ boolean
function IBPI_EasyHudModulesInterface_C:ClearAllExperienceProgressNotifications(ClearPersistentProgressNotification_) end
---@param ExperienceProgressNotificationInfos FS_ExperienceProgressNotificationDefinition
function IBPI_EasyHudModulesInterface_C:DisplayNewExperienceProgressBar(ExperienceProgressNotificationInfos) end
function IBPI_EasyHudModulesInterface_C:StopAllSkillSlotCooldowns() end
---@param UpdateOperationType E_IntegerUpdateOperationType::Type
---@param NewMaxUtilisationsValue int32
function IBPI_EasyHudModulesInterface_C:UpdateSkillSlotMaxUtilisation(UpdateOperationType, NewMaxUtilisationsValue) end
---@param UpdateOperationType E_IntegerUpdateOperationType::Type
---@param NewCurrentUtilisationsValue int32
---@param TriggerCooldown_ boolean
---@param CooldownDuration double
---@param RegainUtilisationAfterCooldown_ boolean
function IBPI_EasyHudModulesInterface_C:UpdateSkillSlotCurrentUtilisation(UpdateOperationType, NewCurrentUtilisationsValue, TriggerCooldown_, CooldownDuration, RegainUtilisationAfterCooldown_) end
---@param Slot_Definition FS_SkillConsumableSlotDefinition
function IBPI_EasyHudModulesInterface_C:InitializeSkillSlot(Slot_Definition) end
function IBPI_EasyHudModulesInterface_C:ClearAllPickUpNotifications() end
---@param ItemInfos FS_PickupItemInfos
function IBPI_EasyHudModulesInterface_C:DisplayNewItemPickUp(ItemInfos) end
---@param UpdateOperationType E_IntegerUpdateOperationType::Type
---@param NewMaximumAmmunitionsValue int32
function IBPI_EasyHudModulesInterface_C:UpdateMaximumAmmunitions(UpdateOperationType, NewMaximumAmmunitionsValue) end
---@param UpdateOperationType E_IntegerUpdateOperationType::Type
---@param NewCurrentAmmunitionValue int32
function IBPI_EasyHudModulesInterface_C:UpdateCurrentAmmunitions(UpdateOperationType, NewCurrentAmmunitionValue) end
---@param WeaponImage UTexture2D
---@param WeaponDisplayName FText
---@param HasInfiniteCurrentAmmunitions_ boolean
---@param CurrentAmmunitions int32
---@param HasInfiniteMaxAmmunitions_ boolean
---@param MaximumAmmunitions int32
function IBPI_EasyHudModulesInterface_C:DisplayNewActiveWeapon(WeaponImage, WeaponDisplayName, HasInfiniteCurrentAmmunitions_, CurrentAmmunitions, HasInfiniteMaxAmmunitions_, MaximumAmmunitions) end
function IBPI_EasyHudModulesInterface_C:AutoSaveCompleted() end
function IBPI_EasyHudModulesInterface_C:AutoSaveStarted() end
function IBPI_EasyHudModulesInterface_C:ClearAllInputPrompts() end
---@param InputPromptUniqueName FName
function IBPI_EasyHudModulesInterface_C:ClearSpecificInputPrompt(InputPromptUniqueName) end
---@param UniqueName FName
---@param UseInputAction_ boolean
---@param InputAction UInputAction
---@param InputMappingContext UInputMappingContext
---@param MouseKeyboardKeys TArray<FKey>
---@param GamepadKeys TArray<FKey>
---@param KeyImageSize double
---@param TextToDisplay FText
---@param TextPosition EHorizontalAlignment
---@param TextPadding FMargin
---@param TextStyling FS_CommonTextInfo
---@param InputsSpacing double
---@param HideKeysForOtherDevices_ boolean
---@param HideTextAsWell_ boolean
---@param VerticalAlignmentInSlot EVerticalAlignment
---@param HorizontalAlignmentInSlot EHorizontalAlignment
---@param MultiInputPromptReference UWBP_EasyMultiInputPromptDisplayer_C
function IBPI_EasyHudModulesInterface_C:DisplayNewMultiInputPrompt(UniqueName, UseInputAction_, InputAction, InputMappingContext, MouseKeyboardKeys, GamepadKeys, KeyImageSize, TextToDisplay, TextPosition, TextPadding, TextStyling, InputsSpacing, HideKeysForOtherDevices_, HideTextAsWell_, VerticalAlignmentInSlot, HorizontalAlignmentInSlot, MultiInputPromptReference) end
---@param UniqueName FName
---@param UseInputAction_ boolean
---@param InputActionInfos FS_InputActionDef
---@param MouseKeyboardKey FKey
---@param GamepadKey FKey
---@param DisplayConditions E_InputPromptDisplayConditions::Type
---@param HideKeyForOtherDevices_ boolean
---@param HideTextAsWell_ boolean
---@param KeyImageSize double
---@param TextToDisplay FText
---@param TextPosition EHorizontalAlignment
---@param TextPadding FMargin
---@param TextStyling FS_CommonTextInfo
---@param InputPromptType E_InputPromptType::Type
---@param VerticalAlignmentInSlot EVerticalAlignment
---@param HorizontalAlignmentInSlot EHorizontalAlignment
---@param InputPromptReference UWBP_EasyInputPromptDisplayer_C
function IBPI_EasyHudModulesInterface_C:DisplayNewSingleInputPrompt(UniqueName, UseInputAction_, InputActionInfos, MouseKeyboardKey, GamepadKey, DisplayConditions, HideKeyForOtherDevices_, HideTextAsWell_, KeyImageSize, TextToDisplay, TextPosition, TextPadding, TextStyling, InputPromptType, VerticalAlignmentInSlot, HorizontalAlignmentInSlot, InputPromptReference) end
---@param NewShieldAmount double
---@param UpdateMaxShield_ boolean
---@param NewMaxShieldAmount double
function IBPI_EasyHudModulesInterface_C:UpdateShieldAmount(NewShieldAmount, UpdateMaxShield_, NewMaxShieldAmount) end
---@param NewHealthAmount double
---@param UpdateMaxHealth_ boolean
---@param NewMaxHealthAmount double
function IBPI_EasyHudModulesInterface_C:UpdateHealthAmount(NewHealthAmount, UpdateMaxHealth_, NewMaxHealthAmount) end
---@param DisplayShield_ boolean
---@param CurrentShield double
---@param MaximumShield double
function IBPI_EasyHudModulesInterface_C:DisplayShieldBar(DisplayShield_, CurrentShield, MaximumShield) end
---@param DisplayHealth_ boolean
---@param CurrentHealth double
---@param MaximumHealth double
function IBPI_EasyHudModulesInterface_C:DisplayHealthBar(DisplayHealth_, CurrentHealth, MaximumHealth) end


