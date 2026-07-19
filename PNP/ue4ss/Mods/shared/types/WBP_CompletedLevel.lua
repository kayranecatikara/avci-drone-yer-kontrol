---@meta

---@class UWBP_CompletedLevel_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field MissionFailed UWidgetAnimation
---@field End UWidgetAnimation
---@field MissionCompleted UWidgetAnimation
---@field Btn_MENU UWBP_EGUI_CommonButton_C
---@field Btn_PlayAgain UWBP_EGUI_CommonButton_C
---@field Image_BlackScreen UImage
---@field ['BP Game Instance'] UBP_GameInstance_C
local UWBP_CompletedLevel_C = {}

---@param isFail boolean
function UWBP_CompletedLevel_C:CompletedLevel(isFail) end
function UWBP_CompletedLevel_C:Construct() end
---@param SelfIndex int32
function UWBP_CompletedLevel_C:BndEvt__WBP_CompletedLevel_Btn_MENU_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_CompletedLevel_C:BndEvt__WBP_CompletedLevel_Btn_PlayAgain_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(SelfIndex) end
---@param EntryPoint int32
function UWBP_CompletedLevel_C:ExecuteUbergraph_WBP_CompletedLevel(EntryPoint) end


