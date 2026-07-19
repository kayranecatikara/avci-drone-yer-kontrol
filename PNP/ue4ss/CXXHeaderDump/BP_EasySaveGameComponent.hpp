#ifndef UE4SS_SDK_BP_EasySaveGameComponent_HPP
#define UE4SS_SDK_BP_EasySaveGameComponent_HPP

class UBP_EasySaveGameComponent_C : public UActorComponent
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A0 (size: 0x8)
    bool RegisterDestruction?;                                                        // 0x00A8 (size: 0x1)
    bool SaveTranform?;                                                               // 0x00A9 (size: 0x1)
    bool HasVariablesToSave?;                                                         // 0x00AA (size: 0x1)
    FJsonObjectWrapper JsonObject;                                                    // 0x00B0 (size: 0x20)
    FBP_EasySaveGameComponent_CLoadingOrSavingVariables LoadingOrSavingVariables;     // 0x00D0 (size: 0x10)
    void LoadingOrSavingVariables(TEnumAsByte<E_SaveGameOperationType::Type> OperationType, FJsonObjectWrapper JsonObject);
    TSoftObjectPtr<AActor> OwnerActorRef;                                             // 0x00E0 (size: 0x28)
    TEnumAsByte<E_SaveGameActorOperation::Type> ActorSaveType;                        // 0x0108 (size: 0x1)
    bool RespawnOrFindOnlyInSameLevel?;                                               // 0x0109 (size: 0x1)
    bool SaveTransformOnlyInSameLevel?;                                               // 0x010A (size: 0x1)
    TSoftClassPtr<AActor> ActorClass;                                                 // 0x0110 (size: 0x28)
    FString ActorUniqueID;                                                            // 0x0138 (size: 0x10)
    TArray<bool> ComponentState;                                                      // 0x0148 (size: 0x10)
    bool Registered?;                                                                 // 0x0158 (size: 0x1)
    bool EnableSaveGameOperationStartedDispatcher?;                                   // 0x0159 (size: 0x1)
    bool EnableSaveGameOperationEndedDispatcher?;                                     // 0x015A (size: 0x1)
    FBP_EasySaveGameComponent_CSaveGameOperationStarted SaveGameOperationStarted;     // 0x0160 (size: 0x10)
    void SaveGameOperationStarted(FS_SaveOperationInfos Operation);
    FBP_EasySaveGameComponent_CSaveGameOperationEnded SaveGameOperationEnded;         // 0x0170 (size: 0x10)
    void SaveGameOperationEnded(FS_SaveOperationInfos Operation);

    void SaveOrLoadVariables(TEnumAsByte<E_SaveGameOperationType::Type> OperationType, FString SavedVariables, TSoftObjectPtr<AActor>& ActorRef, FString& SavedVariablesOut, FString& ActorUniqueID);
    void RequestLoadVariables();
    void RetriggerRegistration();
    void ForceTriggerDestruction();
    void SaveGameOperationEnded_Event(FS_SaveOperationInfos Operation);
    void SaveGameOperationStarted_Event(FS_SaveOperationInfos Operation);
    void ReceiveEndPlay(TEnumAsByte<EEndPlayReason::Type> EndPlayReason);
    void ReceiveBeginPlay();
    void ExecuteUbergraph_BP_EasySaveGameComponent(int32 EntryPoint);
    void SaveGameOperationStarted__DelegateSignature(FS_SaveOperationInfos Operation);
    void SaveGameOperationEnded__DelegateSignature(FS_SaveOperationInfos Operation);
    void LoadingOrSavingVariables__DelegateSignature(TEnumAsByte<E_SaveGameOperationType::Type> OperationType, FJsonObjectWrapper JsonObject);
}; // Size: 0x180

#endif
