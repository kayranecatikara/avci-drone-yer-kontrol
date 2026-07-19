#ifndef UE4SS_SDK_S_CreditsTextSectionDefinition_HPP
#define UE4SS_SDK_S_CreditsTextSectionDefinition_HPP

struct FS_CreditsTextSectionDefinition
{
    FText RoleName_2_B6D30885433F3102A0C2C984FEB018B6;                                // 0x0000 (size: 0x10)
    TEnumAsByte<E_RoleNameTextPosition::Type> RoleNamePosition_9_33FB0BB642D5682E730B7393BBEC033F; // 0x0010 (size: 0x1)
    FText MembersNames_6_B9D5572E4FEF0186347D3E9C2896BBE9;                            // 0x0018 (size: 0x10)
    bool OverrideRoleTextStyle?_21_4B4176BB42B935BA5455278D78A16837;                  // 0x0028 (size: 0x1)
    FS_CreditsTextStyling RoleTextStyleOverride_22_20B9606A49A0E90267332B9BEA882A6F;  // 0x0030 (size: 0x38)
    bool OverrideNamesTextStyle?_14_2515323F4E7FE55CC4B6FEA852BFE2F3;                 // 0x0068 (size: 0x1)
    FS_CreditsTextStyling NamesTextStyleOverride_16_32F63E864F8DBA8F9DFB22A1DE23A8B2; // 0x0070 (size: 0x38)

}; // Size: 0xA8

#endif
