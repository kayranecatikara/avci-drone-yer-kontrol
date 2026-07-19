#ifndef UE4SS_SDK_WBP_EGC_FadeCreditsContainer_HPP
#define UE4SS_SDK_WBP_EGC_FadeCreditsContainer_HPP

class UWBP_EGC_FadeCreditsContainer_C : public UWBP_EGC_CreditsContainerMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03B8 (size: 0x8)
    class UWidgetAnimation* IdleContainerAnimation;                                   // 0x03C0 (size: 0x8)
    class UWidgetAnimation* FadeInOutContainerAnimation;                              // 0x03C8 (size: 0x8)
    class UVerticalBox* VerticalBox;                                                  // 0x03D0 (size: 0x8)
    int32 CurrentIndex;                                                               // 0x03D8 (size: 0x4)
    double FadeInDuration;                                                            // 0x03E0 (size: 0x8)
    double SectionDuration;                                                           // 0x03E8 (size: 0x8)
    double FadeOutDuration;                                                           // 0x03F0 (size: 0x8)

    void SetAlignmentAndPadding(class UWidget* Widget, FMargin Padding);
    void Finished_EBE509394EB8D0E45CF7E79C91978CF3();
    void Finished_C23126DA4D92287ADEA179AFFAFD12AD();
    void DisplayNextCredits();
    void StartCreditsContainer();
    void UpdateSpeedMultiplier(double NewSpeedMultiplier);
    void ExecuteUbergraph_WBP_EGC_FadeCreditsContainer(int32 EntryPoint);
}; // Size: 0x3F8

#endif
