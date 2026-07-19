---@meta

---@class ABPP_Tablet_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Text_Total UTextRenderComponent
---@field Text_TotalFlightTime UTextRenderComponent
---@field Text_SuccessKillCount UTextRenderComponent
---@field SM_Tablet UStaticMeshComponent
---@field DefaultSceneRoot USceneComponent
---@field InitialLocation FVector
local ABPP_Tablet_C = {}

---@param List TArray<FString>
---@param Sum int32
function ABPP_Tablet_C:SumListString(List, Sum) end
---@param List TArray<int32>
---@param Sum int32
function ABPP_Tablet_C:SumList(List, Sum) end
---@param Show boolean
function ABPP_Tablet_C:ShowTabletInformation(Show) end
---@param EntryPoint int32
function ABPP_Tablet_C:ExecuteUbergraph_BPP_Tablet(EntryPoint) end


