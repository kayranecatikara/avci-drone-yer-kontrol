#ifndef UE4SS_SDK_BPI_EGUI_HUDInterface_HPP
#define UE4SS_SDK_BPI_EGUI_HUDInterface_HPP

class IBPI_EGUI_HUDInterface_C : public IInterface
{

    void EscapeReleased();
    void BlockNavBackUntilEscapeRelease();
    void RestoreAudioVolumeSoundModifier();
    void RestoreRemovedGameplayMappingContexts();
    void UpdatePlayerCameraFOV(double& AppliedFOV);
    void SaveUserSettingsToDisk(bool& Success?);
    void GetUserSettings(FJsonObjectWrapper& UserSettings);
    void RemoveAllGameplayInputMappingContexts();
    void AddAllGameplayInputMappingContexts();
    void GetCanSpawnPhotoMode?(bool& CanSpawnPhotoMode?);
    void SetCanSpawnPhotoMode(bool CanSpawnPhotoMode?);
    class UWBP_EasyGameCreditsMain_C* PlayCredits(FString ConfigPresetToUse);
    class UWBP_ESGU_SavesManagerUI_C* OpenSavesManagerUI(TEnumAsByte<E_SaveGameOperationType::Type> OperationType);
    void OpenPhotoMode(class ABP_EPM_PhotoModeController_C*& PhotoModeController);
    void OpenOptionsMenu(class UWBP_EasyOptionsMenuMain_C*& Return Value);
    void OpenPauseMenu(bool ResetInputsOnClose?, class UUserWidget*& Return Value);
    void OpenMainMenu(class ABP_EasyMainMenuController_C* MainMenuController, class UUserWidget*& Return Value);
    void SetFocusLoss(bool FocusLost?);
    void CloseAlertBanner(class UUserWidget* UnderlyingWidget, class UWidget* ElementToRefocus);
    void SetupAlertBanner(class UUserWidget* UnderlyingWidget, FS_AlertBannerSetupInfos AlertBannerSetupInfos, bool IsInputModeGameAndUI?, class UWBP_EGUI_CommonAlertBanner_C*& BannerWidget);
    void HandleCursorVisibility(bool ShouldHideMouseCursor?);
    FEventReply HandleMouseMovementDetection(const FPointerEvent& MouseEvent, TSoftObjectPtr<UUserWidget> InstigatorWidget);
    void HandleFocusLoss(const FKey Key, class UWidget* ElementToRefocus);
    void InitializeFocusHandling(class UUserWidget* WidgetReference, class UWidget* InitialElementToFocus, bool RegisterInputListener?, bool SetInputModeGameAndUI?);
    void UnregisterInputListener(TSoftObjectPtr<UUserWidget> Widget);
    void RegisterInputListener(TSoftObjectPtr<UUserWidget> Widget);
    void SetAndApplyUpscalingMethods(TEnumAsByte<E_UpscalingMethods::Type> RequestedUpscalingMethod, TEnumAsByte<E_AntiAliasingMethods::Type> RequestedAA_Method);
}; // Size: 0x28

#endif
