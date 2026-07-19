#ifndef UE4SS_SDK_WBP_ESGU_LoadingScreen_HPP
#define UE4SS_SDK_WBP_ESGU_LoadingScreen_HPP

class UWBP_ESGU_LoadingScreen_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* FadeAnimation;                                            // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonBackgroundImage_C* Background;                              // 0x02E0 (size: 0x8)
    class UWBP_EGUI_OptionDescription_C* ObjectiveDisplayer;                          // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* Text;                                               // 0x02F0 (size: 0x8)
    class UTexture2D* BackgroundImage;                                                // 0x02F8 (size: 0x8)
    FText TipText;                                                                    // 0x0300 (size: 0x10)
    TEnumAsByte<E_SaveGameOperationType::Type> OperationType;                         // 0x0310 (size: 0x1)

    void Finished_C781A7CD4B96653F3B54FA8BB8742C76();
    void OnLoaded_0432773E4B382506B3F04E8CE953645F(class UObject* Loaded);
    void Construct();
    void StopLoadingScreenAfterDelay(bool PlayFadeAnimation?, double Duration);
    void InitLoadingScreen(TEnumAsByte<E_SaveGameOperationType::Type> OperationType, bool PlayFadeAnimation?);
    void PlayFadeAnimation(bool FadeOut?);
    void ExecuteUbergraph_WBP_ESGU_LoadingScreen(int32 EntryPoint);
}; // Size: 0x311

#endif
