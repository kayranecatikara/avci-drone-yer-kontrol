---@meta

---@class UWBP_EasyGameCreditsMain_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field FadeOutWidget UWidgetAnimation
---@field CrossFadeBackgroundImages UWidgetAnimation
---@field BackBtnInput UWBP_EasyInputPromptDisplayer_C
---@field Background UImage
---@field BackgroundSecondary UImage
---@field CanvasPanel UCanvasPanel
---@field Footer UHorizontalBox
---@field PauseBtnInput UWBP_EasyInputPromptDisplayer_C
---@field PlayerControllerRef APlayerController
---@field HUD AHUD
---@field SpeedMultiplier double
---@field MNKBackKey FKey
---@field GamepadBackKey FKey
---@field ['CheckForSkipCreditsHold?'] boolean
---@field CreditsDefinitionDataTable TSoftObjectPtr<UDataTable>
---@field ActiveCreditsContainer UWBP_EGC_CreditsContainerMaster_C
---@field CreditsDefinitionDataTableReference UDataTable
---@field SectionsToProcess TArray<FName>
---@field LastSectionType E_CreditsSectionType::Type
---@field CreditsBackgroundDefinition FS_CreditsBackgroundDefinition
---@field BackgroundImages TArray<TSoftObjectPtr<UTexture2D>>
---@field CurrentBackgroundImage int32
---@field BackgroundCrossFadeDuration double
---@field MusicReference TSoftObjectPtr<USoundBase>
---@field MusicFadeOutDuration float
---@field MusicAudioComponent UAudioComponent
---@field CreditsStarted FWBP_EasyGameCreditsMain_CCreditsStarted
---@field CreditsCompleted FWBP_EasyGameCreditsMain_CCreditsCompleted
---@field CreditsInputAndGameParameters FS_CreditsInputAndGameParameters
---@field SkipHoldDuration double
---@field LevelToLoadOnCreditsCompletion FName
---@field ['CreditsPaused?'] boolean
---@field PreviousPauseState boolean
---@field ['HudWasHidden?'] boolean
local UWBP_EasyGameCreditsMain_C = {}

function UWBP_EasyGameCreditsMain_C:FadeToNewBackgroundImage() end
---@param SectionType E_CreditsSectionType::Type
---@param CreditSections TArray<FS_CreditsSectionDefinition>
function UWBP_EasyGameCreditsMain_C:CreateSectionContainerWidget(SectionType, CreditSections) end
function UWBP_EasyGameCreditsMain_C:InitializeNextCreditsSection() end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EasyGameCreditsMain_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param Loaded UObject
function UWBP_EasyGameCreditsMain_C:OnLoaded_120C0A384AD6E773B9933ABA00693399(Loaded) end
---@param Loaded UObject
function UWBP_EasyGameCreditsMain_C:OnLoaded_D35641C145049C3BFE94EE877F3D4FD5(Loaded) end
function UWBP_EasyGameCreditsMain_C:Finished_23CD2E0C424290844CBB608A445B83B0() end
function UWBP_EasyGameCreditsMain_C:ForceFooterVisibility() end
function UWBP_EasyGameCreditsMain_C:CreditsContainerFinished() end
function UWBP_EasyGameCreditsMain_C:RestartMusic() end
---@param ManuallyExited_ boolean
function UWBP_EasyGameCreditsMain_C:EndCredits(ManuallyExited_) end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_EasyGameCreditsMain_C:Tick(MyGeometry, InDeltaTime) end
---@param Key FKey
function UWBP_EasyGameCreditsMain_C:AnyKeyPressed(Key) end
function UWBP_EasyGameCreditsMain_C:Construct() end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EasyGameCreditsMain_C:NewInputActionTriggered(InputType, ActionValue) end
---@param EntryPoint int32
function UWBP_EasyGameCreditsMain_C:ExecuteUbergraph_WBP_EasyGameCreditsMain(EntryPoint) end
function UWBP_EasyGameCreditsMain_C:CreditsCompleted__DelegateSignature() end
function UWBP_EasyGameCreditsMain_C:CreditsStarted__DelegateSignature() end


