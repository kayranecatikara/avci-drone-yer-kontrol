#ifndef UE4SS_SDK_WBP_GlobalUI_HPP
#define UE4SS_SDK_WBP_GlobalUI_HPP

class UWBP_GlobalUI_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UVerticalBox* VerticalBox_AmmunationInformation;                            // 0x02D8 (size: 0x8)
    class UWBP_KillFeedPanel_C* WBP_KillFeedPanel;                                    // 0x02E0 (size: 0x8)
    FText Text_InfoAmmo;                                                              // 0x02E8 (size: 0x10)
    FText Text_InfoFiberRope;                                                         // 0x02F8 (size: 0x10)

    void ShowAmmunitionInfo();
    void ShowFiberRopeInfo();
    void ExecuteUbergraph_WBP_GlobalUI(int32 EntryPoint);
}; // Size: 0x308

#endif
