#ifndef UE4SS_SDK_BPP_Spectator_HPP
#define UE4SS_SDK_BPP_Spectator_HPP

class ABPP_Spectator_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class USpectatorTrackingComponent* SpectatorTracking;                             // 0x0330 (size: 0x8)
    class UCineCameraComponent* CineCamera;                                           // 0x0338 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0340 (size: 0x8)
    double SpectatorSpeed;                                                            // 0x0348 (size: 0x8)
    double ZoomSpeed;                                                                 // 0x0350 (size: 0x8)
    class ABPP_UAV_C* BPP MainDrone;                                                  // 0x0358 (size: 0x8)
    class AHUD_MainUAV_C* HUD Main Drone;                                             // 0x0360 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0368 (size: 0x8)
    double Reverse Throttle Axis;                                                     // 0x0370 (size: 0x8)
    double Reverse Pitch Axis;                                                        // 0x0378 (size: 0x8)
    double Reverse Yaw Axis;                                                          // 0x0380 (size: 0x8)
    bool isCompletedLevel;                                                            // 0x0388 (size: 0x1)
    bool canRotate;                                                                   // 0x0389 (size: 0x1)
    float SpawnDroneAxisInput;                                                        // 0x038C (size: 0x4)
    float PitchAxisInput;                                                             // 0x0390 (size: 0x4)
    float ZoomAxisInput;                                                              // 0x0394 (size: 0x4)
    float YawAxisInput;                                                               // 0x0398 (size: 0x4)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x03A0 (size: 0x8)
    bool Crashed;                                                                     // 0x03A8 (size: 0x1)
    class AActor* Target;                                                             // 0x03B0 (size: 0x8)
    FCameraFocusSettings Focus Settings;                                              // 0x03B8 (size: 0x60)

    void leftDpadReleased_E7B710F149BA11720448C5AEB567E56B();
    void leftDpadPressed_E7B710F149BA11720448C5AEB567E56B();
    void rightDpadReleased_E7B710F149BA11720448C5AEB567E56B();
    void rightDpadPressed_E7B710F149BA11720448C5AEB567E56B();
    void topDpadReleased_E7B710F149BA11720448C5AEB567E56B();
    void topDpadPressed_E7B710F149BA11720448C5AEB567E56B();
    void bottomDpadReleased_E7B710F149BA11720448C5AEB567E56B();
    void bottomDpadPressed_E7B710F149BA11720448C5AEB567E56B();
    void actionReleased_E1FCD34540B0A2CA78449E9B38EF0C83();
    void actionPressed_E1FCD34540B0A2CA78449E9B38EF0C83();
    void InpActEvt_E_K2Node_InputKeyEvent_3(FKey Key);
    void InpActEvt_Tab_K2Node_InputKeyEvent_2(FKey Key);
    void InpActEvt_Tab_K2Node_InputKeyEvent_1(FKey Key);
    void InpActEvt_Escape_K2Node_InputKeyEvent_0(FKey Key);
    void onAction_7B2EFCD44879D68D516A57B11BD6E251(const float AxisValue);
    void onAction_F60342974C4CD2E3F4A35D80E8E29F2E(const float AxisValue);
    void onAction_90427C0245DE4EAA58138E9ED0888F76(const float AxisValue);
    void onAction_7B71C67F489E058981AB61851A38E600(const float AxisValue);
    void failed_9B71C67E41AC31D2683779A46D997440();
    void successful_9B71C67E41AC31D2683779A46D997440();
    void SetFocusCamera();
    void CompletedLevel();
    void ReceiveBeginPlay();
    void InpAxisEvt_I_KeyboardSpecSoom_K2Node_InputAxisEvent_3(float AxisValue);
    void InpAxisEvt_I_KeyboardSpecPitch_K2Node_InputAxisEvent_1(float AxisValue);
    void InpAxisEvt_I_KeyboardSpecYaw_K2Node_InputAxisEvent_0(float AxisValue);
    void Spawn Drone(double Spawn Drone Axis Input);
    void CameraZoom(double Zoom Axis Input);
    void CameraRotationLook(float Yaw Axis Input, double Pitch Axis Input);
    void ExecuteUbergraph_BPP_Spectator(int32 EntryPoint);
}; // Size: 0x418

#endif
