---@meta

---@class UWBP_MainMenu_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field BackgroundBlur_Empty UBackgroundBlur
---@field BackgroundBlur_Full UBackgroundBlur
---@field BackgroundBlur_Half UBackgroundBlur
---@field Btn_CONTROLS UWBP_EGUI_CommonButton_C
---@field Btn_FLY UWBP_EGUI_CommonButton_C
---@field Btn_Maps UWBP_EGUI_CommonButton_C
---@field Btn_MENU UWBP_EGUI_CommonButton_C
---@field Btn_SETTINGS UWBP_EGUI_CommonButton_C
---@field Btn_UAV UWBP_EGUI_CommonButton_C
---@field ButtonsContainer UVerticalBox
---@field Image_Empty UImage
---@field QuitBtn UWBP_EGUI_CommonButton_C
---@field WBP_ControlMenu UWBP_ControlMenu_C
---@field WBP_LevelSelection UWBP_LevelSelection_C
---@field WBP_ScoreboardBase UWBP_ScoreboardBase_C
---@field WBP_SelectedOptions UWBP_SelectedOptions_C
---@field WBP_SettingsMenu UWBP_SettingsMenu_C
---@field WBP_UAVSelection UWBP_UAVSelection_C
---@field WidgetSwitcher_Blur UWidgetSwitcher
---@field WidgetSwitcher_Panels UWidgetSwitcher
---@field ['HUD Main Menu'] AHUD_MainMenu_C
---@field ['BPP Main Drone'] ABPP_UAV_C
---@field ['BP Save Game Player'] UBP_SaveGame_Player_C
---@field SaveRef USaveGame
---@field PlayerNickname FText
---@field ['BPP Menu Cam'] ABPP_MenuCam_C
---@field ['BPP Tablet'] ABPP_Tablet_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['GM Main Menu'] AGM_MainMenu_C
---@field BPPCustomizableUAV ABPP_CustomizableUAV_C
local UWBP_MainMenu_C = {}

function UWBP_MainMenu_C:Construct() end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_FLY_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_SETTINGS_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_CONTROLS_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_QuitBtn_K2Node_ComponentBoundEvent_8_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_MENU_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_FLY_1_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_WBP_LevelSelection_K2Node_ComponentBoundEvent_6_OnClickAnyButton__DelegateSignature() end
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_WBP_UAVSelection_K2Node_ComponentBoundEvent_7_OnClickAnyButton__DelegateSignature() end
---@param SelfIndex int32
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_Btn_FLY_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(SelfIndex) end
function UWBP_MainMenu_C:BndEvt__WBP_MainMenu_WBP_SelectedOptions_K2Node_ComponentBoundEvent_12_OnClickedScoreboard__DelegateSignature() end
function UWBP_MainMenu_C:LoadScoreboardData() end
---@param EntryPoint int32
function UWBP_MainMenu_C:ExecuteUbergraph_WBP_MainMenu(EntryPoint) end


