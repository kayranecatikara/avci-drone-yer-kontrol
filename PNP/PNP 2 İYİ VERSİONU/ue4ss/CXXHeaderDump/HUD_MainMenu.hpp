#ifndef UE4SS_SDK_HUD_MainMenu_HPP
#define UE4SS_SDK_HUD_MainMenu_HPP

class AHUD_MainMenu_C : public AHUD
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0398 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x03A0 (size: 0x8)
    class UWBP_MainMenu_C* WBP Main Menu;                                             // 0x03A8 (size: 0x8)
    class UWBP_LoadingScreenSelf_C* WBP Loading Screen;                               // 0x03B0 (size: 0x8)
    class UWBP_LevelSelection_C* WBP Level Selection;                                 // 0x03B8 (size: 0x8)
    class UWBP_UAVSelection_C* WBP Drone Selection;                                   // 0x03C0 (size: 0x8)
    class UWBP_ControlMenu_C* WBP Control Menu;                                       // 0x03C8 (size: 0x8)
    class UWBP_ScoreboardBase_C* WBP Scoreboard Base;                                 // 0x03D0 (size: 0x8)
    class UWBP_PressAnyButton_C* WBP Press Any Button;                                // 0x03D8 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x03E0 (size: 0x8)
    class UWBP_SettingsMenu_C* WBP Settings Menu;                                     // 0x03E8 (size: 0x8)

    void SetVisiblityLoadingScreen(bool Show);
    void SetVisibilityLevelSelection(bool Show);
    void SetVisibilityDroneSelection(bool Show);
    void SetVisibilityControlMenu(bool Show);
    void SetVisibilityMainMenu(bool Show);
    void ReceiveBeginPlay();
    void SetShowHideScoreboardInformation(bool Show);
    void SetVisibilitySettingsMenu(bool Show);
    void ExecuteUbergraph_HUD_MainMenu(int32 EntryPoint);
}; // Size: 0x3F0

#endif
