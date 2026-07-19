---@meta

---@class APC_MainDroneBase_C : APlayerController
---@field UberGraphFrame FPointerToUberGraphFrame
local APC_MainDroneBase_C = {}

function APC_MainDroneBase_C:ReceiveBeginPlay() end
---@param UI boolean
APC_MainDroneBase_C['Set Game or UI Mode'] = function(self, UI) end
---@param EntryPoint int32
function APC_MainDroneBase_C:ExecuteUbergraph_PC_MainDroneBase(EntryPoint) end


