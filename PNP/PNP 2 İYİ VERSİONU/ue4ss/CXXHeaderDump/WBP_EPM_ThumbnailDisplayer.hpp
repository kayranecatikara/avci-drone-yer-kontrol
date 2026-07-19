#ifndef UE4SS_SDK_WBP_EPM_ThumbnailDisplayer_HPP
#define UE4SS_SDK_WBP_EPM_ThumbnailDisplayer_HPP

class UWBP_EPM_ThumbnailDisplayer_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* BackgroundButton;                                 // 0x02D8 (size: 0x8)
    class UImage* Image;                                                              // 0x02E0 (size: 0x8)
    class UScaleBox* ScaleBox;                                                        // 0x02E8 (size: 0x8)
    FSlateBrush ImageBrush;                                                           // 0x02F0 (size: 0xB0)
    FString ScreenshotName;                                                           // 0x03A0 (size: 0x10)
    bool ThumbnailLoaded?;                                                            // 0x03B0 (size: 0x1)
    FWBP_EPM_ThumbnailDisplayer_CImageClicked ImageClicked;                           // 0x03B8 (size: 0x10)
    void ImageClicked(class UTexture2D* ImageRef, FString ScreenshotName);
    class UWBP_EPM_Gallery_C* GalleryRef;                                             // 0x03C8 (size: 0x8)

    FEventReply OnFocusReceived(FGeometry MyGeometry, FFocusEvent InFocusEvent);
    void BndEvt__WBP_ThumbnailDisplayer_WBP_EGUI_CommonButton_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void OnMouseEnter(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void Construct();
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void ExecuteUbergraph_WBP_EPM_ThumbnailDisplayer(int32 EntryPoint);
    void ImageClicked__DelegateSignature(class UTexture2D* ImageRef, FString ScreenshotName);
}; // Size: 0x3D0

#endif
