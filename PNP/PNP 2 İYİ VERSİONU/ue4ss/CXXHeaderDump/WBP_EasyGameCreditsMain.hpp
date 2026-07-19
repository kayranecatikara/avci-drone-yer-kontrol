#ifndef UE4SS_SDK_WBP_EasyGameCreditsMain_HPP
#define UE4SS_SDK_WBP_EasyGameCreditsMain_HPP

class UWBP_EasyGameCreditsMain_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* FadeOutWidget;                                            // 0x02D8 (size: 0x8)
    class UWidgetAnimation* CrossFadeBackgroundImages;                                // 0x02E0 (size: 0x8)
    class UWBP_EasyInputPromptDisplayer_C* BackBtnInput;                              // 0x02E8 (size: 0x8)
    class UImage* Background;                                                         // 0x02F0 (size: 0x8)
    class UImage* BackgroundSecondary;                                                // 0x02F8 (size: 0x8)
    class UCanvasPanel* CanvasPanel;                                                  // 0x0300 (size: 0x8)
    class UHorizontalBox* Footer;                                                     // 0x0308 (size: 0x8)
    class UWBP_EasyInputPromptDisplayer_C* PauseBtnInput;                             // 0x0310 (size: 0x8)
    class APlayerController* PlayerControllerRef;                                     // 0x0318 (size: 0x8)
    class AHUD* HUD;                                                                  // 0x0320 (size: 0x8)
    double SpeedMultiplier;                                                           // 0x0328 (size: 0x8)
    FKey MNKBackKey;                                                                  // 0x0330 (size: 0x18)
    FKey GamepadBackKey;                                                              // 0x0348 (size: 0x18)
    bool CheckForSkipCreditsHold?;                                                    // 0x0360 (size: 0x1)
    TSoftObjectPtr<UDataTable> CreditsDefinitionDataTable;                            // 0x0368 (size: 0x28)
    class UWBP_EGC_CreditsContainerMaster_C* ActiveCreditsContainer;                  // 0x0390 (size: 0x8)
    class UDataTable* CreditsDefinitionDataTableReference;                            // 0x0398 (size: 0x8)
    TArray<FName> SectionsToProcess;                                                  // 0x03A0 (size: 0x10)
    TEnumAsByte<E_CreditsSectionType::Type> LastSectionType;                          // 0x03B0 (size: 0x1)
    FS_CreditsBackgroundDefinition CreditsBackgroundDefinition;                       // 0x03B8 (size: 0x38)
    TArray<TSoftObjectPtr<UTexture2D>> BackgroundImages;                              // 0x03F0 (size: 0x10)
    int32 CurrentBackgroundImage;                                                     // 0x0400 (size: 0x4)
    double BackgroundCrossFadeDuration;                                               // 0x0408 (size: 0x8)
    TSoftObjectPtr<USoundBase> MusicReference;                                        // 0x0410 (size: 0x28)
    float MusicFadeOutDuration;                                                       // 0x0438 (size: 0x4)
    class UAudioComponent* MusicAudioComponent;                                       // 0x0440 (size: 0x8)
    FWBP_EasyGameCreditsMain_CCreditsStarted CreditsStarted;                          // 0x0448 (size: 0x10)
    void CreditsStarted();
    FWBP_EasyGameCreditsMain_CCreditsCompleted CreditsCompleted;                      // 0x0458 (size: 0x10)
    void CreditsCompleted();
    FS_CreditsInputAndGameParameters CreditsInputAndGameParameters;                   // 0x0468 (size: 0x10)
    double SkipHoldDuration;                                                          // 0x0478 (size: 0x8)
    FName LevelToLoadOnCreditsCompletion;                                             // 0x0480 (size: 0x8)
    bool CreditsPaused?;                                                              // 0x0488 (size: 0x1)
    bool PreviousPauseState;                                                          // 0x0489 (size: 0x1)
    bool HudWasHidden?;                                                               // 0x048A (size: 0x1)

    void FadeToNewBackgroundImage();
    void CreateSectionContainerWidget(TEnumAsByte<E_CreditsSectionType::Type> SectionType, TArray<FS_CreditsSectionDefinition>& CreditSections);
    void InitializeNextCreditsSection();
    FEventReply OnMouseMove(FGeometry MyGeometry, const FPointerEvent& MouseEvent);
    void OnLoaded_120C0A384AD6E773B9933ABA00693399(class UObject* Loaded);
    void OnLoaded_D35641C145049C3BFE94EE877F3D4FD5(class UObject* Loaded);
    void Finished_23CD2E0C424290844CBB608A445B83B0();
    void ForceFooterVisibility();
    void CreditsContainerFinished();
    void RestartMusic();
    void EndCredits(bool ManuallyExited?);
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void AnyKeyPressed(FKey Key);
    void Construct();
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
    void ExecuteUbergraph_WBP_EasyGameCreditsMain(int32 EntryPoint);
    void CreditsCompleted__DelegateSignature();
    void CreditsStarted__DelegateSignature();
}; // Size: 0x48B

#endif
