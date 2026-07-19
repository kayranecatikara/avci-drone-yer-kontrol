---@meta

---@class ABP_EPM_PhotoModeController_C : ASpectatorPawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field CineCamera UCineCameraComponent
---@field PhotoModeWidget UWBP_EasyPhotoMode_C
---@field PhotoModeClosed FBP_EPM_PhotoModeController_CPhotoModeClosed
---@field PlayerControllerRef APlayerController
---@field SpawnLocation FTransform
---@field ControlCameraRotation FRotator
---@field BasePlayerCharacter APawn
---@field MaxCameraRange double
---@field HUD AHUD
---@field BlockingVolumes TArray<ABP_EPM_CameraBlockingVolume_C>
---@field CurrentScreenshotFilename FString
---@field ScreenshotDirectoryType E_ScreenshotsSaveLocation::Type
---@field ScreenshotsDirectory FString
---@field ['CaptureThumbnail?'] boolean
---@field MasterSoundClass USoundClass
---@field MuteSoundMix USoundMix
---@field ['GalleryOpened?'] boolean
---@field GalleryUI UWBP_EPM_Gallery_C
---@field FocusLineTraceHit FHitResult
---@field ScreenshotsCaptureMethod E_ScreenshotCaptureMethod::Type
---@field SceneCaptureComponent USceneCaptureComponent2D
---@field ScreenResolution FVector2D
---@field FinalResolution FIntPoint
---@field WarmUpFrames int32
---@field RenderTargetTexture TSoftObjectPtr<UTextureRenderTarget2D>
---@field ['ClampCameraRange?'] boolean
local ABP_EPM_PhotoModeController_C = {}

function ABP_EPM_PhotoModeController_C:ClosePhotoMode() end
---@param EditionMode_ boolean
function ABP_EPM_PhotoModeController_C:UpdateMappingContexts(EditionMode_) end
---@param CurrentLocation double
---@param SpawnLocation double
---@return double
function ABP_EPM_PhotoModeController_C:GetClampedFloat(CurrentLocation, SpawnLocation) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_TakePhoto_K2Node_EnhancedInputActionEvent_8(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_ResetPhotoMode_K2Node_EnhancedInputActionEvent_7(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_HidePhotoUI_K2Node_EnhancedInputActionEvent_6(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_SwitchMode_K2Node_EnhancedInputActionEvent_5(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_PhotoModeVerticalMovement_K2Node_EnhancedInputActionEvent_4(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param Loaded UObject
function ABP_EPM_PhotoModeController_C:OnLoaded_7EC0AA904C90D3B5E76636A07A187B7D(Loaded) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_FocusLocation_K2Node_EnhancedInputActionEvent_3(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_PhotoModeLook_K2Node_EnhancedInputActionEvent_2(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_PhotoModeMovement_K2Node_EnhancedInputActionEvent_1(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
---@param ActionValue FInputActionValue
---@param ElapsedTime float
---@param TriggeredTime float
---@param SourceAction UInputAction
function ABP_EPM_PhotoModeController_C:InpActEvt_IA_LocatePhotosFolder_K2Node_EnhancedInputActionEvent_0(ActionValue, ElapsedTime, TriggeredTime, SourceAction) end
function ABP_EPM_PhotoModeController_C:ReceiveBeginPlay() end
function ABP_EPM_PhotoModeController_C:GalleryClosed() end
function ABP_EPM_PhotoModeController_C:ReceiveDestroyed() end
function ABP_EPM_PhotoModeController_C:TakePhoto() end
---@param EntryPoint int32
function ABP_EPM_PhotoModeController_C:ExecuteUbergraph_BP_EPM_PhotoModeController(EntryPoint) end
function ABP_EPM_PhotoModeController_C:PhotoModeClosed__DelegateSignature() end


