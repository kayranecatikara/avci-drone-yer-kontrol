---@meta

---@class UWBP_EGC_FadeCreditsContainer_C : UWBP_EGC_CreditsContainerMaster_C
---@field UberGraphFrame FPointerToUberGraphFrame
---@field IdleContainerAnimation UWidgetAnimation
---@field FadeInOutContainerAnimation UWidgetAnimation
---@field VerticalBox UVerticalBox
---@field CurrentIndex int32
---@field FadeInDuration double
---@field SectionDuration double
---@field FadeOutDuration double
local UWBP_EGC_FadeCreditsContainer_C = {}

---@param Widget UWidget
---@param Padding FMargin
function UWBP_EGC_FadeCreditsContainer_C:SetAlignmentAndPadding(Widget, Padding) end
function UWBP_EGC_FadeCreditsContainer_C:Finished_EBE509394EB8D0E45CF7E79C91978CF3() end
function UWBP_EGC_FadeCreditsContainer_C:Finished_C23126DA4D92287ADEA179AFFAFD12AD() end
function UWBP_EGC_FadeCreditsContainer_C:DisplayNextCredits() end
function UWBP_EGC_FadeCreditsContainer_C:StartCreditsContainer() end
---@param NewSpeedMultiplier double
function UWBP_EGC_FadeCreditsContainer_C:UpdateSpeedMultiplier(NewSpeedMultiplier) end
---@param EntryPoint int32
function UWBP_EGC_FadeCreditsContainer_C:ExecuteUbergraph_WBP_EGC_FadeCreditsContainer(EntryPoint) end


