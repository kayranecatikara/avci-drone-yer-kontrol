#ifndef UE4SS_SDK_BFL_EasySaveGameFunctions_HPP
#define UE4SS_SDK_BFL_EasySaveGameFunctions_HPP

class UBFL_EasySaveGameFunctions_C : public UBlueprintFunctionLibrary
{

    void GetSaveGameOperationsManager(class UObject* __WorldContext, class ABP_EasySaveGameOperationsManager_C*& SaveGameOperationManager);
    void GetPlayTimeAsText(int32 PlayTimeInSeconds, class UObject* __WorldContext, FText& Result);
    void CalcNewPlayTime(FDateTime StartDate, int32 PreviousPlayTime, class UObject* __WorldContext, int32& NewPlayTime);
    void CaptureThumbnailForSaveFile(FString& SaveFileName, class UObject* __WorldContext, FString& ThumbnailPath);
    FString GetThumbnailFilePath(FString& SaveSlot, bool IncludeFileName?, class UObject* __WorldContext);
    void GetSaveFilesPath(class UObject* __WorldContext, FString& SaveFilesPath);
    void GetAllSaveSlots(FString SaveType, class UObject* __WorldContext, TArray<FString>& FoundSlots, bool& FoundSlots?);
    void FindNewestOrOldestSaveSlotFromList(TArray<FString>& Paths, bool FindNewest?, class UObject* __WorldContext, FString& SlotUniqueName, int32& SlotIndex, class UBP_EasySaveGameObject_C*& SaveSlot);
    void FindAvailableIndexForSaveType(FString SaveType, int32 MaxAmountOfSavesForType, class UObject* __WorldContext, FString& SaveUniqueName);
}; // Size: 0x28

#endif
