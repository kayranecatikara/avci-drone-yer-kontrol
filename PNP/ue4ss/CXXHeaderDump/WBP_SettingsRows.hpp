#ifndef UE4SS_SDK_WBP_SettingsRows_HPP
#define UE4SS_SDK_WBP_SettingsRows_HPP

class UWBP_SettingsRows_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UButton* Row;                                                               // 0x02D8 (size: 0x8)
    class UTextBlock* RowName;                                                        // 0x02E0 (size: 0x8)
    FLinearColor HoveredColor;                                                        // 0x02E8 (size: 0x10)
    FText RowText;                                                                    // 0x02F8 (size: 0x10)
    FLinearColor UnhoveredColor;                                                      // 0x0308 (size: 0x10)

    void PreConstruct(bool IsDesignTime);
    void BndEvt__WBP_SettingsRows_Row_K2Node_ComponentBoundEvent_0_OnButtonHoverEvent__DelegateSignature();
    void SetRow();
    void BndEvt__WBP_SettingsRows_Row_K2Node_ComponentBoundEvent_1_OnButtonHoverEvent__DelegateSignature();
    void ExecuteUbergraph_WBP_SettingsRows(int32 EntryPoint);
}; // Size: 0x318

#endif
