#ifndef UE4SS_SDK_GM_MainMenu_HPP
#define UE4SS_SDK_GM_MainMenu_HPP

class AGM_MainMenu_C : public AGameModeBase
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0340 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0348 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0350 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0358 (size: 0x8)

    void GetScoreBoardData();
    void LoadGameScoreboard(class UBP_SaveGame_ScoreBoard_C* Save Game Scoreboard);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_GM_MainMenu(int32 EntryPoint);
}; // Size: 0x360

#endif
