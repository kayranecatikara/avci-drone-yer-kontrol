---@meta

---@class UBPC_AIMove_C : UActorComponent
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Spline ABP_Spline_C
---@field Speed double
---@field DistanceAlongSpline double
---@field isLoop boolean
---@field ['Move Actor'] AActor
---@field isDead boolean
---@field ['Pitch Rotation Angle'] double
---@field ['Yaw RotationAngle'] double
---@field ['Mesh Scale'] FVector
local UBPC_AIMove_C = {}

---@param DeltaSeconds float
function UBPC_AIMove_C:ReceiveTick(DeltaSeconds) end
function UBPC_AIMove_C:Dead() end
---@param EntryPoint int32
function UBPC_AIMove_C:ExecuteUbergraph_BPC_AIMove(EntryPoint) end


