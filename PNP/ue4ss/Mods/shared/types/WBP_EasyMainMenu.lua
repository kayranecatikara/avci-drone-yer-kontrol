---@meta

---@class UWBP_EasyMainMenu_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ButtonsContainer UVerticalBox
---@field ContinueBtn UWBP_EGUI_CommonButton_C
---@field CreditsBtn UWBP_EGUI_CommonButton_C
---@field FullscreenLogoPanel UCanvasPanel
---@field LoadSavegameButton UWBP_EGUI_CommonButton_C
---@field Logo UImage
---@field Logo_1 UImage
---@field MainMenuPanel UCanvasPanel
---@field NewGameButton UWBP_EGUI_CommonButton_C
---@field OptionsBtn UWBP_EGUI_CommonButton_C
---@field QuitBtn UWBP_EGUI_CommonButton_C
---@field PlayerControllerRef APlayerController
---@field HUD AHUD
---@field MainMenuClosed FWBP_EasyMainMenu_CMainMenuClosed
---@field MainMenuController ABP_EasyMainMenuController_C
---@field ['MainMenuDisplayed?'] boolean
---@field NewestSaveSlot UBP_EasySaveGameObject_C
---@field QuickSaveTooltip UWBP_EGUI_CommonTooltip_C
---@field DefaultButtonToFocus UWidget
---@field FocusedButtonIndex int32
---@field AnyButtonFocused FWBP_EasyMainMenu_CAnyButtonFocused
---@field ExclusiveButtonIndexes TArray<int32>
local UWBP_EasyMainMenu_C = {}

function UWBP_EasyMainMenu_C:ToggleSaveButtonsIfNotAllowed() end
---@param ButtonToRefocus UWidget
function UWBP_EasyMainMenu_C:GetValidButtonToRefocus(ButtonToRefocus) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_EasyMainMenu_C:OnMouseMove(MyGeometry, MouseEvent) end
---@param IsDesignTime boolean
function UWBP_EasyMainMenu_C:PreConstruct(IsDesignTime) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EasyMainMenu_NewGameButton_K2Node_ComponentBoundEvent_6_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EasyMainMenu_LoadSavegameButton_K2Node_ComponentBoundEvent_7_ButtonClicked__DelegateSignature(SelfIndex) end
---@param ButtonIndex int32
function UWBP_EasyMainMenu_C:LoadSaveAction(ButtonIndex) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EasyMainMenu_CreditsBtn_K2Node_ComponentBoundEvent_6_ButtonClicked__DelegateSignature(SelfIndex) end
---@param Key FKey
function UWBP_EasyMainMenu_C:AnyKeyPressed(Key) end
function UWBP_EasyMainMenu_C:ResetAndCloseMainMenu() end
function UWBP_EasyMainMenu_C:DisplayMainMenuPanel() end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_EasyMainMenu_C:NewInputActionTriggered(InputType, ActionValue) end
---@param ButtonIndex int32
function UWBP_EasyMainMenu_C:QuitGameAction(ButtonIndex) end
function UWBP_EasyMainMenu_C:Construct() end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EOM_DemoPauseMenu_QuitBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:NewButtonFocused(SelfIndex) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EOM_DemoPauseMenu_OptionsBtn_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_EasyMainMenu_C:BndEvt__WBP_EOM_DemoPauseMenu_ContinueBtn_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
function UWBP_EasyMainMenu_C:CreditsCompleted_Event() end
function UWBP_EasyMainMenu_C:SaveManagerClosed() end
function UWBP_EasyMainMenu_C:OptionsMenuClosed() end
---@param EntryPoint int32
function UWBP_EasyMainMenu_C:ExecuteUbergraph_WBP_EasyMainMenu(EntryPoint) end
---@param ButtonIndex int32
function UWBP_EasyMainMenu_C:AnyButtonFocused__DelegateSignature(ButtonIndex) end
function UWBP_EasyMainMenu_C:MainMenuClosed__DelegateSignature() end


