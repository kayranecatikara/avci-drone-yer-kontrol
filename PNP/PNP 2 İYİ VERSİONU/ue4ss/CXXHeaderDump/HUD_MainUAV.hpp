#ifndef UE4SS_SDK_HUD_MainUAV_HPP
#define UE4SS_SDK_HUD_MainUAV_HPP

class AHUD_MainUAV_C : public AHUD
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0398 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x03A0 (size: 0x8)
    class UWBP_MainUAV_C* WBP Main Drone;                                             // 0x03A8 (size: 0x8)
    class UWBP_SettingsMenu_C* WBP Settings Menu;                                     // 0x03B0 (size: 0x8)
    class UWBP_Spectator_C* WBP Spectator;                                            // 0x03B8 (size: 0x8)
    class UWBP_GlobalUI_C* WBP Global UI;                                             // 0x03C0 (size: 0x8)
    class UWBP_CompletedLevel_C* WBP Completed Level;                                 // 0x03C8 (size: 0x8)
    class UWBP_ScoreBoard_C* WBP Score Board;                                         // 0x03D0 (size: 0x8)
    class APC_SpectatorDroneBase_C* PC Spectator Drone Base;                          // 0x03D8 (size: 0x8)

    void SetShowHideMainDrone(bool Show);
    void SetShowHideSpectatorMenu(bool Show);
    void ShowHideSettingsMenu(bool Show);
    void SetVisibilityCompletedLevel(bool isFail);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_HUD_MainUAV(int32 EntryPoint);
}; // Size: 0x3E0

#endif
