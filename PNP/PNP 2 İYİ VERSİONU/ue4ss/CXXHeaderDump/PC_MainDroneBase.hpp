#ifndef UE4SS_SDK_PC_MainDroneBase_HPP
#define UE4SS_SDK_PC_MainDroneBase_HPP

class APC_MainDroneBase_C : public APlayerController
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x0858 (size: 0x8)

    void ReceiveBeginPlay();
    void Set Game or UI Mode(bool UI);
    void ExecuteUbergraph_PC_MainDroneBase(int32 EntryPoint);
}; // Size: 0x860

#endif
