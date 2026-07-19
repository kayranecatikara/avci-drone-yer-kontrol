#ifndef UE4SS_SDK_S_SkillConsumableSlotDefinition_HPP
#define UE4SS_SDK_S_SkillConsumableSlotDefinition_HPP

struct FS_SkillConsumableSlotDefinition
{
    FSlateBrush SlotIcon_2_BC2D77BC493ECDCF0EFB26B682A4F5EB;                          // 0x0000 (size: 0xB0)
    FLinearColor CooldownFillColor_25_05E1E74942B118FFEFE5AAA17E1767C4;               // 0x00B0 (size: 0x10)
    int32 AvailableUtilisations_5_2FC9C0DD446F85BC7542ACB451D7B884;                   // 0x00C0 (size: 0x4)
    int32 MaximumUtilisations_7_1576A5A1460A7B76A29BCD97A0F32608;                     // 0x00C4 (size: 0x4)
    bool InitializeWithCooldown?_19_262F88F741371AA777C006B724460F53;                 // 0x00C8 (size: 0x1)
    double InitialCooldown_20_DD8EC2E740A9B4B05D59DEA93DEE0394;                       // 0x00D0 (size: 0x8)
    bool RegainUtilisationAfterCooldown?_22_51CFA984436E5AE638B70896AC484AD4;         // 0x00D8 (size: 0x1)

}; // Size: 0xD9

#endif
