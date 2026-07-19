---@meta

---@class ABPP_Drone_SD_15PLUS_C : ABPP_UAV_Drone_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SM_Drone_PropellerFR2 UStaticMeshComponent
---@field SM_Drone_PropellerFL2 UStaticMeshComponent
---@field SM_Drone_PropellerRL2 UStaticMeshComponent
---@field SM_Drone_PropellerRR2 UStaticMeshComponent
local ABPP_Drone_SD_15PLUS_C = {}

---@param DeltaSeconds float
function ABPP_Drone_SD_15PLUS_C:ReceiveTick(DeltaSeconds) end
---@param EntryPoint int32
function ABPP_Drone_SD_15PLUS_C:ExecuteUbergraph_BPP_Drone_SD_15PLUS(EntryPoint) end


