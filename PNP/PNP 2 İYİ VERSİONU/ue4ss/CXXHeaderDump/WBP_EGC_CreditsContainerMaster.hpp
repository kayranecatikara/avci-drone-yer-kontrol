#ifndef UE4SS_SDK_WBP_EGC_CreditsContainerMaster_HPP
#define UE4SS_SDK_WBP_EGC_CreditsContainerMaster_HPP

class UWBP_EGC_CreditsContainerMaster_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    FWBP_EGC_CreditsContainerMaster_CCreditsContainerFinished CreditsContainerFinished; // 0x02D8 (size: 0x10)
    void CreditsContainerFinished();
    double CreditsSpeedMultiplier;                                                    // 0x02E8 (size: 0x8)
    TArray<FS_CreditsSectionDefinition> CreditSections;                               // 0x02F0 (size: 0x10)
    FS_CreditsTextStyling SectionTitleStyle;                                          // 0x0300 (size: 0x38)
    FS_CreditsTextStyling TextSectionRoleStyle;                                       // 0x0338 (size: 0x38)
    FS_CreditsTextStyling TextSectionNamesStyle;                                      // 0x0370 (size: 0x38)
    FMargin TextSectionOuterMargin;                                                   // 0x03A8 (size: 0x10)

    void GetAnimationSpeedFromTime(double Time, double& PlaybackSpeed);
    void SetAlignmentAndPadding(class UWidget* Widget, FMargin Padding);
    void CreateCreditsSection(class UPanelWidget* Panel, const FS_CreditsSectionDefinition& CreditsSectionDefinition);
    void CreateSectionSpacer(class UPanelWidget* Panel, double SizeY);
    void CreateImageSection(class UPanelWidget* Panel, const FSlateBrush& InBrush, FMargin ImagePadding);
    void CreateTextSection(class UPanelWidget* Panel, const FS_CreditsTextSectionDefinition& TextSectionDefinition);
    void CreateSectionTitle(class UPanelWidget* Panel, FText Text, bool OverrideStyle?, FS_CreditsTextStyling StyleOverride);
    void CreateTextWidget(FText Text, FS_CommonTextInfo TextStyling, FLinearColor TextColor, class UWidget*& OutWidget);
    void UpdateSpeedMultiplier(double NewSpeedMultiplier);
    void CreditsContainerCompleted();
    void Construct();
    void StartCreditsContainer();
    void ExecuteUbergraph_WBP_EGC_CreditsContainerMaster(int32 EntryPoint);
    void CreditsContainerFinished__DelegateSignature();
}; // Size: 0x3B8

#endif
