#ifndef UE4SS_SDK_BP_EPM_CameraBlockingVolume_HPP
#define UE4SS_SDK_BP_EPM_CameraBlockingVolume_HPP

class ABP_EPM_CameraBlockingVolume_C : public AActor
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02A8 (size: 0x8)
    class UBoxComponent* Box;                                                         // 0x02B0 (size: 0x8)

    void ToggleBlockingVolume(bool Activate?);
    void ExecuteUbergraph_BP_EPM_CameraBlockingVolume(int32 EntryPoint);
}; // Size: 0x2B8

#endif
