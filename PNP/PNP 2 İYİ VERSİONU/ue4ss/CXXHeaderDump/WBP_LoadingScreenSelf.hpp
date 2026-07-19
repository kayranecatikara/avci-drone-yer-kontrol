#ifndef UE4SS_SDK_WBP_LoadingScreenSelf_HPP
#define UE4SS_SDK_WBP_LoadingScreenSelf_HPP

class UWBP_LoadingScreenSelf_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UImage* Image_Background;                                                   // 0x02D8 (size: 0x8)
    class UProgressBar* ProgressBar_0;                                                // 0x02E0 (size: 0x8)
    class UTextBlock* Text_LoadingPercent;                                            // 0x02E8 (size: 0x8)
    class UTextBlock* TextBlock_MapName;                                              // 0x02F0 (size: 0x8)
    class UBP_GameInstance_C* As BP Game Instance;                                    // 0x02F8 (size: 0x8)
    class UDataTable* DTMaps;                                                         // 0x0300 (size: 0x8)

    void UpdateProgressBarValue(double Percent);
    void Construct();
    void ExecuteUbergraph_WBP_LoadingScreenSelf(int32 EntryPoint);
}; // Size: 0x308

#endif
