#ifndef UE4SS_SDK_WBP_ScoreBoard_HPP
#define UE4SS_SDK_WBP_ScoreBoard_HPP

class UWBP_ScoreBoard_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* Intro;                                                    // 0x02D8 (size: 0x8)
    class URetainerBox* RetainerBox_2;                                                // 0x02E0 (size: 0x8)
    class UTextBlock* Text_ControllerName;                                            // 0x02E8 (size: 0x8)
    class UTextBlock* Text_ControllerType;                                            // 0x02F0 (size: 0x8)
    class UTextBlock* Text_Count_Drone;                                               // 0x02F8 (size: 0x8)
    class UTextBlock* Text_Count_FixedGun;                                            // 0x0300 (size: 0x8)
    class UTextBlock* Text_Count_Heavy;                                               // 0x0308 (size: 0x8)
    class UTextBlock* Text_Count_Helicopter;                                          // 0x0310 (size: 0x8)
    class UTextBlock* Text_Count_Soldier;                                             // 0x0318 (size: 0x8)
    class UTextBlock* Text_Count_Vehicle;                                             // 0x0320 (size: 0x8)
    class UTextBlock* Text_CrashC;                                                    // 0x0328 (size: 0x8)
    class UTextBlock* Text_DroneType;                                                 // 0x0330 (size: 0x8)
    class UTextBlock* Text_EnemyKilledC;                                              // 0x0338 (size: 0x8)
    class UTextBlock* Text_EnemyLeftC;                                                // 0x0340 (size: 0x8)
    class UTextBlock* Text_ExplosiveType;                                             // 0x0348 (size: 0x8)
    class UTextBlock* Text_FailC;                                                     // 0x0350 (size: 0x8)
    class UTextBlock* Text_MapMode;                                                   // 0x0358 (size: 0x8)
    class UTextBlock* Text_MapName;                                                   // 0x0360 (size: 0x8)
    class UTextBlock* Text_SuccessC;                                                  // 0x0368 (size: 0x8)
    class UTextBlock* Text_TotalEnemyC;                                               // 0x0370 (size: 0x8)
    class UTextBlock* TextBlock_CurrentTime;                                          // 0x0378 (size: 0x8)
    FTimerHandle TimerHandle;                                                         // 0x0380 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0388 (size: 0x8)
    TMap<FString, int32> ComboBoxSelection;                                           // 0x0390 (size: 0x50)
    class UComboBoxString* ComboBox_Controllers;                                      // 0x03E0 (size: 0x8)
    class AGM_UAVBase_C* GM Main Drone Base;                                          // 0x03E8 (size: 0x8)

    void Construct();
    void SetBoardValue();
    void Destruct();
    void RestartOnce();
    void ondeviceDetachedEventDelegate_Event_0(FSimpleControllerDevice device, int32 connectionIndex);
    void ondeviceAttachedEventDelegate_Event_0(FSimpleControllerDevice device, int32 connectionIndex);
    void ExecuteUbergraph_WBP_ScoreBoard(int32 EntryPoint);
}; // Size: 0x3F0

#endif
