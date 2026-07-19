#ifndef UE4SS_SDK_WBP_ESGU_SaveFileCard_HPP
#define UE4SS_SDK_WBP_ESGU_SaveFileCard_HPP

class UWBP_ESGU_SaveFileCard_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonBackground_C* Background;                                   // 0x02D8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* DisplayName;                                        // 0x02E0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* GameVersion;                                        // 0x02E8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* PlayTime;                                           // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonText_C* SaveDate;                                           // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonText_C* UniqueName;                                         // 0x0300 (size: 0x8)
    class UWBP_ESGU_SavesManagerUI_C* SaveGamesUIRef;                                 // 0x0308 (size: 0x8)
    class UTexture2D* Thumbnail;                                                      // 0x0310 (size: 0x8)
    FS_SaveGameMetadatas MetaDatas;                                                   // 0x0318 (size: 0x48)
    bool SaveFileIncompatible?;                                                       // 0x0360 (size: 0x1)

    FEventReply OnMouseButtonDown(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void RefreshMetadatas(FS_SaveGameMetadatas MetaDatas);
    void OnMouseEnter(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void OnAddedToFocusPath(FFocusEvent InFocusEvent);
    void Construct();
    void ExecuteUbergraph_WBP_ESGU_SaveFileCard(int32 EntryPoint);
}; // Size: 0x361

#endif
