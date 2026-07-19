#ifndef UE4SS_SDK_BPP_Drone_SD_15PLUS_HPP
#define UE4SS_SDK_BPP_Drone_SD_15PLUS_HPP

class ABPP_Drone_SD_15PLUS_C : public ABPP_UAV_Drone_C
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x2458 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerFR2;                                // 0x2460 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerFL2;                                // 0x2468 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerRL2;                                // 0x2470 (size: 0x8)
    class UStaticMeshComponent* SM_Drone_PropellerRR2;                                // 0x2478 (size: 0x8)

    void ReceiveTick(float DeltaSeconds);
    void ExecuteUbergraph_BPP_Drone_SD_15PLUS(int32 EntryPoint);
}; // Size: 0x2480

#endif
