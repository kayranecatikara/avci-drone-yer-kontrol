#ifndef UE4SS_SDK_L_TeknofestSavasanIha_HPP
#define UE4SS_SDK_L_TeknofestSavasanIha_HPP

class AL_TeknofestSavasanIha_C : public ALevelScriptActor
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02B0 (size: 0x8)
    class AGM_UAVBase_C* As GM UAVBase;                                               // 0x02B8 (size: 0x8)
    class ACineCameraActor* CineCameraActor_2_ExecuteUbergraph_L_TeknofestSavasanIha_RefProperty; // 0x02C0 (size: 0x8)

    void ReceiveBeginPlay();
    void ExecuteUbergraph_L_TeknofestSavasanIha(int32 EntryPoint);
}; // Size: 0x2C8

#endif
