#ifndef UE4SS_SDK_BPI_EasyHudModulesInterface_HPP
#define UE4SS_SDK_BPI_EasyHudModulesInterface_HPP

class IBPI_EasyHudModulesInterface_C : public IInterface
{

    void HudInputTriggered(FString InputName, ETriggerEvent TriggerEvent);
    void HasCanvasSlot?(bool& bHasCanvasSlot?);
    void GetCurrentModuleLayout(FS_HudModuleLayoutSettings& CurrentModuleLayout);
    void GetModuleName(FString& ModuleName);
    void IsModuleActive?(bool& ModuleActive?);
    void ClearSkillConsumableSlot();
    void ClearFramerateCounter();
    void DisplayFramerateCounter(double RefreshInterval);
    void ClearActiveWeapon();
    void UpdateInfiniteAmmunitions(bool HasInfiniteCurrentAmmunitions?, bool HasInfiniteMaxAmmunitions?);
    void ClearModule(bool OverrideFadeDuration?, double FadeOutDuration);
    void InitModule(FString ModuleName, class UActorComponent* HudBuilderManagerRef, class UCanvasPanelSlot* CanvasPanelSlot, FS_HudModuleLayoutSettings ModuleLayout);
    void ClearCurrentQuest(bool ClearOnlyIfAllObjectivesHaveBeenDone?, bool ClearWithDelay?, double ClearDelay);
    void ClearCurrentQuestObjectives();
    void UpdateQuestObjectivesList(const bool ClearAllCurrentObjectives?, const TArray<FS_QuestObjectiveDefinition>& NewQuestObjectives);
    void UpdateQuestObjectiveDescription(const FName ObjectiveUniqueName, FText NewDescription, bool NewIsOptional?);
    void UpdateQuestObjectiveState(const FName ObjectiveUniqueName, TEnumAsByte<E_QuestObjectiveState::Type> NewState, bool ClearAfterDelay?, double ClearDelay);
    void DisplayNewQuest(FText QuestDisplayName, const TArray<FS_QuestObjectiveDefinition>& QuestInitialObjectives);
    void ClearAllTutorials();
    void ClearCurrentTutorial();
    void DisplayNewTutorial(FS_TutorialDefinition TutorialDefinition);
    void ClearAllImportantAlerts();
    void ClearCurrentImportantAlert();
    void DisplayNewImportantAlert(FS_ImportantAlertDefinition ImportantAlertDefinition);
    void ClearPersistentExperienceProgressNotification();
    void ClearAllExperienceProgressNotifications(bool ClearPersistentProgressNotification?);
    void DisplayNewExperienceProgressBar(FS_ExperienceProgressNotificationDefinition ExperienceProgressNotificationInfos);
    void StopAllSkillSlotCooldowns();
    void UpdateSkillSlotMaxUtilisation(TEnumAsByte<E_IntegerUpdateOperationType::Type> UpdateOperationType, int32 NewMaxUtilisationsValue);
    void UpdateSkillSlotCurrentUtilisation(TEnumAsByte<E_IntegerUpdateOperationType::Type> UpdateOperationType, int32 NewCurrentUtilisationsValue, bool TriggerCooldown?, double CooldownDuration, bool RegainUtilisationAfterCooldown?);
    void InitializeSkillSlot(FS_SkillConsumableSlotDefinition Slot Definition);
    void ClearAllPickUpNotifications();
    void DisplayNewItemPickUp(FS_PickupItemInfos ItemInfos);
    void UpdateMaximumAmmunitions(TEnumAsByte<E_IntegerUpdateOperationType::Type> UpdateOperationType, int32 NewMaximumAmmunitionsValue);
    void UpdateCurrentAmmunitions(TEnumAsByte<E_IntegerUpdateOperationType::Type> UpdateOperationType, int32 NewCurrentAmmunitionValue);
    void DisplayNewActiveWeapon(class UTexture2D* WeaponImage, FText WeaponDisplayName, bool HasInfiniteCurrentAmmunitions?, int32 CurrentAmmunitions, bool HasInfiniteMaxAmmunitions?, int32 MaximumAmmunitions);
    void AutoSaveCompleted();
    void AutoSaveStarted();
    void ClearAllInputPrompts();
    void ClearSpecificInputPrompt(FName InputPromptUniqueName);
    void DisplayNewMultiInputPrompt(FName UniqueName, bool UseInputAction?, class UInputAction* InputAction, class UInputMappingContext* InputMappingContext, TArray<FKey>& MouseKeyboardKeys, TArray<FKey>& GamepadKeys, double KeyImageSize, FText TextToDisplay, TEnumAsByte<EHorizontalAlignment> TextPosition, FMargin TextPadding, FS_CommonTextInfo TextStyling, double InputsSpacing, bool HideKeysForOtherDevices?, bool HideTextAsWell?, TEnumAsByte<EVerticalAlignment> VerticalAlignmentInSlot, TEnumAsByte<EHorizontalAlignment> HorizontalAlignmentInSlot, class UWBP_EasyMultiInputPromptDisplayer_C*& MultiInputPromptReference);
    void DisplayNewSingleInputPrompt(FName UniqueName, bool UseInputAction?, FS_InputActionDef InputActionInfos, FKey MouseKeyboardKey, FKey GamepadKey, TEnumAsByte<E_InputPromptDisplayConditions::Type> DisplayConditions, bool HideKeyForOtherDevices?, bool HideTextAsWell?, double KeyImageSize, FText TextToDisplay, TEnumAsByte<EHorizontalAlignment> TextPosition, FMargin TextPadding, FS_CommonTextInfo TextStyling, TEnumAsByte<E_InputPromptType::Type> InputPromptType, TEnumAsByte<EVerticalAlignment> VerticalAlignmentInSlot, TEnumAsByte<EHorizontalAlignment> HorizontalAlignmentInSlot, class UWBP_EasyInputPromptDisplayer_C*& InputPromptReference);
    void UpdateShieldAmount(double NewShieldAmount, bool UpdateMaxShield?, double NewMaxShieldAmount);
    void UpdateHealthAmount(double NewHealthAmount, bool UpdateMaxHealth?, double NewMaxHealthAmount);
    void DisplayShieldBar(bool DisplayShield?, double CurrentShield, double MaximumShield);
    void DisplayHealthBar(bool DisplayHealth?, double CurrentHealth, double MaximumHealth);
}; // Size: 0x28

#endif
