#ifndef UE4SS_SDK_WBP_EGUI_OptionDescription_HPP
#define UE4SS_SDK_WBP_EGUI_OptionDescription_HPP

class UWBP_EGUI_OptionDescription_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonScrollBox_C* DescriptionTextScrollBox;                      // 0x02D8 (size: 0x8)
    class UBorder* DisplayImage;                                                      // 0x02E0 (size: 0x8)
    class UScaleBox* DisplayImageBox;                                                 // 0x02E8 (size: 0x8)
    class UBorder* Divider;                                                           // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* OptionTitleText;                                    // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonRichText_C* RichTextDescription;                            // 0x0300 (size: 0x8)
    FS_CommonTextInfo TitleTextStyling;                                               // 0x0308 (size: 0x18)
    FS_CommonTextInfo DescriptionTextStyling;                                         // 0x0320 (size: 0x18)
    bool DescriptionOnly?;                                                            // 0x0338 (size: 0x1)
    TEnumAsByte<EHorizontalAlignment> DividerHorizontalAlignment;                     // 0x0339 (size: 0x1)
    TSoftObjectPtr<UTexture2D> CurrentImageDisplayed;                                 // 0x0340 (size: 0x28)

    FText GetDescriptionText();
    void UpdateDescription(FText OptionTitle, FText OptionDescription, TSoftObjectPtr<UTexture2D> ImageToDisplay);
    void OnLoaded_C4B73404456EE5B2D218C6963C5C63AD(class UObject* Loaded);
    void Construct();
    void PreConstruct(bool IsDesignTime);
    void LoadNewDescriptionImage(TSoftObjectPtr<UObject> ImageToLoad);
    void ExecuteUbergraph_WBP_EGUI_OptionDescription(int32 EntryPoint);
}; // Size: 0x368

#endif
