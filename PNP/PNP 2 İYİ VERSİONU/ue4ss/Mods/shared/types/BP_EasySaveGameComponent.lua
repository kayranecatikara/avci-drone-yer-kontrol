---@meta

---@class UBP_EasySaveGameComponent_C : UActorComponent
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ['RegisterDestruction?'] boolean
---@field ['SaveTranform?'] boolean
---@field ['HasVariablesToSave?'] boolean
---@field JsonObject FJsonObjectWrapper
---@field LoadingOrSavingVariables FBP_EasySaveGameComponent_CLoadingOrSavingVariables
---@field OwnerActorRef TSoftObjectPtr<AActor>
---@field ActorSaveType E_SaveGameActorOperation::Type
---@field ['RespawnOrFindOnlyInSameLevel?'] boolean
---@field ['SaveTransformOnlyInSameLevel?'] boolean
---@field ActorClass TSoftClassPtr<AActor>
---@field ActorUniqueID FString
---@field ComponentState TArray<boolean>
---@field ['Registered?'] boolean
---@field ['EnableSaveGameOperationStartedDispatcher?'] boolean
---@field ['EnableSaveGameOperationEndedDispatcher?'] boolean
---@field SaveGameOperationStarted FBP_EasySaveGameComponent_CSaveGameOperationStarted
---@field SaveGameOperationEnded FBP_EasySaveGameComponent_CSaveGameOperationEnded
local UBP_EasySaveGameComponent_C = {}

---@param OperationType E_SaveGameOperationType::Type
---@param SavedVariables FString
---@param ActorRef TSoftObjectPtr<AActor>
---@param SavedVariablesOut FString
---@param ActorUniqueID FString
function UBP_EasySaveGameComponent_C:SaveOrLoadVariables(OperationType, SavedVariables, ActorRef, SavedVariablesOut, ActorUniqueID) end
function UBP_EasySaveGameComponent_C:RequestLoadVariables() end
function UBP_EasySaveGameComponent_C:RetriggerRegistration() end
function UBP_EasySaveGameComponent_C:ForceTriggerDestruction() end
---@param Operation FS_SaveOperationInfos
function UBP_EasySaveGameComponent_C:SaveGameOperationEnded_Event(Operation) end
---@param Operation FS_SaveOperationInfos
function UBP_EasySaveGameComponent_C:SaveGameOperationStarted_Event(Operation) end
---@param EndPlayReason EEndPlayReason::Type
function UBP_EasySaveGameComponent_C:ReceiveEndPlay(EndPlayReason) end
function UBP_EasySaveGameComponent_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function UBP_EasySaveGameComponent_C:ExecuteUbergraph_BP_EasySaveGameComponent(EntryPoint) end
---@param Operation FS_SaveOperationInfos
function UBP_EasySaveGameComponent_C:SaveGameOperationStarted__DelegateSignature(Operation) end
---@param Operation FS_SaveOperationInfos
function UBP_EasySaveGameComponent_C:SaveGameOperationEnded__DelegateSignature(Operation) end
---@param OperationType E_SaveGameOperationType::Type
---@param JsonObject FJsonObjectWrapper
function UBP_EasySaveGameComponent_C:LoadingOrSavingVariables__DelegateSignature(OperationType, JsonObject) end


