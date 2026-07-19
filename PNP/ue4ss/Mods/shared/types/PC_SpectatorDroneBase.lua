---@meta

---@class APC_SpectatorDroneBase_C : APlayerController
---@field UberGraphFrame FPointerToUberGraphFrame
local APC_SpectatorDroneBase_C = {}

---@param UI boolean
APC_SpectatorDroneBase_C['Set Game or UI Mode'] = function(self, UI) end
function APC_SpectatorDroneBase_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function APC_SpectatorDroneBase_C:ExecuteUbergraph_PC_SpectatorDroneBase(EntryPoint) end


