#ifndef UE4SS_SDK_BP_EPM_PhotoModeController_HPP
#define UE4SS_SDK_BP_EPM_PhotoModeController_HPP

class ABP_EPM_PhotoModeController_C : public ASpectatorPawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0350 (size: 0x8)
    class UCineCameraComponent* CineCamera;                                           // 0x0358 (size: 0x8)
    class UWBP_EasyPhotoMode_C* PhotoModeWidget;                                      // 0x0360 (size: 0x8)
    FBP_EPM_PhotoModeController_CPhotoModeClosed PhotoModeClosed;                     // 0x0368 (size: 0x10)
    void PhotoModeClosed();
    class APlayerController* PlayerControllerRef;                                     // 0x0378 (size: 0x8)
    FTransform SpawnLocation;                                                         // 0x0380 (size: 0x60)
    FRotator ControlCameraRotation;                                                   // 0x03E0 (size: 0x18)
    class APawn* BasePlayerCharacter;                                                 // 0x03F8 (size: 0x8)
    double MaxCameraRange;                                                            // 0x0400 (size: 0x8)
    class AHUD* HUD;                                                                  // 0x0408 (size: 0x8)
    TArray<class ABP_EPM_CameraBlockingVolume_C*> BlockingVolumes;                    // 0x0410 (size: 0x10)
    FString CurrentScreenshotFilename;                                                // 0x0420 (size: 0x10)
    TEnumAsByte<E_ScreenshotsSaveLocation::Type> ScreenshotDirectoryType;             // 0x0430 (size: 0x1)
    FString ScreenshotsDirectory;                                                     // 0x0438 (size: 0x10)
    bool CaptureThumbnail?;                                                           // 0x0448 (size: 0x1)
    class USoundClass* MasterSoundClass;                                              // 0x0450 (size: 0x8)
    class USoundMix* MuteSoundMix;                                                    // 0x0458 (size: 0x8)
    bool GalleryOpened?;                                                              // 0x0460 (size: 0x1)
    class UWBP_EPM_Gallery_C* GalleryUI;                                              // 0x0468 (size: 0x8)
    FHitResult FocusLineTraceHit;                                                     // 0x0470 (size: 0x100)
    TEnumAsByte<E_ScreenshotCaptureMethod::Type> ScreenshotsCaptureMethod;            // 0x0570 (size: 0x1)
    class USceneCaptureComponent2D* SceneCaptureComponent;                            // 0x0578 (size: 0x8)
    FVector2D ScreenResolution;                                                       // 0x0580 (size: 0x10)
    FIntPoint FinalResolution;                                                        // 0x0590 (size: 0x8)
    int32 WarmUpFrames;                                                               // 0x0598 (size: 0x4)
    TSoftObjectPtr<UTextureRenderTarget2D> RenderTargetTexture;                       // 0x05A0 (size: 0x28)
    bool ClampCameraRange?;                                                           // 0x05C8 (size: 0x1)

    void ClosePhotoMode();
    void UpdateMappingContexts(bool EditionMode?);
    double GetClampedFloat(double CurrentLocation, double SpawnLocation);
    void InpActEvt_IA_TakePhoto_K2Node_EnhancedInputActionEvent_8(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_ResetPhotoMode_K2Node_EnhancedInputActionEvent_7(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_HidePhotoUI_K2Node_EnhancedInputActionEvent_6(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_SwitchMode_K2Node_EnhancedInputActionEvent_5(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_PhotoModeVerticalMovement_K2Node_EnhancedInputActionEvent_4(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void OnLoaded_7EC0AA904C90D3B5E76636A07A187B7D(class UObject* Loaded);
    void InpActEvt_IA_FocusLocation_K2Node_EnhancedInputActionEvent_3(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_PhotoModeLook_K2Node_EnhancedInputActionEvent_2(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_PhotoModeMovement_K2Node_EnhancedInputActionEvent_1(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void InpActEvt_IA_LocatePhotosFolder_K2Node_EnhancedInputActionEvent_0(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime, const class UInputAction* SourceAction);
    void ReceiveBeginPlay();
    void GalleryClosed();
    void ReceiveDestroyed();
    void TakePhoto();
    void ExecuteUbergraph_BP_EPM_PhotoModeController(int32 EntryPoint);
    void PhotoModeClosed__DelegateSignature();
}; // Size: 0x5C9

#endif
