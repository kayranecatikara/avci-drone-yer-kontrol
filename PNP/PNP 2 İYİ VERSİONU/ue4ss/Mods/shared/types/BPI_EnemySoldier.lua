---@meta

---@class IBPI_EnemySoldier_C : IInterface
local IBPI_EnemySoldier_C = {}

---@param Speed E_AI_EnemySoldierMovementSpeed::Type
---@param SpeedValue double
function IBPI_EnemySoldier_C:SetMovementSpeed(Speed, SpeedValue) end
---@param PatroLRoute ABP_PatrolRoute_C
function IBPI_EnemySoldier_C:GetPatrolRoute(PatroLRoute) end


