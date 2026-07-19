#ifndef UE4SS_SDK_WBP_EGC_ScrollCreditsContainer_HPP
#define UE4SS_SDK_WBP_EGC_ScrollCreditsContainer_HPP

class UWBP_EGC_ScrollCreditsContainer_C : public UWBP_EGC_CreditsContainerMaster_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x03B8 (size: 0x8)
    class UScrollBox* ScrollBox;                                                      // 0x03C0 (size: 0x8)
    double AutoScrollSpeed;                                                           // 0x03C8 (size: 0x8)
    bool Scroll?;                                                                     // 0x03D0 (size: 0x1)
    float ScrollOffsetOfEnd;                                                          // 0x03D4 (size: 0x4)
    double CurrentScroll;                                                             // 0x03D8 (size: 0x8)

    void SetAlignmentAndPadding(class UWidget* Widget, FMargin Padding);
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void StartCreditsContainer();
    void Construct();
    void BndEvt__WBP_ScrollCreditsContainer_ScrollBox_K2Node_ComponentBoundEvent_0_OnUserScrolledEvent__DelegateSignature(float CurrentOffset);
    void ExecuteUbergraph_WBP_EGC_ScrollCreditsContainer(int32 EntryPoint);
}; // Size: 0x3E0

#endif
