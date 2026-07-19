---@meta

---@class ABPP_AIDrone_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Sphere USphereComponent
---@field SM_SDrone7_Explosive1 UStaticMeshComponent
---@field SM_Battery15 UStaticMeshComponent
---@field SM_SDrone15_Bracket UStaticMeshComponent
---@field SM_SDrone15_Propeller4 UStaticMeshComponent
---@field SM_SDrone15_Propeller3 UStaticMeshComponent
---@field SM_SDrone15_Propeller2 UStaticMeshComponent
---@field SM_SDrone15_Propeller1 UStaticMeshComponent
---@field SM_Drone15 UStaticMeshComponent
---@field SM_Battery7 UStaticMeshComponent
---@field SM_SDrone7_Explosive UStaticMeshComponent
---@field SM_SDrone7_Bracket UStaticMeshComponent
---@field SM_SDrone7_Propeller4 UStaticMeshComponent
---@field SM_SDrone7_Propeller3 UStaticMeshComponent
---@field SM_SDrone7_Propeller2 UStaticMeshComponent
---@field SM_SDrone7_Propeller1 UStaticMeshComponent
---@field SM_Drone7 UStaticMeshComponent
---@field Audio UAudioComponent
---@field SM_SDrone10_Bracket UStaticMeshComponent
---@field SM_SDrone10_Explosive UStaticMeshComponent
---@field SM_Battery10 UStaticMeshComponent
---@field SM_SDrone10_Propeller4 UStaticMeshComponent
---@field SM_SDrone10_Propeller3 UStaticMeshComponent
---@field SM_SDrone10_Propeller2 UStaticMeshComponent
---@field SM_SDrone10_Propeller1 UStaticMeshComponent
---@field SM_Drone10 UStaticMeshComponent
---@field BPC_AIMove UBPC_AIMove_C
---@field DefaultSceneRoot USceneComponent
---@field Spline ABP_Spline_C
---@field Speed double
---@field ['Mesh Scale'] FVector
---@field ['Yaw Rotation Angle'] double
---@field ['As BP Game Instance'] UBP_GameInstance_C
---@field ['Pitch Rotation Angle'] double
---@field RandomValue int32
---@field ['Delta Seconds'] float
---@field Countdown double
---@field CounterTimeHandle FTimerHandle
---@field isFinishedTime boolean
---@field ['BP Main OPSoldier'] ABP_MainOPSoldier_C
---@field ['HUD Main Drone'] AHUD_MainUAV_C
---@field ['BP OPSoldier'] ABP_OPSoldier_C
local ABPP_AIDrone_C = {}

function ABPP_AIDrone_C:Counter() end
function ABPP_AIDrone_C:UserConstructionScript() end
---@param isShow boolean
function ABPP_AIDrone_C:SetVisibility7(isShow) end
---@param isShow boolean
function ABPP_AIDrone_C:SetVisibility10(isShow) end
---@param isShow boolean
function ABPP_AIDrone_C:SetVisibility15(isShow) end
function ABPP_AIDrone_C:ReceiveBeginPlay() end
function ABPP_AIDrone_C:HideAllDrones() end
function ABPP_AIDrone_C:SuccessfulKamikaze() end
---@param DeltaSeconds float
function ABPP_AIDrone_C:ReceiveTick(DeltaSeconds) end
function ABPP_AIDrone_C:OPSoldierDead_Event() end
---@param EntryPoint int32
function ABPP_AIDrone_C:ExecuteUbergraph_BPP_AIDrone(EntryPoint) end


