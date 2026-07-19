---@meta

---@class UDA_EGUI_GlobalStyling_C : UPrimaryDataAsset
---@field AccentColor FLinearColor
---@field InputPromptIconColor FLinearColor
---@field PrimaryTextColor FSlateColor
---@field InvertedTextColor FSlateColor
---@field Fonts TMap<E_FontTypeFaces::Type, FS_FontsStylingInfos>
---@field DefaultButtonStyle FButtonStyle
---@field SecondaryButtonStyle FButtonStyle
---@field CommonScrollBoxStyle FScrollBoxStyle
---@field CommonScrollBarStyle FScrollBarStyle
---@field SettingBackgroundStyle E_BackgroundStyleSelector::Type
---@field SettingBackgroundActiveStyle E_BackgroundStyleSelector::Type
---@field OptionsSelectorsBackgroundStyle E_BackgroundStyleSelector::Type
---@field SettingToggleButtonsStyle E_ButtonStyleSelector::Type
---@field ResetSettingButtonStyle E_ButtonStyleSelector::Type
---@field ProgressBarStyle FProgressBarStyle
---@field SpinBoxStyle FSpinBoxStyle
---@field ['UseInvertedTextColorInSpinBox?'] boolean
---@field KeySelectorNormalStyle FSlateBrush
---@field KeySelectorActiveStyle FSlateBrush
---@field SettingDirtyIndicatorBrush FSlateBrush
---@field EOMSettingTitleTextStyle FS_CommonTextInfo
---@field SettingDirtyIndicatorPadding FMargin
---@field Alternative01ButtonStyle FButtonStyle
---@field Alternative02ButtonStyle FButtonStyle
---@field GameLogo UTexture2D
---@field GlobalCursorStyling TMap<EMouseCursor::Type, TSoftClassPtr<UUserWidget>>
---@field DefaultGamepadKeysBrand E_GamepadBrand::Type
---@field CommonBackgroundStyles TMap<E_BackgroundStyleSelector::Type, FSlateBrush>
---@field ActiveGamepadKeysBrand E_GamepadBrand::Type
---@field Alternative03ButtonStyle FButtonStyle
---@field Alternative04ButtonStyle FButtonStyle
---@field Alternative05ButtonStyle FButtonStyle
---@field SelectorArrowTexture TSoftObjectPtr<UTexture2D>
---@field ['UseAccentColorOnSelectorArrow?'] boolean
---@field SectionTitleStyle FS_CreditsTextStyling
---@field TextSectionRoleStyle FS_CreditsTextStyling
---@field TextSectionNamesStyle FS_CreditsTextStyling
---@field TextSectionOuterMargin FMargin
---@field EOMOptionsValuesTextStyle FS_CommonTextInfo
---@field InputPromptOverlayMaterial UMaterialInterface
---@field InputPromptOverlayMaterialParameterName FName
---@field EPMSettingTitleTextStyle FS_CommonTextInfo
---@field EPMOptionsValuesTextStyle FS_CommonTextInfo
local UDA_EGUI_GlobalStyling_C = {}

---@param SlateBrush FSlateBrush
---@param Corner_Radii FVector4
---@param Rounding_Type ESlateBrushRoundingType::Type
---@param SlateBrushOut FSlateBrush
function UDA_EGUI_GlobalStyling_C:UpdateSlateBrushRoundingValues(SlateBrush, Corner_Radii, Rounding_Type, SlateBrushOut) end
---@param Corner_Radii FVector4
---@param Rounding_Type ESlateBrushRoundingType::Type
function UDA_EGUI_GlobalStyling_C:GetDefaultBackgroundRoundingValues(Corner_Radii, Rounding_Type) end
---@param StyleSelector E_BackgroundStyleSelector::Type
---@param RequestedRoundingType ESlateBrushRoundingType::Type
---@param BackgroundStyling FSlateBrush
function UDA_EGUI_GlobalStyling_C:GetBackgroundStyling(StyleSelector, RequestedRoundingType, BackgroundStyling) end
---@param ButtonStyle E_ButtonStyleSelector::Type
---@param PreferedRoundingType ESlateBrushRoundingType::Type
---@param OutButtonStyle FButtonStyle
function UDA_EGUI_GlobalStyling_C:GetButtonStyling(ButtonStyle, PreferedRoundingType, OutButtonStyle) end
---@param FontInfos FS_FontSelector
---@param FixFontScaling_ boolean
---@param Font FSlateFontInfo
---@param Shadow_offset FVector2D
---@param Shadow_Color FLinearColor
function UDA_EGUI_GlobalStyling_C:GetFont(FontInfos, FixFontScaling_, Font, Shadow_offset, Shadow_Color) end


