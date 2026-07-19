#ifndef UE4SS_SDK_S_CreditsInputAndGameParameters_HPP
#define UE4SS_SDK_S_CreditsInputAndGameParameters_HPP

struct FS_CreditsInputAndGameParameters
{
    double SkipHoldDuration_14_3EA38DE34B47C7A8D8E4C883B7ABD055;                      // 0x0000 (size: 0x8)
    bool PauseGameDuringCredits?_4_687DFF3546379552F9AD49A19D6E1754;                  // 0x0008 (size: 0x1)
    TEnumAsByte<E_ActionsOnCreditsCompletion::Type> ActionOnCreditsCompletion_6_A4F636BD4823273EAFE9959AD657D79A; // 0x0009 (size: 0x1)
    TEnumAsByte<E_PauseStateOnCreditsCompletion::Type> PauseStateToApplyOnCreditsCompletion_10_1F05A0D849D95C21C46E249F7DA2F536; // 0x000A (size: 0x1)
    bool SetInputModeGameOnlyonCompletion?_8_2B5BD6624C4BC21AAA3E798C92DB308E;        // 0x000B (size: 0x1)
    bool RestoreGameplayInputMappingContextonCompletion?_18_9B8E916A4D0733397DE09E835E0F4CD6; // 0x000C (size: 0x1)

}; // Size: 0xD

#endif
