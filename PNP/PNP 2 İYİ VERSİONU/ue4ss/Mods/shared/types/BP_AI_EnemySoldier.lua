---@meta

---@class ABP_AI_EnemySoldier_C : ACharacter
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SM_Body USkeletalMeshComponent
---@field SM_LeftArm USkeletalMeshComponent
---@field SM_RightLeg USkeletalMeshComponent
---@field SM_RightArm USkeletalMeshComponent
---@field SM_LegLeft USkeletalMeshComponent
---@field COL_Interact UCapsuleComponent
---@field Arrow_FireDirection UArrowComponent
---@field isWieldWeapon boolean
---@field PatroLRoute ABP_PatrolRoute_C
---@field AttackEnd FBP_AI_EnemySoldier_CAttackEnd
---@field ['AGame Instance'] UBP_GameInstance_C
---@field ['EExplosive Type'] E_ExplosiveType::Type
---@field isDead boolean
---@field isDroneCircle boolean
---@field isRunbackCircle boolean
---@field ['GM UAV Base'] AGM_UAVBase_C
local ABP_AI_EnemySoldier_C = {}

---@param Speed E_AI_EnemySoldierMovementSpeed::Type
---@param SpeedValue double
function ABP_AI_EnemySoldier_C:SetMovementSpeed(Speed, SpeedValue) end
---@param PatroLRoute ABP_PatrolRoute_C
function ABP_AI_EnemySoldier_C:GetPatrolRoute(PatroLRoute) end
---@param NotifyName FName
function ABP_AI_EnemySoldier_C:OnNotifyEnd_9A5E320B49991A2D22973880ADC25EBA(NotifyName) end
---@param NotifyName FName
function ABP_AI_EnemySoldier_C:OnNotifyBegin_9A5E320B49991A2D22973880ADC25EBA(NotifyName) end
---@param NotifyName FName
function ABP_AI_EnemySoldier_C:OnInterrupted_9A5E320B49991A2D22973880ADC25EBA(NotifyName) end
---@param NotifyName FName
function ABP_AI_EnemySoldier_C:OnBlendOut_9A5E320B49991A2D22973880ADC25EBA(NotifyName) end
---@param NotifyName FName
function ABP_AI_EnemySoldier_C:OnCompleted_9A5E320B49991A2D22973880ADC25EBA(NotifyName) end
function ABP_AI_EnemySoldier_C:Attack() end
---@param IsDetach boolean
function ABP_AI_EnemySoldier_C:WieldWeapon(IsDetach) end
function ABP_AI_EnemySoldier_C:Fire() end
function ABP_AI_EnemySoldier_C:DeadCharacter() end
function ABP_AI_EnemySoldier_C:ReceiveBeginPlay() end
---@param Drone_Pawn ABPP_UAV_C
function ABP_AI_EnemySoldier_C:InteractDrone(Drone_Pawn) end
---@param BPP_Drone_Base ABPP_UAV_C
function ABP_AI_EnemySoldier_C:Interact(BPP_Drone_Base) end
function ABP_AI_EnemySoldier_C:CalculateDistance() end
---@param isAttack boolean
function ABP_AI_EnemySoldier_C:SoldierAttack(isAttack) end
---@param EntryPoint int32
function ABP_AI_EnemySoldier_C:ExecuteUbergraph_BP_AI_EnemySoldier(EntryPoint) end
function ABP_AI_EnemySoldier_C:AttackEnd__DelegateSignature() end


