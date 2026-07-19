#ifndef UE4SS_SDK_WBP_MainUAV_HPP
#define UE4SS_SDK_WBP_MainUAV_HPP

class UWBP_MainUAV_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBorder* Border_FinishRace;                                                 // 0x02D8 (size: 0x8)
    class UBackgroundBlur* CardFinish_Blur;                                           // 0x02E0 (size: 0x8)
    class UImage* Image_Battery1;                                                     // 0x02E8 (size: 0x8)
    class UImage* Image_Battery2;                                                     // 0x02F0 (size: 0x8)
    class UImage* Image_CrashUI;                                                      // 0x02F8 (size: 0x8)
    class UImage* Image_Crosshair;                                                    // 0x0300 (size: 0x8)
    class UImage* Image_FiberCamera;                                                  // 0x0308 (size: 0x8)
    class UImage* Image_JammerUI;                                                     // 0x0310 (size: 0x8)
    class UImage* Image_LeftJoystick;                                                 // 0x0318 (size: 0x8)
    class UImage* Image_LeftJoystickBG;                                               // 0x0320 (size: 0x8)
    class UImage* Image_LockKit1;                                                     // 0x0328 (size: 0x8)
    class UImage* Image_LockKit2;                                                     // 0x0330 (size: 0x8)
    class UImage* Image_RightJoystick;                                                // 0x0338 (size: 0x8)
    class UImage* Image_RightJoystickBG;                                              // 0x0340 (size: 0x8)
    class UImage* Image_TargetLock;                                                   // 0x0348 (size: 0x8)
    class UImage* Image_WindUI;                                                       // 0x0350 (size: 0x8)
    class UProgressBar* ProgressBar_Battery1;                                         // 0x0358 (size: 0x8)
    class UProgressBar* ProgressBar_Battery2;                                         // 0x0360 (size: 0x8)
    class UTextBlock* Text_AirSpeed;                                                  // 0x0368 (size: 0x8)
    class UTextBlock* Text_AirSpeed_1;                                                // 0x0370 (size: 0x8)
    class UTextBlock* Text_AirSpeed_2;                                                // 0x0378 (size: 0x8)
    class UTextBlock* Text_ALTValue;                                                  // 0x0380 (size: 0x8)
    class UTextBlock* Text_Arm_Notice;                                                // 0x0388 (size: 0x8)
    class UTextBlock* Text_Battery_1;                                                 // 0x0390 (size: 0x8)
    class UTextBlock* Text_Battery_2;                                                 // 0x0398 (size: 0x8)
    class UTextBlock* Text_Current1;                                                  // 0x03A0 (size: 0x8)
    class UTextBlock* Text_Current2;                                                  // 0x03A8 (size: 0x8)
    class UTextBlock* Text_Distance;                                                  // 0x03B0 (size: 0x8)
    class UTextBlock* Text_DistanceInitial;                                           // 0x03B8 (size: 0x8)
    class UTextBlock* Text_DistanceValue;                                             // 0x03C0 (size: 0x8)
    class UTextBlock* Text_FlightMode;                                                // 0x03C8 (size: 0x8)
    class UTextBlock* Text_GroundSpeed;                                               // 0x03D0 (size: 0x8)
    class UTextBlock* Text_GroundSpeedG;                                              // 0x03D8 (size: 0x8)
    class UTextBlock* Text_GroundSpeeds;                                              // 0x03E0 (size: 0x8)
    class UTextBlock* Text_Heading;                                                   // 0x03E8 (size: 0x8)
    class UTextBlock* Text_Hover;                                                     // 0x03F0 (size: 0x8)
    class UTextBlock* Text_LOW_VOLTAGE;                                               // 0x03F8 (size: 0x8)
    class UTextBlock* Text_LQ;                                                        // 0x0400 (size: 0x8)
    class UTextBlock* Text_Navigation;                                                // 0x0408 (size: 0x8)
    class UTextBlock* Text_RaceCheckpoint;                                            // 0x0410 (size: 0x8)
    class UTextBlock* Text_RaceTimer;                                                 // 0x0418 (size: 0x8)
    class UTextBlock* Text_RX_LOSS;                                                   // 0x0420 (size: 0x8)
    class UTextBlock* Text_Speed;                                                     // 0x0428 (size: 0x8)
    class UTextBlock* Text_ThrottlePercent;                                           // 0x0430 (size: 0x8)
    class UTextBlock* Text_Timer_Mİnutes;                                             // 0x0438 (size: 0x8)
    class UTextBlock* Text_Timer_Seconds;                                             // 0x0440 (size: 0x8)
    class UTextBlock* TextBlock_Arm;                                                  // 0x0448 (size: 0x8)
    class UTextBlock* TextBlock_Trigger;                                              // 0x0450 (size: 0x8)
    class ABPP_UAV_C* BPP UAV;                                                        // 0x0458 (size: 0x8)
    int32 Seconds;                                                                    // 0x0460 (size: 0x4)
    int32 Minutes;                                                                    // 0x0464 (size: 0x4)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0468 (size: 0x8)
    class AGM_UAVBase_C* GM UAV Base;                                                 // 0x0470 (size: 0x8)
    double RaceTimer;                                                                 // 0x0478 (size: 0x8)
    class UBP_SaveGame_ScoreBoard_C* BP Save Game Score Board;                        // 0x0480 (size: 0x8)
    class ABPP_UAV_Drone_C* As BPP UAV Drone;                                         // 0x0488 (size: 0x8)

    FText Get_Text_Current2_Text();
    FText Set Current1 Text();
    FText Get_Text_AirSpeed_3_Text();
    FText Set GroundSpeed Text();
    FText Set ThrottlePercent Text();
    FText Set Heading Text();
    FText Distance();
    FText SignalText();
    FText Set Timer Mİnutes();
    FText Set Timer Seconds();
    void M to Text(double Meters, FText& NewParam);
    FText Set Altitude Text();
    FText Set Speed Text();
    void Construct();
    void ResetFlyMin();
    void SetArmText(bool IsArmOn);
    void SetVisibilityJammerIcon(bool Show);
    void SetVisibilityWindIcon(bool Show);
    void SetVisibilityLock1Icon(bool Show);
    void SetVisibilityLock2Icon(bool Show);
    void SetShowHideCrosshair(ESlateVisibility Visibility);
    void ShowArmModeText(ESlateVisibility Visibility);
    void SetTriggerText(bool isShow);
    void UpdateAxisControllers();
    void FlyMinTimer();
    void TargetLockUI(double In Size, bool isLock);
    void SetVisibilityTargetLockUI(ESlateVisibility InVisibility);
    void SetVisibilityLockSquare(bool Show);
    void UpdateBatteryInfos();
    void SetVisibilityCrashIcon(bool Show);
    void Hover();
    void LQ();
    void CallResetBatteryInfo();
    void SetBatteryInfo(float Percent, double FirstBattery, double SecondBattery);
    void UpdateRaceCheckpointCount();
    void UpdateRaceTimer();
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void ResetTimer();
    void SetFlightModeText(TEnumAsByte<E_UAV_FlightMode::Type> UAV Flight Mode);
    void UpdateFinishCard(bool isFinish);
    void SetInitialBatteryValues();
    void ExecuteUbergraph_WBP_MainUAV(int32 EntryPoint);
}; // Size: 0x490

#endif
