#ifndef UE4SS_SDK_S_UAV_HPP
#define UE4SS_SDK_S_UAV_HPP

struct FS_UAV
{
    TEnumAsByte<E_UAV::Type> Type_2_D48D35FD433FDB1FA31A8A8B3CE09FCA;                 // 0x0000 (size: 0x1)
    TSubclassOf<class ABPP_UAV_C> UAVPawn_70_B74BEEB5443F838016748B94DA3A6AE8;        // 0x0008 (size: 0x8)
    double MaxSpeedTrain_11_500DD9CD4ECEC044721819BE40318DEF;                         // 0x0010 (size: 0x8)
    double MaxSpeedAttack_12_D3D204EF461406F19CA2F7904F9AB62E;                        // 0x0018 (size: 0x8)
    double Mass_78_F6240A5E48EB9D257DB55A9B3106D94C;                                  // 0x0020 (size: 0x8)
    double ExplosionWeight_81_14D90D174C5B45D5C412F5B998B93653;                       // 0x0028 (size: 0x8)
    double ExplosionHeavyRadius_66_700A10BB4D0756F3C8720E98AA24541A;                  // 0x0030 (size: 0x8)
    double ExplosionPersonalRadius_65_15094FDD4421B98529D0F49F382806CA;               // 0x0038 (size: 0x8)
    FVector ExplosionEffectScale_34_24971AB642EFAB3E9AA321BE797AF7A5;                 // 0x0040 (size: 0x18)
    double ExplosionEffectScaleMultiply_19_D59847AE463F398756A9C09793D82D29;          // 0x0058 (size: 0x8)
    double PropellerRotateSpeed_21_18A6C4AB4BA23169A7627D95A1D56447;                  // 0x0060 (size: 0x8)
    double LockDistance_23_90183C384300886EC352B8A79FB19A98;                          // 0x0068 (size: 0x8)
    double PropwashDuration_27_0EF6BE7F48A93F7BFE8532A3B086CEB9;                      // 0x0070 (size: 0x8)
    double JammerActionInput_39_B66FF0EB435B28381F1C759F383B4C50;                     // 0x0078 (size: 0x8)
    double JammerDefaultInput_40_595715CD4AC72C6B9C7CE79E6172DE64;                    // 0x0080 (size: 0x8)
    FPostProcessSettings PPThermal_43_73B0A06F46F1D006CB558F91A327F9D2;               // 0x0090 (size: 0x700)
    FPostProcessSettings PPNormal_47_44FA85FC404AB306507E27B2BD7D865B;                // 0x0790 (size: 0x700)
    FPostProcessSettings PPOutsideFirstPhase_48_8129B2F245E36D6AAE13B1B350241091;     // 0x0E90 (size: 0x700)
    FPostProcessSettings PPOutsideSecondPhase_49_CC2192624E5999C9A7D45D99080AA85B;    // 0x1590 (size: 0x700)
    double RopeBrokeDuration_52_D8AB936C4F399489950A7BA4C287144B;                     // 0x1C90 (size: 0x8)
    double Fiber5KMDistance_57_EFACCDF24FC0FBA35FE751BE18AE9180;                      // 0x1C98 (size: 0x8)
    double Fiber10KMDistance_56_C809B52C4D0EE9CBFB947C988FD3BEB1;                     // 0x1CA0 (size: 0x8)
    double MinEngineSoundPitch_75_2DC7D52440EA8F068F4D8ABC0EA462CB;                   // 0x1CA8 (size: 0x8)
    double MaxEngineSoundPitch_76_BA715F8446B9235A3EB5B9ADFDF0DD9A;                   // 0x1CB0 (size: 0x8)
    double BatteryDuration_62_6BCC9DBD438B1BFCF2C188B456779684;                       // 0x1CB8 (size: 0x8)
    FS_BatteryPhaseValue BatteryInformationFirstPhase1_105_5A6C047C415689B818B9A0AB33AE5F53; // 0x1CC0 (size: 0x28)
    FS_BatteryPhaseValue BatteryInformationFirstPhase2_99_78B1D04E4E4291159B08ECB1DC85E8F2; // 0x1CE8 (size: 0x28)
    FS_BatteryPhaseValue BatteryInformationFirstPhase3_104_680EFEA040E0D3AF269A4187C748C50E; // 0x1D10 (size: 0x28)
    FS_BatteryPhaseValue BatteryInformationFirstPhase4_103_620319EB4FC66E73829BFAA953B21E2F; // 0x1D38 (size: 0x28)

}; // Size: 0x1D60

#endif
