#ifndef UE4SS_SDK_S_SaveOperationInfos_HPP
#define UE4SS_SDK_S_SaveOperationInfos_HPP

struct FS_SaveOperationInfos
{
    FString SlotName_13_C6CE877E44331F53DE974E9C417060A6;                             // 0x0000 (size: 0x10)
    TEnumAsByte<E_SaveGameOperationType::Type> OperationType_11_BE8E193647AC277087C4ADAAF709F344; // 0x0010 (size: 0x1)
    TEnumAsByte<E_SaveGameOperationSpeed::Type> OperationSpeed_12_8FE24B47473CFDB1147573A0580BD662; // 0x0011 (size: 0x1)
    bool LoadingScreen?_15_96FB46C14EFC0D4F91B56DBAA6BEC39E;                          // 0x0012 (size: 0x1)

}; // Size: 0x13

#endif
