#ifndef UE4SS_SDK_BP_I_Data_HPP
#define UE4SS_SDK_BP_I_Data_HPP

class IBP_I_Data_C : public IInterface
{

    void Notify_Scoreboard(FString FailCrash, FString SuccessCrash, FString TotalCrash, FString Date, FString DateTime, FString TotalTime);
    void Notify_Killfeed(FString Killer, FString WhoDead, bool isNet, bool isFail);
}; // Size: 0x28

#endif
