#ifndef UE4SS_SDK_BP_EasySaveGameObject_HPP
#define UE4SS_SDK_BP_EasySaveGameObject_HPP

class UBP_EasySaveGameObject_C : public USaveGame
{
    FS_SaveGameMetadatas MetaDatas;                                                   // 0x0028 (size: 0x48)
    TMap<class TSoftObjectPtr<AActor>, class FString> PersistentActors;               // 0x0070 (size: 0x50)
    TMap<class FString, class FS_MapsOfActorsToFindOrRespawn> ActorsToFindOrRespawn;  // 0x00C0 (size: 0x50)
    TArray<TSoftObjectPtr<AActor>> ActorsToDestroy;                                   // 0x0110 (size: 0x10)
    TMap<class FString, class FTransform> PlayerTransform;                            // 0x0120 (size: 0x50)

}; // Size: 0x170

#endif
