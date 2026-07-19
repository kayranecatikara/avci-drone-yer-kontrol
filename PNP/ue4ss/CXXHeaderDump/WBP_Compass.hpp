#ifndef UE4SS_SDK_WBP_Compass_HPP
#define UE4SS_SDK_WBP_Compass_HPP

class UWBP_Compass_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UImage* Image_Compass;                                                      // 0x02D8 (size: 0x8)
    class UOverlay* OverlayPanel;                                                     // 0x02E0 (size: 0x8)
    class ABPP_Spectator_C* As BPP Spectator;                                         // 0x02E8 (size: 0x8)
    class UMaterialInstanceDynamic* CompassMaterial;                                  // 0x02F0 (size: 0x8)

    void PreConstruct(bool IsDesignTime);
    void CompassRotation();
    void ExecuteUbergraph_WBP_Compass(int32 EntryPoint);
}; // Size: 0x2F8

#endif
