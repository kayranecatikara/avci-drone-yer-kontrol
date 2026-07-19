---@meta

---@class UWBP_ESGU_LoadingScreen_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field FadeAnimation UWidgetAnimation
---@field Background UWBP_EGUI_CommonBackgroundImage_C
---@field ObjectiveDisplayer UWBP_EGUI_OptionDescription_C
---@field Text UWBP_EGUI_CommonText_C
---@field BackgroundImage UTexture2D
---@field TipText FText
---@field OperationType E_SaveGameOperationType::Type
local UWBP_ESGU_LoadingScreen_C = {}

function UWBP_ESGU_LoadingScreen_C:Finished_C781A7CD4B96653F3B54FA8BB8742C76() end
---@param Loaded UObject
function UWBP_ESGU_LoadingScreen_C:OnLoaded_0432773E4B382506B3F04E8CE953645F(Loaded) end
function UWBP_ESGU_LoadingScreen_C:Construct() end
---@param PlayFadeAnimation_ boolean
---@param Duration double
function UWBP_ESGU_LoadingScreen_C:StopLoadingScreenAfterDelay(PlayFadeAnimation_, Duration) end
---@param OperationType E_SaveGameOperationType::Type
---@param PlayFadeAnimation_ boolean
function UWBP_ESGU_LoadingScreen_C:InitLoadingScreen(OperationType, PlayFadeAnimation_) end
---@param FadeOut_ boolean
function UWBP_ESGU_LoadingScreen_C:PlayFadeAnimation(FadeOut_) end
---@param EntryPoint int32
function UWBP_ESGU_LoadingScreen_C:ExecuteUbergraph_WBP_ESGU_LoadingScreen(EntryPoint) end


