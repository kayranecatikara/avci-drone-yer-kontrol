#ifndef UE4SS_SDK_WBP_SelectedOptions_HPP
#define UE4SS_SDK_WBP_SelectedOptions_HPP

class UWBP_SelectedOptions_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_MENU_1;                                       // 0x02D8 (size: 0x8)
    class UImage* SaveFileThumbnail;                                                  // 0x02E0 (size: 0x8)
    class UTextBlock* Text_MapName;                                                   // 0x02E8 (size: 0x8)
    class UTextBlock* TextBlock_Type;                                                 // 0x02F0 (size: 0x8)
    class UTextBlock* TextBlock_UAV;                                                  // 0x02F8 (size: 0x8)
    class UBP_GameInstance_C*  BP Game Instance;                                      // 0x0300 (size: 0x8)
    class UDataTable* DTMaps;                                                         // 0x0308 (size: 0x8)
    class UMaterial* Card Picture;                                                    // 0x0310 (size: 0x8)
    FWBP_SelectedOptions_COnClickedScoreboard OnClickedScoreboard;                    // 0x0318 (size: 0x10)
    void OnClickedScoreboard();

    void GetCustomDataTable(TEnumAsByte<E_Levels::Type> Level, class UTexture2D*& CardTexture);
    void UpdateInformation();
    void Construct();
    void BndEvt__WBP_SelectedOptions_Btn_MENU_1_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void ExecuteUbergraph_WBP_SelectedOptions(int32 EntryPoint);
    void OnClickedScoreboard__DelegateSignature();
}; // Size: 0x328

#endif
