---@meta

---@class UWBP_EGC_ScrollCreditsContainer_C : UWBP_EGC_CreditsContainerMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ScrollBox UScrollBox
---@field AutoScrollSpeed double
---@field ['Scroll?'] boolean
---@field ScrollOffsetOfEnd float
---@field CurrentScroll double
local UWBP_EGC_ScrollCreditsContainer_C = {}

---@param Widget UWidget
---@param Padding FMargin
function UWBP_EGC_ScrollCreditsContainer_C:SetAlignmentAndPadding(Widget, Padding) end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_EGC_ScrollCreditsContainer_C:Tick(MyGeometry, InDeltaTime) end
function UWBP_EGC_ScrollCreditsContainer_C:StartCreditsContainer() end
function UWBP_EGC_ScrollCreditsContainer_C:Construct() end
---@param CurrentOffset float
function UWBP_EGC_ScrollCreditsContainer_C:BndEvt__WBP_ScrollCreditsContainer_ScrollBox_K2Node_ComponentBoundEvent_0_OnUserScrolledEvent__DelegateSignature(CurrentOffset) end
---@param EntryPoint int32
function UWBP_EGC_ScrollCreditsContainer_C:ExecuteUbergraph_WBP_EGC_ScrollCreditsContainer(EntryPoint) end


