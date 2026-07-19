#ifndef UE4SS_SDK_S_AlertBannerSetupInfos_HPP
#define UE4SS_SDK_S_AlertBannerSetupInfos_HPP

struct FS_AlertBannerSetupInfos
{
    FText ActionDescription_2_61D2DCEC4D89D4D21D9E74B061F42FD2;                       // 0x0000 (size: 0x10)
    TArray<FText> OptionsButtons_5_05B6A43A4F29C2F606E97DB4DC8B48E2;                  // 0x0010 (size: 0x10)
    TEnumAsByte<ESlateSizeRule::Type> ButtonsSizeRule_11_8B73AFEE46A5F5CC1372ACA5629B3438; // 0x0020 (size: 0x1)
    int32 DelayBeforeAutomaticAction_19_7E2D68994C215F51B853DCA3E4B32021;             // 0x0024 (size: 0x4)
    int32 ActionToExecuteAfterDelay_18_36B95C4D47BF2A0ADF394EBBFBDE8067;              // 0x0028 (size: 0x4)
    bool AllowBackInputToTriggerAction?_26_1374DBA44DA34569D4A0F699CEA481A7;          // 0x002C (size: 0x1)
    int32 ActionToExecuteOnBackInputFired_25_0C8879CD4C518F3CFF357EBC46790098;        // 0x0030 (size: 0x4)

}; // Size: 0x34

#endif
