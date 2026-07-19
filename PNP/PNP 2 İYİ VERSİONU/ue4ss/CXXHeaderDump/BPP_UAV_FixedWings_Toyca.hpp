#ifndef UE4SS_SDK_BPP_UAV_FixedWings_Toyca_HPP
#define UE4SS_SDK_BPP_UAV_FixedWings_Toyca_HPP

class ABPP_UAV_FixedWings_Toyca_C : public ABPP_UAV_FixedWings_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x2440 (size: 0x8)

    void ReceiveTick(float DeltaSeconds);
    void ExecuteUbergraph_BPP_UAV_FixedWings_Toyca(int32 EntryPoint);
}; // Size: 0x2448

#endif
