#ifndef UE4SS_SDK_S_CreditsPresetInfos_HPP
#define UE4SS_SDK_S_CreditsPresetInfos_HPP

struct FS_CreditsPresetInfos
{
    TSoftObjectPtr<UDataTable> CreditsDefinitionDataTable_19_46EC68E5413D8BCD530CB5B3115E6B6D; // 0x0000 (size: 0x28)
    FS_CreditsBackgroundDefinition CreditsBackgroundDefinition_20_5ED1D9334CF1A371CD1EC79615F5B491; // 0x0028 (size: 0x38)
    TSoftObjectPtr<USoundBase> MusicReference_21_DF98EDFB4F0D6D5FB44F889B1EFCCEFE;    // 0x0060 (size: 0x28)
    double MusicFadeOutDuration_22_8132BCA345482B86A79DA39131AE85AA;                  // 0x0088 (size: 0x8)
    FS_CreditsInputAndGameParameters CreditsInputAndGameParameters_23_83A8EE8546D6335F63178A8A778DBDCB; // 0x0090 (size: 0x10)
    FName LevelToLoadOnCreditsCompletion_24_0DC6C10F4346A8700E88A193903EA0F7;         // 0x00A0 (size: 0x8)

}; // Size: 0xA8

#endif
