#ifndef UE4SS_SDK_BP_EasyMainMenuController_HPP
#define UE4SS_SDK_BP_EasyMainMenuController_HPP

class ABP_EasyMainMenuController_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UBillboardComponent* Billboard;                                             // 0x0330 (size: 0x8)
    class USceneComponent* Scene;                                                     // 0x0338 (size: 0x8)
    class APlayerController* PlayerControllerRef;                                     // 0x0340 (size: 0x8)
    class UWBP_EasyMainMenu_C* MainMenuWidgetRef;                                     // 0x0348 (size: 0x8)
    TMap<class TSoftObjectPtr<AActor>, class FS_MainMenuCameraBindings> TargetCameraBindings; // 0x0350 (size: 0x50)
    TArray<class AActor*> TargetCameras;                                              // 0x03A0 (size: 0x10)
    TArray<FS_MainMenuCameraBindings> CameraBindingsValues;                           // 0x03B0 (size: 0x10)

    void AnyButtonFocused(int32 ButtonIndex);
    void SetViewpointToCamera(int32 RequestedCamera, float BlendTime);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_BP_EasyMainMenuController(int32 EntryPoint);
}; // Size: 0x3C0

#endif
