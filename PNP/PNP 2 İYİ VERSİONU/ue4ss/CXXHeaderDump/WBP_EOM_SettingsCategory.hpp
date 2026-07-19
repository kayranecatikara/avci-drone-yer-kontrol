#ifndef UE4SS_SDK_WBP_EOM_SettingsCategory_HPP
#define UE4SS_SDK_WBP_EOM_SettingsCategory_HPP

class UWBP_EOM_SettingsCategory_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UBorder* Divider;                                                           // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SectionName;                                        // 0x02E0 (size: 0x8)
    class USizeBox* SizeBox;                                                          // 0x02E8 (size: 0x8)
    FText Name;                                                                       // 0x02F0 (size: 0x10)
    float SizeBoxHeight;                                                              // 0x0300 (size: 0x4)
    FS_CommonTextInfo Text Styling;                                                   // 0x0308 (size: 0x18)

    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EOM_SettingsCategory(int32 EntryPoint);
}; // Size: 0x320

#endif
