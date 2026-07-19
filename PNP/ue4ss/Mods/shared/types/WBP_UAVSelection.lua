---@meta

---@class UWBP_UAVSelection_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Gate UWidgetAnimation
---@field CanvasPanel_Main UCanvasPanel
---@field Image_ExtraVideo UImage
---@field Image_Outline UImage
---@field Overlay_HoverCardVideo UOverlay
---@field WBP_EGUI_CommonHeader UWBP_EGUI_CommonHeader_C
---@field WBP_MapCard_Big UWBP_MenuCard_C
---@field WBP_MapCard_Heavy UWBP_MenuCard_C
---@field WBP_MapCard_Kargu UWBP_MenuCard_C
---@field WBP_MapCard_LockKit UWBP_MenuCard_C
---@field WBP_MapCard_Normal UWBP_MenuCard_C
---@field WBP_MapCard_Personal UWBP_MenuCard_C
---@field WBP_MapCard_PushImpact UWBP_MenuCard_C
---@field WBP_MapCard_SD10 UWBP_MenuCard_C
---@field WBP_MapCard_SD15 UWBP_MenuCard_C
---@field ['WBP_MapCard_SD15+'] UWBP_MenuCard_C
---@field WBP_MapCard_SD7 UWBP_MenuCard_C
---@field WBP_MapCard_SDMINI UWBP_MenuCard_C
---@field WBP_MapCard_Skydagger UWBP_MenuCard_C
---@field WBP_MapCard_Small UWBP_MenuCard_C
---@field WBP_MapCard_Thermal UWBP_MenuCard_C
---@field WBP_MapCard_TOYCA UWBP_MenuCard_C
---@field WidgetSwitcher UWidgetSwitcher
---@field ['HUD Main Menu'] AHUD_MainMenu_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['BPP Customizable Drone'] ABPP_CustomizableUAV_C
---@field isOnThermal boolean
---@field isOnLockKit boolean
---@field isOnPushImpact boolean
---@field canFollowMouseGIF boolean
---@field MediaPlayerThermal UMediaPlayer
---@field MediaPlayerLockKit UMediaPlayer
---@field OnClickAnyButton FWBP_UAVSelection_COnClickAnyButton
---@field MediaPlayerPushImpactPersonal UMediaPlayer
---@field MediaPlayerPushImpactHeavy UMediaPlayer
local UWBP_UAVSelection_C = {}

function UWBP_UAVSelection_C:Construct() end
---@param IsOn boolean
function UWBP_UAVSelection_C:SetLockKitOnOff(IsOn) end
---@param IsOn boolean
function UWBP_UAVSelection_C:SetThermalOnOff(IsOn) end
---@param E_UAV E_UAV::Type
UWBP_UAVSelection_C['Set Drone Type'] = function(self, E_UAV) end
---@param IsOn boolean
function UWBP_UAVSelection_C:SetPushImpactOnOff(IsOn) end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_UAVSelection_C:Tick(MyGeometry, InDeltaTime) end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_24_NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_11_K2Node_ComponentBoundEvent_0_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_9_K2Node_ComponentBoundEvent_4_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_K2Node_ComponentBoundEvent_26_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_1_K2Node_ComponentBoundEvent_27_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_2_K2Node_ComponentBoundEvent_28_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_3_K2Node_ComponentBoundEvent_29_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_4_K2Node_ComponentBoundEvent_34_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_5_K2Node_ComponentBoundEvent_35_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_38_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_39_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_40_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_44_OnUnhover__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_Thermal_K2Node_ComponentBoundEvent_45_OnHover__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_46_OnHover__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_LockKit_K2Node_ComponentBoundEvent_47_OnUnhover__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_Heavy_K2Node_ComponentBoundEvent_52_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_Personal_K2Node_ComponentBoundEvent_53_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:LoadInformation() end
function UWBP_UAVSelection_C:CheckPushImpact() end
UWBP_UAVSelection_C['BndEvt__WBP_UAVSelection_WBP_MapCard_SD15+_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature'] = function(self, ) end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_SDMINI_K2Node_ComponentBoundEvent_2_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_TOYCA_K2Node_ComponentBoundEvent_3_OnClicked__DelegateSignature() end
function UWBP_UAVSelection_C:ShowGlitchEffect() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_5_OnHover__DelegateSignature() end
function UWBP_UAVSelection_C:BndEvt__WBP_UAVSelection_WBP_MapCard_PushImpact_K2Node_ComponentBoundEvent_6_OnUnhover__DelegateSignature() end
---@param MenuCard TArray<UWBP_MenuCard_C>
---@param Type uint8
function UWBP_UAVSelection_C:SetSelectedOption(MenuCard, Type) end
function UWBP_UAVSelection_C:SetSelectedUAV() end
function UWBP_UAVSelection_C:SetSelectedController() end
function UWBP_UAVSelection_C:SetSelectedAmmunition() end
function UWBP_UAVSelection_C:SetSelectedFiber() end
function UWBP_UAVSelection_C:InitializeSetSelectedExtra() end
function UWBP_UAVSelection_C:SetAllSelectedOptions() end
---@param EntryPoint int32
function UWBP_UAVSelection_C:ExecuteUbergraph_WBP_UAVSelection(EntryPoint) end
function UWBP_UAVSelection_C:OnClickAnyButton__DelegateSignature() end


