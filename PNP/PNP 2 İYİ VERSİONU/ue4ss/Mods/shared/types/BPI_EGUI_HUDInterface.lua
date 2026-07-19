---@meta

---@class IBPI_EGUI_HUDInterface_C : IInterface
local IBPI_EGUI_HUDInterface_C = {}

function IBPI_EGUI_HUDInterface_C:EscapeReleased() end
function IBPI_EGUI_HUDInterface_C:BlockNavBackUntilEscapeRelease() end
function IBPI_EGUI_HUDInterface_C:RestoreAudioVolumeSoundModifier() end
function IBPI_EGUI_HUDInterface_C:RestoreRemovedGameplayMappingContexts() end
---@param AppliedFOV double
function IBPI_EGUI_HUDInterface_C:UpdatePlayerCameraFOV(AppliedFOV) end
---@param Success_ boolean
function IBPI_EGUI_HUDInterface_C:SaveUserSettingsToDisk(Success_) end
---@param UserSettings FJsonObjectWrapper
function IBPI_EGUI_HUDInterface_C:GetUserSettings(UserSettings) end
function IBPI_EGUI_HUDInterface_C:RemoveAllGameplayInputMappingContexts() end
function IBPI_EGUI_HUDInterface_C:AddAllGameplayInputMappingContexts() end
---@param CanSpawnPhotoMode_ boolean
IBPI_EGUI_HUDInterface_C['GetCanSpawnPhotoMode?'] = function(self, CanSpawnPhotoMode_) end
---@param CanSpawnPhotoMode_ boolean
function IBPI_EGUI_HUDInterface_C:SetCanSpawnPhotoMode(CanSpawnPhotoMode_) end
---@param ConfigPresetToUse FString
---@return UWBP_EasyGameCreditsMain_C
function IBPI_EGUI_HUDInterface_C:PlayCredits(ConfigPresetToUse) end
---@param OperationType E_SaveGameOperationType::Type
---@return UWBP_ESGU_SavesManagerUI_C
function IBPI_EGUI_HUDInterface_C:OpenSavesManagerUI(OperationType) end
---@param PhotoModeController ABP_EPM_PhotoModeController_C
function IBPI_EGUI_HUDInterface_C:OpenPhotoMode(PhotoModeController) end
---@param Return_Value UWBP_EasyOptionsMenuMain_C
function IBPI_EGUI_HUDInterface_C:OpenOptionsMenu(Return_Value) end
---@param ResetInputsOnClose_ boolean
---@param Return_Value UUserWidget
function IBPI_EGUI_HUDInterface_C:OpenPauseMenu(ResetInputsOnClose_, Return_Value) end
---@param MainMenuController ABP_EasyMainMenuController_C
---@param Return_Value UUserWidget
function IBPI_EGUI_HUDInterface_C:OpenMainMenu(MainMenuController, Return_Value) end
---@param FocusLost_ boolean
function IBPI_EGUI_HUDInterface_C:SetFocusLoss(FocusLost_) end
---@param UnderlyingWidget UUserWidget
---@param ElementToRefocus UWidget
function IBPI_EGUI_HUDInterface_C:CloseAlertBanner(UnderlyingWidget, ElementToRefocus) end
---@param UnderlyingWidget UUserWidget
---@param AlertBannerSetupInfos FS_AlertBannerSetupInfos
---@param IsInputModeGameAndUI_ boolean
---@param BannerWidget UWBP_EGUI_CommonAlertBanner_C
function IBPI_EGUI_HUDInterface_C:SetupAlertBanner(UnderlyingWidget, AlertBannerSetupInfos, IsInputModeGameAndUI_, BannerWidget) end
---@param ShouldHideMouseCursor_ boolean
function IBPI_EGUI_HUDInterface_C:HandleCursorVisibility(ShouldHideMouseCursor_) end
---@param MouseEvent FPointerEvent
---@param InstigatorWidget TSoftObjectPtr<UUserWidget>
---@return FEventReply
function IBPI_EGUI_HUDInterface_C:HandleMouseMovementDetection(MouseEvent, InstigatorWidget) end
---@param Key FKey
---@param ElementToRefocus UWidget
function IBPI_EGUI_HUDInterface_C:HandleFocusLoss(Key, ElementToRefocus) end
---@param WidgetReference UUserWidget
---@param InitialElementToFocus UWidget
---@param RegisterInputListener_ boolean
---@param SetInputModeGameAndUI_ boolean
function IBPI_EGUI_HUDInterface_C:InitializeFocusHandling(WidgetReference, InitialElementToFocus, RegisterInputListener_, SetInputModeGameAndUI_) end
---@param Widget TSoftObjectPtr<UUserWidget>
function IBPI_EGUI_HUDInterface_C:UnregisterInputListener(Widget) end
---@param Widget TSoftObjectPtr<UUserWidget>
function IBPI_EGUI_HUDInterface_C:RegisterInputListener(Widget) end
---@param RequestedUpscalingMethod E_UpscalingMethods::Type
---@param RequestedAA_Method E_AntiAliasingMethods::Type
function IBPI_EGUI_HUDInterface_C:SetAndApplyUpscalingMethods(RequestedUpscalingMethod, RequestedAA_Method) end


