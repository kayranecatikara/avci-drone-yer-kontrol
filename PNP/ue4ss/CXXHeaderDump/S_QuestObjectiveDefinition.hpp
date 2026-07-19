#ifndef UE4SS_SDK_S_QuestObjectiveDefinition_HPP
#define UE4SS_SDK_S_QuestObjectiveDefinition_HPP

struct FS_QuestObjectiveDefinition
{
    FName ObjectiveUniqueName_5_A84385A24E49840BC9B1119582222B1B;                     // 0x0000 (size: 0x8)
    FText ObjectiveDescription_2_DE664236499823335FF81584E805C3E7;                    // 0x0008 (size: 0x10)
    bool IsOptionalObjective?_12_70AE625F4A971A71A73762986E08D2D9;                    // 0x0018 (size: 0x1)
    TEnumAsByte<E_QuestObjectiveState::Type> ObjectiveDefaultState_8_CE9846C84C5DEF10AD7903A12CCB83A2; // 0x0019 (size: 0x1)

}; // Size: 0x1A

#endif
