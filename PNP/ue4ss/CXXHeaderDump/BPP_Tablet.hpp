#ifndef UE4SS_SDK_BPP_Tablet_HPP
#define UE4SS_SDK_BPP_Tablet_HPP

class ABPP_Tablet_C : public APawn
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0328 (size: 0x8)
    class UTextRenderComponent* Text_Total;                                           // 0x0330 (size: 0x8)
    class UTextRenderComponent* Text_TotalFlightTime;                                 // 0x0338 (size: 0x8)
    class UTextRenderComponent* Text_SuccessKillCount;                                // 0x0340 (size: 0x8)
    class UStaticMeshComponent* SM_Tablet;                                            // 0x0348 (size: 0x8)
    class USceneComponent* DefaultSceneRoot;                                          // 0x0350 (size: 0x8)
    FVector InitialLocation;                                                          // 0x0358 (size: 0x18)

    void SumListString(TArray<FString>& List, int32& Sum);
    void SumList(TArray<int32>& List, int32& Sum);
    void ShowTabletInformation(bool Show);
    void ExecuteUbergraph_BPP_Tablet(int32 EntryPoint);
}; // Size: 0x370

#endif
