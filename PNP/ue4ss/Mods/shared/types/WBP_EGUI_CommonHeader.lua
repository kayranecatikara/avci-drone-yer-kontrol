---@meta

---@class UWBP_EGUI_CommonHeader_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field ActiveTabIndicator UHorizontalBox
---@field Header UHorizontalBox
---@field TitleText UWBP_EGUI_CommonText_C
---@field ButtonsReferences TArray<UWBP_EGUI_CommonButton_C>
---@field TabsDefinition TArray<FS_CultureInvariantOptionsValues>
---@field DefaultActiveTab int32
---@field ['ManuallySelectInitialTab?'] boolean
---@field WidgetSwitcherRef UWidgetSwitcher
---@field ['DisplayTitleOnly?'] boolean
---@field ['DisplayActiveTabIndicator?'] boolean
---@field TabIndicatorsPadding FMargin
---@field ButtonsTextStyling FS_CommonTextInfo
---@field ButtonsSpacing double
---@field ButtonsStyle E_ButtonStyleSelector::Type
---@field ButtonsTextPadding FMargin
---@field ButtonSelectionIndicatorPosition E_SelectionIndicatorPosition::Type
---@field TitleTextStyling FS_CommonTextInfo
---@field NewTabSelected FWBP_EGUI_CommonHeader_CNewTabSelected
---@field CurrentTab int32
---@field SelectionIndicators TArray<UWBP_ActiveSelectIndicator_C>
local UWBP_EGUI_CommonHeader_C = {}

function UWBP_EGUI_CommonHeader_C:RefreshSelectionIndicators() end
---@param ButtonIndex int32
---@param Text FText
---@param Text_Culture_Invariant FString
function UWBP_EGUI_CommonHeader_C:GetTabName(ButtonIndex, Text, Text_Culture_Invariant) end
---@param Next_ boolean
function UWBP_EGUI_CommonHeader_C:GoToPreviousOrNextTab(Next_) end
---@param ButtonTitle FText
---@param CurrentIndex int32
function UWBP_EGUI_CommonHeader_C:CreateNewButton(ButtonTitle, CurrentIndex) end
---@param SelfIndex int32
function UWBP_EGUI_CommonHeader_C:ButtonClicked_Event(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_EGUI_CommonHeader_C:PreConstruct(IsDesignTime) end
function UWBP_EGUI_CommonHeader_C:Construct() end
---@param TabIndex int32
function UWBP_EGUI_CommonHeader_C:SelectInitialTab(TabIndex) end
---@param EntryPoint int32
function UWBP_EGUI_CommonHeader_C:ExecuteUbergraph_WBP_EGUI_CommonHeader(EntryPoint) end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_EGUI_CommonHeader_C:NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end


