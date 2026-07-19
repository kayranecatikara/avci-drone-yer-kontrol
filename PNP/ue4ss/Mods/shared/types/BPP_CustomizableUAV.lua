---@meta

---@class ABPP_CustomizableUAV_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SM_Marble UStaticMeshComponent
---@field SM_SDrone7_Propeller1 UStaticMeshComponent
---@field SM_SDrone7_Propeller2 UStaticMeshComponent
---@field SM_SDrone7_Propeller3 UStaticMeshComponent
---@field SM_Battery7 UStaticMeshComponent
---@field SM_SDrone7_Propeller UStaticMeshComponent
---@field SM_SDrone_7 UStaticMeshComponent
---@field DefaultSceneRoot USceneComponent
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field TrainTransform FTransform
---@field AttackTransform FTransform
---@field FiberTransform10KM FTransform
---@field FiberTransform5KM FTransform
local ABPP_CustomizableUAV_C = {}

---@param NewParam TArray<UStaticMeshComponent>
---@param bNewVisibility boolean
function ABPP_CustomizableUAV_C:SetVisibilityArray(NewParam, bNewVisibility) end
---@param Visibility boolean
---@param UAV_Pieces TArray<UStaticMeshComponent>
---@param ExplosiveBracket USceneComponent
---@param ExplosiveHeavy UStaticMeshComponent
---@param ExplosivePersonalOut UStaticMeshComponent
---@param ExplosivePersonalIn UStaticMeshComponent
function ABPP_CustomizableUAV_C:SetVisibilityUAV(Visibility, UAV_Pieces, ExplosiveBracket, ExplosiveHeavy, ExplosivePersonalOut, ExplosivePersonalIn) end
function ABPP_CustomizableUAV_C:ReceiveBeginPlay() end
function ABPP_CustomizableUAV_C:AllSetNoneVisibilityDrone() end
function ABPP_CustomizableUAV_C:AllSetNoneVisibilityFiber() end
function ABPP_CustomizableUAV_C:AllSetNoneVisibilityComponents() end
function ABPP_CustomizableUAV_C:SetDroneTransform() end
function ABPP_CustomizableUAV_C:SetFiberTransform() end
---@param isVisibility boolean
function ABPP_CustomizableUAV_C:SetVisibilitySDrone7(isVisibility) end
---@param EntryPoint int32
function ABPP_CustomizableUAV_C:ExecuteUbergraph_BPP_CustomizableUAV(EntryPoint) end


