#ifndef UE4SS_SDK_WBP_KillFeedItem_HPP
#define UE4SS_SDK_WBP_KillFeedItem_HPP

class UWBP_KillFeedItem_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* ItemAnim;                                                 // 0x02D8 (size: 0x8)
    class UImage* Image_Icon;                                                         // 0x02E0 (size: 0x8)
    class UTextBlock* TextBlock_Enemy;                                                // 0x02E8 (size: 0x8)
    class UTextBlock* TextBlock_EnemyCount;                                           // 0x02F0 (size: 0x8)
    class UTextBlock* TextBlock_PlayerName;                                           // 0x02F8 (size: 0x8)
    FText Text_PlayerName;                                                            // 0x0300 (size: 0x10)
    FText Text_EnemyName;                                                             // 0x0310 (size: 0x10)
    FText Text_EnemyCount;                                                            // 0x0320 (size: 0x10)
    FSlateBrush KamikazeBrush;                                                        // 0x0330 (size: 0xB0)
    bool isNet;                                                                       // 0x03E0 (size: 0x1)
    FSlateBrush NetBrush;                                                             // 0x03F0 (size: 0xB0)
    bool isFail;                                                                      // 0x04A0 (size: 0x1)

    void Finished_E9E0132B40781F5947424DBB6884375C();
    void Construct();
    void ExecuteUbergraph_WBP_KillFeedItem(int32 EntryPoint);
}; // Size: 0x4A1

#endif
