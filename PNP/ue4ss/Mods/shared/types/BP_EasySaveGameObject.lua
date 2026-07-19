---@meta

---@class UBP_EasySaveGameObject_C : USaveGame
---@field MetaDatas FS_SaveGameMetadatas
---@field PersistentActors TMap<TSoftObjectPtr<AActor>, FString>
---@field ActorsToFindOrRespawn TMap<FString, FS_MapsOfActorsToFindOrRespawn>
---@field ActorsToDestroy TArray<TSoftObjectPtr<AActor>>
---@field PlayerTransform TMap<FString, FTransform>
local UBP_EasySaveGameObject_C = {}



