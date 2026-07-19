---@meta

---@class UWBP_EGC_CreditsContainerMaster_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field CreditsContainerFinished FWBP_EGC_CreditsContainerMaster_CCreditsContainerFinished
---@field CreditsSpeedMultiplier double
---@field CreditSections TArray<FS_CreditsSectionDefinition>
---@field SectionTitleStyle FS_CreditsTextStyling
---@field TextSectionRoleStyle FS_CreditsTextStyling
---@field TextSectionNamesStyle FS_CreditsTextStyling
---@field TextSectionOuterMargin FMargin
local UWBP_EGC_CreditsContainerMaster_C = {}

---@param Time double
---@param PlaybackSpeed double
function UWBP_EGC_CreditsContainerMaster_C:GetAnimationSpeedFromTime(Time, PlaybackSpeed) end
---@param Widget UWidget
---@param Padding FMargin
function UWBP_EGC_CreditsContainerMaster_C:SetAlignmentAndPadding(Widget, Padding) end
---@param Panel UPanelWidget
---@param CreditsSectionDefinition FS_CreditsSectionDefinition
function UWBP_EGC_CreditsContainerMaster_C:CreateCreditsSection(Panel, CreditsSectionDefinition) end
---@param Panel UPanelWidget
---@param SizeY double
function UWBP_EGC_CreditsContainerMaster_C:CreateSectionSpacer(Panel, SizeY) end
---@param Panel UPanelWidget
---@param InBrush FSlateBrush
---@param ImagePadding FMargin
function UWBP_EGC_CreditsContainerMaster_C:CreateImageSection(Panel, InBrush, ImagePadding) end
---@param Panel UPanelWidget
---@param TextSectionDefinition FS_CreditsTextSectionDefinition
function UWBP_EGC_CreditsContainerMaster_C:CreateTextSection(Panel, TextSectionDefinition) end
---@param Panel UPanelWidget
---@param Text FText
---@param OverrideStyle_ boolean
---@param StyleOverride FS_CreditsTextStyling
function UWBP_EGC_CreditsContainerMaster_C:CreateSectionTitle(Panel, Text, OverrideStyle_, StyleOverride) end
---@param Text FText
---@param TextStyling FS_CommonTextInfo
---@param TextColor FLinearColor
---@param OutWidget UWidget
function UWBP_EGC_CreditsContainerMaster_C:CreateTextWidget(Text, TextStyling, TextColor, OutWidget) end
---@param NewSpeedMultiplier double
function UWBP_EGC_CreditsContainerMaster_C:UpdateSpeedMultiplier(NewSpeedMultiplier) end
function UWBP_EGC_CreditsContainerMaster_C:CreditsContainerCompleted() end
function UWBP_EGC_CreditsContainerMaster_C:Construct() end
function UWBP_EGC_CreditsContainerMaster_C:StartCreditsContainer() end
---@param EntryPoint int32
function UWBP_EGC_CreditsContainerMaster_C:ExecuteUbergraph_WBP_EGC_CreditsContainerMaster(EntryPoint) end
function UWBP_EGC_CreditsContainerMaster_C:CreditsContainerFinished__DelegateSignature() end


