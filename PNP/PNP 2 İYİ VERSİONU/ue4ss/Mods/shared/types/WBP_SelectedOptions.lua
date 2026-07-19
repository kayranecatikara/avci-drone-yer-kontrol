---@meta

---@class UWBP_SelectedOptions_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Btn_MENU_1 UWBP_EGUI_CommonButton_C
---@field SaveFileThumbnail UImage
---@field Text_MapName UTextBlock
---@field TextBlock_Type UTextBlock
---@field TextBlock_UAV UTextBlock
---@field [' BP Game Instance'] UBP_GameInstance_C
---@field DTMaps UDataTable
---@field ['Card Picture'] UMaterial
---@field OnClickedScoreboard FWBP_SelectedOptions_COnClickedScoreboard
local UWBP_SelectedOptions_C = {}

---@param Level E_Levels::Type
---@param CardTexture UTexture2D
function UWBP_SelectedOptions_C:GetCustomDataTable(Level, CardTexture) end
function UWBP_SelectedOptions_C:UpdateInformation() end
function UWBP_SelectedOptions_C:Construct() end
---@param SelfIndex int32
function UWBP_SelectedOptions_C:BndEvt__WBP_SelectedOptions_Btn_MENU_1_K2Node_ComponentBoundEvent_1_ButtonClicked__DelegateSignature(SelfIndex) end
---@param EntryPoint int32
function UWBP_SelectedOptions_C:ExecuteUbergraph_WBP_SelectedOptions(EntryPoint) end
function UWBP_SelectedOptions_C:OnClickedScoreboard__DelegateSignature() end


