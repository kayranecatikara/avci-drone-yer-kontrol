---@meta

---@class UBP_AnimNotify_Fire_C : UAnimNotify
local UBP_AnimNotify_Fire_C = {}

function UBP_AnimNotify_Fire_C:NewFunction() end
---@param MeshComp USkeletalMeshComponent
---@param Animation UAnimSequenceBase
---@param EventReference FAnimNotifyEventReference
---@return boolean
function UBP_AnimNotify_Fire_C:Received_Notify(MeshComp, Animation, EventReference) end


