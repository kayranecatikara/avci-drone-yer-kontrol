#ifndef UE4SS_SDK_WBP_EGUI_CommonBackgroundImage_HPP
#define UE4SS_SDK_WBP_EGUI_CommonBackgroundImage_HPP

class UWBP_EGUI_CommonBackgroundImage_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBorder* Background;                                                        // 0x02D8 (size: 0x8)
    class UImage* BackgroundImage;                                                    // 0x02E0 (size: 0x8)
    class UScaleBox* BackgroundScaleBox;                                              // 0x02E8 (size: 0x8)
    bool DisplayBackgroundImage?;                                                     // 0x02F0 (size: 0x1)
    FSlateBrush ImageBrush;                                                           // 0x0300 (size: 0xB0)
    bool DisplayBackgroundColor?;                                                     // 0x03B0 (size: 0x1)
    FSlateBrush BackgroundColorBrush;                                                 // 0x03C0 (size: 0xB0)

    void PreConstruct(bool IsDesignTime);
    void UpdateBackgroundImage(class UTexture2D* Texture);
    void ExecuteUbergraph_WBP_EGUI_CommonBackgroundImage(int32 EntryPoint);
}; // Size: 0x470

#endif
