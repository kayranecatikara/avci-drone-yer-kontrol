---@meta

---@class UGamepadSensitivity_C : UInputModifier
---@field Sensitivity double
local UGamepadSensitivity_C = {}

---@param PlayerInput UEnhancedPlayerInput
---@param CurrentValue FInputActionValue
---@param DeltaTime float
---@return FInputActionValue
function UGamepadSensitivity_C:ModifyRaw(PlayerInput, CurrentValue, DeltaTime) end


