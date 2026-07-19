#ifndef UE4SS_SDK_WBP_SettingsOption_HPP
#define UE4SS_SDK_WBP_SettingsOption_HPP

class UWBP_SettingsOption_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UButton* ButtonLeft;                                                        // 0x02D8 (size: 0x8)
    class UButton* ButtonRight;                                                       // 0x02E0 (size: 0x8)
    class UTextBlock* SelectionText;                                                  // 0x02E8 (size: 0x8)
    TArray<FString> Options;                                                          // 0x02F0 (size: 0x10)
    int32 CurrentOption;                                                              // 0x0300 (size: 0x4)
    FWBP_SettingsOption_COnOptionsChanged OnOptionsChanged;                           // 0x0308 (size: 0x10)
    void OnOptionsChanged(FString Option, int32 OptionIndex);

    bool Get_ButtonLeft_bIsEnabled();
    bool Get_ButtonRight_bIsEnabled();
    void Construct();
    void SetSelectedOption(FString NewOption, bool IsCalled);
    void BndEvt__WBP_SettingsOption_ButtonLeft_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature();
    void BndEvt__WBP_SettingsOption_ButtonRight_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature();
    void BndEvt__WBP_SettingsOption_ButtonRight_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature();
    void BndEvt__WBP_SettingsOption_ButtonLeft_K2Node_ComponentBoundEvent_3_OnButtonHoverEvent__DelegateSignature();
    void ExecuteUbergraph_WBP_SettingsOption(int32 EntryPoint);
    void OnOptionsChanged__DelegateSignature(FString Option, int32 OptionIndex);
}; // Size: 0x318

#endif
