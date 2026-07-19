#ifndef UE4SS_SDK_WBP_ActiveSelectIndicator_HPP
#define UE4SS_SDK_WBP_ActiveSelectIndicator_HPP

class UWBP_ActiveSelectIndicator_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBorder* Border;                                                            // 0x02D8 (size: 0x8)
    bool IsActive?;                                                                   // 0x02E0 (size: 0x1)
    FLinearColor AccentColor;                                                         // 0x02E4 (size: 0x10)

    void UpdateState(bool Active?);
    void Construct();
    void ExecuteUbergraph_WBP_ActiveSelectIndicator(int32 EntryPoint);
}; // Size: 0x2F4

#endif
