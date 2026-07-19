#ifndef UE4SS_SDK_WBP_EGUI_VersionDisplayer_HPP
#define UE4SS_SDK_WBP_EGUI_VersionDisplayer_HPP

class UWBP_EGUI_VersionDisplayer_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* Text;                                               // 0x02D8 (size: 0x8)
    FS_CommonTextInfo TextStyling;                                                    // 0x02E0 (size: 0x18)

    void PreConstruct(bool IsDesignTime);
    void ExecuteUbergraph_WBP_EGUI_VersionDisplayer(int32 EntryPoint);
}; // Size: 0x2F8

#endif
