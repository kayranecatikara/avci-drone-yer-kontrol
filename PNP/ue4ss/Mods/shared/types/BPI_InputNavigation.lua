---@meta

---@class IBPI_InputNavigation_C : IInterface
local IBPI_InputNavigation_C = {}

---@param Key FKey
function IBPI_InputNavigation_C:AnyKeyPressed(Key) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function IBPI_InputNavigation_C:NewInputActionTriggered(InputType, ActionValue) end


