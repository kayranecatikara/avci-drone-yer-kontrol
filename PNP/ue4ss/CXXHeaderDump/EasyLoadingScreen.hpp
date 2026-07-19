#ifndef UE4SS_SDK_EasyLoadingScreen_HPP
#define UE4SS_SDK_EasyLoadingScreen_HPP

class UEasyLoadingScreenAsync : public UBlueprintAsyncActionBase
{
    FEasyLoadingScreenAsyncOnUpdate OnUpdate;                                         // 0x0038 (size: 0x10)
    void LoadingUpdateDelegate(float Percentage);
    FEasyLoadingScreenAsyncOnComplete OnComplete;                                     // 0x0048 (size: 0x10)
    void LoadingFinishDelegate();

    void OpenServerLevelWithUMG2(class UObject* WorldContextObject, FString URL, const TSoftObjectPtr<UWorld> Level, bool bAbsolute, FString Options, float DelayOpen);
    void OpenServerLevelWithUMG(class UObject* WorldContextObject, FString URL, FName LevelName, bool bAbsolute, FString Options, float DelayOpen);
    void OpenLevelWithUMG2(class UObject* WorldContextObject, const TSoftObjectPtr<UWorld> Level, bool bAbsolute, FString Options, float DelayOpen);
    void OpenLevelWithUMG(class UObject* WorldContextObject, FName LevelName, bool bAbsolute, FString Options, float DelayOpen);
    class UEasyLoadingScreenAsync* OpenLevelWithPercentage2(class UObject* WorldContextObject, const TSoftObjectPtr<UWorld> Level, bool bAbsolute, FString Options, float DelayOpen);
    class UEasyLoadingScreenAsync* OpenLevelWithPercentage(class UObject* WorldContextObject, FName LevelName, bool bAbsolute, FString Options, float DelayOpen);
}; // Size: 0xE8

#endif
