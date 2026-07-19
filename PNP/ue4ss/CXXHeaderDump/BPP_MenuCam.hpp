#ifndef UE4SS_SDK_BPP_MenuCam_HPP
#define UE4SS_SDK_BPP_MenuCam_HPP

class ABPP_MenuCam_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class USceneCaptureComponent2D* ControllerCapture;                                // 0x0330 (size: 0x8)
    class URectLightComponent* RectLight_Controller;                                  // 0x0338 (size: 0x8)
    class URectLightComponent* RectLight_UAV;                                         // 0x0340 (size: 0x8)
    class USkeletalMeshComponent* SKM_RadioMasterPocket;                              // 0x0348 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_Propeller2;                                 // 0x0350 (size: 0x8)
    class UStaticMeshComponent* SM_Battery;                                           // 0x0358 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_Propeller3;                                 // 0x0360 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_Propeller4;                                 // 0x0368 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_Propeller1;                                 // 0x0370 (size: 0x8)
    class UStaticMeshComponent* SM_SDrone_7";                                         // 0x0378 (size: 0x8)
    class USceneCaptureComponent2D* DroneCapture;                                     // 0x0380 (size: 0x8)
    class UInterpToMovementComponent* InterpToMovement;                               // 0x0388 (size: 0x8)
    class UCineCameraComponent* CineCamera;                                           // 0x0390 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0398 (size: 0x8)
    float Timeline_0_NewTrack_1_ECFCA1434AEC619FA50765BBC9FDFB3D;                     // 0x03A0 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline_0__Direction_ECFCA1434AEC619FA50765BBC9FDFB3D; // 0x03A4 (size: 0x1)
    class UTimelineComponent* Timeline_0;                                             // 0x03A8 (size: 0x8)
    float Timeline_NewTrack_1_57CB5A8749D785A25D67F4861D580833;                       // 0x03B0 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline__Direction_57CB5A8749D785A25D67F4861D580833; // 0x03B4 (size: 0x1)
    class UTimelineComponent* Timeline;                                               // 0x03B8 (size: 0x8)
    float Timeline_2_NewTrack_0_FC2FE8794C67D3B47807F7A5B40334C5;                     // 0x03C0 (size: 0x4)
    TEnumAsByte<ETimelineDirection::Type> Timeline_2__Direction_FC2FE8794C67D3B47807F7A5B40334C5; // 0x03C4 (size: 0x1)
    class UTimelineComponent* Timeline_2;                                             // 0x03C8 (size: 0x8)
    FTransform DroneTransform;                                                        // 0x03D0 (size: 0x60)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0430 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0438 (size: 0x8)
    double MaximumDegree;                                                             // 0x0440 (size: 0x8)
    double MinumumDegree;                                                             // 0x0448 (size: 0x8)
    double RollAxisInput;                                                             // 0x0450 (size: 0x8)
    double PitchAxisInput;                                                            // 0x0458 (size: 0x8)
    double ThrottleAxisInput;                                                         // 0x0460 (size: 0x8)
    double YawAxisInput;                                                              // 0x0468 (size: 0x8)
    double DeadZone;                                                                  // 0x0470 (size: 0x8)
    FTransform InitialTransform;                                                      // 0x0480 (size: 0x60)
    FTransform UAVTransform;                                                          // 0x04E0 (size: 0x60)
    TEnumAsByte<E_MenuCameraPhases::Type> MenuCameraPhase;                            // 0x0540 (size: 0x1)
    FTransform MiniDroneTransform;                                                    // 0x0550 (size: 0x60)
    FRotator StartControlRotation;                                                    // 0x05B0 (size: 0x18)
    FRotator TargetControlRotation;                                                   // 0x05C8 (size: 0x18)
    bool isRotated;                                                                   // 0x05E0 (size: 0x1)

    void NormalizeDeadzone(double Input, double& Output);
    void Timeline_2__FinishedFunc();
    void Timeline_2__UpdateFunc();
    void Timeline__FinishedFunc();
    void Timeline__UpdateFunc();
    void Timeline_0__FinishedFunc();
    void Timeline_0__UpdateFunc();
    void failed_450A7522400B4CBB7613909D7157054F();
    void successful_450A7522400B4CBB7613909D7157054F();
    void onAction_CAF3C7E84B78055A99946E98035BF4B6(const float AxisValue);
    void onAction_347FAD934BDC8F7A39A48998768D5735(const float AxisValue);
    void onAction_2AA3B148420E2A12DB44E9A8AF67BFEA(const float AxisValue);
    void onAction_25E518404515131C72411D983ECAFCFD(const float AxisValue);
    void ReceiveBeginPlay();
    void MoveToCam(bool isMenu, TEnumAsByte<E_MenuCameraPhases::Type> Target);
    void LoadedData_Event();
    void MoveToLocation(FVector CurrentLocation, FRotator CurrentRotation, FVector TargetLocation, FRotator TargetRotation);
    void MoveToDroneSection();
    void SetFocusSettings(TEnumAsByte<E_MenuCameraPhases::Type> Index);
    void RotateController(bool isNormal);
    void MovementYawAxis(double YawAxisInput);
    void MovementThrottleAxis(double ThrottleAxisInput);
    void MovementPitchAxis(double RollAxisInput);
    void MovementRollAxis(double PitchAxisInput);
    void ExecuteUbergraph_BPP_MenuCam(int32 EntryPoint);
}; // Size: 0x5E1

#endif
