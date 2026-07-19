---@meta

---@class ABP_EPM_CameraBlockingVolume_C : AActor
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Box UBoxComponent
local ABP_EPM_CameraBlockingVolume_C = {}

---@param Activate_ boolean
function ABP_EPM_CameraBlockingVolume_C:ToggleBlockingVolume(Activate_) end
---@param EntryPoint int32
function ABP_EPM_CameraBlockingVolume_C:ExecuteUbergraph_BP_EPM_CameraBlockingVolume(EntryPoint) end


