#ifndef UE4SS_SDK_PC_SpectatorDroneBase_HPP
#define UE4SS_SDK_PC_SpectatorDroneBase_HPP

class APC_SpectatorDroneBase_C : public APlayerController
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0858 (size: 0x8)

    void Set Game or UI Mode(bool UI);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_PC_SpectatorDroneBase(int32 EntryPoint);
}; // Size: 0x860

#endif
