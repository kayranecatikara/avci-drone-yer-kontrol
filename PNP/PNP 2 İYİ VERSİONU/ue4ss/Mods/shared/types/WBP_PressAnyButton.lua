---@meta

---@class UWBP_PressAnyButton_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field PressTheButtonFade UWidgetAnimation
---@field FadeOut UWidgetAnimation
---@field Image_226 UImage
---@field Image_334 UImage
---@field Image_Background UImage
---@field Image_BlackBarBottom UImage
---@field Image_BlackBarTop UImage
---@field Image_Logo UImage
---@field Image_LogoShadow UImage
---@field WBP_EGUI_CommonButton UWBP_EGUI_CommonButton_C
---@field WBP_EGUI_CommonText UWBP_EGUI_CommonText_C
---@field [' HUD Main Menu'] AHUD_MainMenu_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field IntroMediaPlayer UMediaPlayer
local UWBP_PressAnyButton_C = {}

function UWBP_PressAnyButton_C:Construct() end
function UWBP_PressAnyButton_C:PressedAnyButton() end
---@param SelfIndex int32
function UWBP_PressAnyButton_C:BndEvt__WBP_PressAnyButton_WBP_EGUI_CommonButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param EntryPoint int32
function UWBP_PressAnyButton_C:ExecuteUbergraph_WBP_PressAnyButton(EntryPoint) end


