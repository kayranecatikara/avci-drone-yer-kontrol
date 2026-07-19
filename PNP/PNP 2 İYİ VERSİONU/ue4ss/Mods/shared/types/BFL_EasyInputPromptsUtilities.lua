---@meta

---@class UBFL_EasyInputPromptsUtilities_C : UBlueprintFunctionLibrary
local UBFL_EasyInputPromptsUtilities_C = {}

---@param Key FKey
---@param __WorldContext UObject
---@param KeyName FName
---@param KeyFound boolean
function UBFL_EasyInputPromptsUtilities_C:GetKeyCultureInvariantName(Key, __WorldContext, KeyName, KeyFound) end
---@param Gamepad_Keys_Brand E_GamepadBrand::Type
---@param __WorldContext UObject
function UBFL_EasyInputPromptsUtilities_C:SetNewGamepadBrand(Gamepad_Keys_Brand, __WorldContext) end
---@param __WorldContext UObject
---@param Gamepad_Keys_Brand E_GamepadBrand::Type
---@param BrandAsString FString
function UBFL_EasyInputPromptsUtilities_C:GetGamepadBrand(__WorldContext, Gamepad_Keys_Brand, BrandAsString) end
---@param KeyMapping FEnhancedActionKeyMapping
---@param __WorldContext UObject
---@param IsGamepadKey boolean
---@param OutKey FKey
function UBFL_EasyInputPromptsUtilities_C:GetRebindedKey(KeyMapping, __WorldContext, IsGamepadKey, OutKey) end
---@param SearchDataTable UDataTable
---@param Key FKey
---@param __WorldContext UObject
---@param ImageFound_ boolean
---@param Image UTexture2D
function UBFL_EasyInputPromptsUtilities_C:GetInputPromptImageFromKey(SearchDataTable, Key, __WorldContext, ImageFound_, Image) end
---@param InputMappingContext UInputMappingContext
---@param InputAction UObject
---@param __WorldContext UObject
---@param MNK_Keys TArray<FKey>
---@param GamepadKeys TArray<FKey>
function UBFL_EasyInputPromptsUtilities_C:GetAllKeysFromInputAction(InputMappingContext, InputAction, __WorldContext, MNK_Keys, GamepadKeys) end
---@param InputActionInfos FS_InputActionDef
---@param __WorldContext UObject
---@param MNK_Key FKey
---@param GamepadKey FKey
function UBFL_EasyInputPromptsUtilities_C:GetSingleKeyFromInputAction(InputActionInfos, __WorldContext, MNK_Key, GamepadKey) end
---@param Key FKey
---@param UseTextSize_ boolean
---@param ManualSize int32
---@param __WorldContext UObject
---@param RichTextOutput FText
function UBFL_EasyInputPromptsUtilities_C:KeyToRichTextQuery(Key, UseTextSize_, ManualSize, __WorldContext, RichTextOutput) end


