---@meta

---@class UWBP_SettingsOption_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ButtonLeft UButton
---@field ButtonRight UButton
---@field SelectionText UTextBlock
---@field Options TArray<FString>
---@field CurrentOption int32
---@field OnOptionsChanged FWBP_SettingsOption_COnOptionsChanged
local UWBP_SettingsOption_C = {}

---@return boolean
function UWBP_SettingsOption_C:Get_ButtonLeft_bIsEnabled() end
---@return boolean
function UWBP_SettingsOption_C:Get_ButtonRight_bIsEnabled() end
function UWBP_SettingsOption_C:Construct() end
---@param NewOption FString
---@param IsCalled boolean
function UWBP_SettingsOption_C:SetSelectedOption(NewOption, IsCalled) end
function UWBP_SettingsOption_C:BndEvt__WBP_SettingsOption_ButtonLeft_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature() end
function UWBP_SettingsOption_C:BndEvt__WBP_SettingsOption_ButtonRight_K2Node_ComponentBoundEvent_1_OnButtonClickedEvent__DelegateSignature() end
function UWBP_SettingsOption_C:BndEvt__WBP_SettingsOption_ButtonRight_K2Node_ComponentBoundEvent_2_OnButtonHoverEvent__DelegateSignature() end
function UWBP_SettingsOption_C:BndEvt__WBP_SettingsOption_ButtonLeft_K2Node_ComponentBoundEvent_3_OnButtonHoverEvent__DelegateSignature() end
---@param EntryPoint int32
function UWBP_SettingsOption_C:ExecuteUbergraph_WBP_SettingsOption(EntryPoint) end
---@param Option FString
---@param OptionIndex int32
function UWBP_SettingsOption_C:OnOptionsChanged__DelegateSignature(Option, OptionIndex) end


