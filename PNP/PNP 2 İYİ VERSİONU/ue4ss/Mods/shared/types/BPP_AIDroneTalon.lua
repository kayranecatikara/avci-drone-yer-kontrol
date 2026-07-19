---@meta

---@class ABPP_AIDroneTalon_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field TalonGPSSpoof UTalonGPSSpoofComponent
---@field SM_Talon_WingSmall_R UStaticMeshComponent
---@field SM_Talon_WingSmall_L UStaticMeshComponent
---@field SM_Talon_Wing_R UStaticMeshComponent
---@field SM_Talon_Wing_L UStaticMeshComponent
---@field SM_Talon_Body UStaticMeshComponent
---@field Box UBoxComponent
---@field SM_Talon_Propeller UStaticMeshComponent
---@field Arrow UArrowComponent
---@field Banking UBankingComponent
---@field Audio UAudioComponent
---@field BPC_AIMove UBPC_AIMove_C
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
---@field Crashed boolean
---@field ['As GM UAVBase'] AGM_UAVBase_C
---@field Pieces TArray<UStaticMeshComponent>
---@field PiecesCopy TArray<UStaticMeshComponent>
local ABPP_AIDroneTalon_C = {}

function ABPP_AIDroneTalon_C:Counter() end
function ABPP_AIDroneTalon_C:UserConstructionScript() end
---@param DeltaSeconds float
function ABPP_AIDroneTalon_C:ReceiveTick(DeltaSeconds) end
---@param OverlappedComponent UPrimitiveComponent
---@param OtherActor AActor
---@param OtherComp UPrimitiveComponent
---@param OtherBodyIndex int32
---@param bFromSweep boolean
---@param SweepResult FHitResult
function ABPP_AIDroneTalon_C:BndEvt__BPP_AIDroneTalon_Box_K2Node_ComponentBoundEvent_1_ComponentBeginOverlapSignature__DelegateSignature(OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult) end
function ABPP_AIDroneTalon_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function ABPP_AIDroneTalon_C:ExecuteUbergraph_BPP_AIDroneTalon(EntryPoint) end


