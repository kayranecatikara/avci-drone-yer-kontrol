#ifndef UE4SS_SDK_WBP_CompletedLevel_HPP
#define UE4SS_SDK_WBP_CompletedLevel_HPP

class UWBP_CompletedLevel_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* MissionFailed;                                            // 0x02D8 (size: 0x8)
    class UWidgetAnimation* End;                                                      // 0x02E0 (size: 0x8)
    class UWidgetAnimation* MissionCompleted;                                         // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_MENU;                                         // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_PlayAgain;                                    // 0x02F8 (size: 0x8)
    class UImage* Image_BlackScreen;                                                  // 0x0300 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0308 (size: 0x8)

    void CompletedLevel(bool isFail);
    void Construct();
    void BndEvt__WBP_CompletedLevel_Btn_MENU_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_CompletedLevel_Btn_PlayAgain_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void ExecuteUbergraph_WBP_CompletedLevel(int32 EntryPoint);
}; // Size: 0x310

#endif
