#ifndef UE4SS_SDK_WBP_PressAnyButton_HPP
#define UE4SS_SDK_WBP_PressAnyButton_HPP

class UWBP_PressAnyButton_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* PressTheButtonFade;                                       // 0x02D8 (size: 0x8)
    class UWidgetAnimation* FadeOut;                                                  // 0x02E0 (size: 0x8)
    class UImage* Image_226;                                                          // 0x02E8 (size: 0x8)
    class UImage* Image_334;                                                          // 0x02F0 (size: 0x8)
    class UImage* Image_Background;                                                   // 0x02F8 (size: 0x8)
    class UImage* Image_BlackBarBottom;                                               // 0x0300 (size: 0x8)
    class UImage* Image_BlackBarTop;                                                  // 0x0308 (size: 0x8)
    class UImage* Image_Logo;                                                         // 0x0310 (size: 0x8)
    class UImage* Image_LogoShadow;                                                   // 0x0318 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* WBP_EGUI_CommonButton;                            // 0x0320 (size: 0x8)
    class UWBP_EGUI_CommonText_C* WBP_EGUI_CommonText;                                // 0x0328 (size: 0x8)
    class AHUD_MainMenu_C*  HUD Main Menu;                                            // 0x0330 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0338 (size: 0x8)
    class UMediaPlayer* IntroMediaPlayer;                                             // 0x0340 (size: 0x8)

    void Construct();
    void PressedAnyButton();
    void BndEvt__WBP_PressAnyButton_WBP_EGUI_CommonButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void ExecuteUbergraph_WBP_PressAnyButton(int32 EntryPoint);
}; // Size: 0x348

#endif
