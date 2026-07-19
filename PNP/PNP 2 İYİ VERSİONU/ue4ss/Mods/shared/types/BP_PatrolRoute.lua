---@meta

---@class ABP_PatrolRoute_C : AActor
---@field UberGraphFrame FPointerToUberGraphFrame
---@field PatroLRoute USplineComponent
---@field DefaultSceneRoot USceneComponent
---@field RouteIndex int32
---@field Direction int32
local ABP_PatrolRoute_C = {}

---@param Location FVector
function ABP_PatrolRoute_C:WorldLocationOfSplinePoint(Location) end
function ABP_PatrolRoute_C:IncrementPatrolRouteIndex() end
---@param EntryPoint int32
function ABP_PatrolRoute_C:ExecuteUbergraph_BP_PatrolRoute(EntryPoint) end


