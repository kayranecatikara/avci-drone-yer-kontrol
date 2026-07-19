---@meta

---@class UWBP_EGUI_CommonScrollBox_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field NamedSlot UNamedSlot
---@field ScrollBox UScrollBox
---@field ChildrenContainer UPanelWidget
---@field CommonScrollBarStyle FScrollBarStyle
---@field GlobalStyle FScrollBoxStyle
---@field ScrollBarStyle FScrollBarStyle
---@field ['AutoScroll?'] boolean
---@field AutoScrollSpeed double
---@field DelayBetweenAutoScrolls double
---@field ['AlwaysShowScrollbar?'] boolean
---@field ['UseStylingLocalOverride?'] boolean
---@field Alpha double
---@field ['Inverted?'] boolean
---@field AccentColor FLinearColor
local UWBP_EGUI_CommonScrollBox_C = {}

---@param Navigation EUINavigation
---@return UWidget
function UWBP_EGUI_CommonScrollBox_C:DoCustomNavigation(Navigation) end
---@param CurrentOffset float
function UWBP_EGUI_CommonScrollBox_C:BndEvt__WBP_EOM_CommonScrollBox_ScrollBox_K2Node_ComponentBoundEvent_1_OnUserScrolledEvent__DelegateSignature(CurrentOffset) end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_EGUI_CommonScrollBox_C:Tick(MyGeometry, InDeltaTime) end
function UWBP_EGUI_CommonScrollBox_C:Construct() end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonScrollBox_C:PreConstruct(IsDesignTime) end
---@param EntryPoint int32
function UWBP_EGUI_CommonScrollBox_C:ExecuteUbergraph_WBP_EGUI_CommonScrollBox(EntryPoint) end


