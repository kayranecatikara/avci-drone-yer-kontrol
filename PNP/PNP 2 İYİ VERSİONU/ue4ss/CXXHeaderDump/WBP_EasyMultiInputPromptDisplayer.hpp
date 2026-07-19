#ifndef UE4SS_SDK_WBP_EasyMultiInputPromptDisplayer_HPP
#define UE4SS_SDK_WBP_EasyMultiInputPromptDisplayer_HPP

class UWBP_EasyMultiInputPromptDisplayer_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UHorizontalBox* Container;                                                  // 0x02D8 (size: 0x8)
    bool UseInputAction?;                                                             // 0x02E0 (size: 0x1)
    class UInputAction* InputAction;                                                  // 0x02E8 (size: 0x8)
    class UInputMappingContext* InputMappingContext;                                  // 0x02F0 (size: 0x8)
    TArray<FKey> MNK Keys;                                                            // 0x02F8 (size: 0x10)
    TArray<FKey> Gamepad Keys;                                                        // 0x0308 (size: 0x10)
    double Key Image Size;                                                            // 0x0318 (size: 0x8)
    FText Text to Display;                                                            // 0x0320 (size: 0x10)
    TEnumAsByte<EHorizontalAlignment> Text Position;                                  // 0x0330 (size: 0x1)
    FMargin Text Padding;                                                             // 0x0334 (size: 0x10)
    FS_CommonTextInfo Text Styling;                                                   // 0x0348 (size: 0x18)
    double Spacing;                                                                   // 0x0360 (size: 0x8)
    int32 LastIndex;                                                                  // 0x0368 (size: 0x4)
    bool Hide Key for Other Devices?;                                                 // 0x036C (size: 0x1)
    bool HideTextAsWell?;                                                             // 0x036D (size: 0x1)
    bool Use Styling Local Override?;                                                 // 0x036E (size: 0x1)
    FSlateColor Text Color;                                                           // 0x0370 (size: 0x14)
    FLinearColor Icon Color;                                                          // 0x0384 (size: 0x10)
    TArray<class UWBP_EasyInputPromptDisplayer_C*> InputPromptsReferences;            // 0x0398 (size: 0x10)

    void CreateInputPromptsWidgets(TArray<FKey>& Array);
    void RefreshInputPrompts();
    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EasyMultiInputPromptDisplayer(int32 EntryPoint);
}; // Size: 0x3A8

#endif
