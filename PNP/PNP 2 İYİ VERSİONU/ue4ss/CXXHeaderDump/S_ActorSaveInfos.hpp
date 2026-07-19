#ifndef UE4SS_SDK_S_ActorSaveInfos_HPP
#define UE4SS_SDK_S_ActorSaveInfos_HPP

struct FS_ActorSaveInfos
{
    bool ActorWasDestroyed?_14_6B4BE1F04515E9C52639C3A45C477B7C;                      // 0x0000 (size: 0x1)
    TSoftObjectPtr<UBP_EasySaveGameComponent_C> SaveGameComponentRef_3_921E86CD44C80EDCFB6462995C988A07; // 0x0008 (size: 0x28)
    TSoftClassPtr<AActor> ActorClass_18_3A4AE48E4908EA719DDEEDBC84AD48D9;             // 0x0030 (size: 0x28)
    TEnumAsByte<E_SaveGameActorOperation::Type> ActorSaveType_5_43CCB8EA4009C7551689DC9C0BC69670; // 0x0058 (size: 0x1)
    bool SaveLevel?_13_93C687114A2BCE26EB9AAA877AD5AF83;                              // 0x0059 (size: 0x1)
    FString ActorUniqueID_15_F3BA6B9446A4E0BE533AA292C5F44905;                        // 0x0060 (size: 0x10)

}; // Size: 0x70

#endif
