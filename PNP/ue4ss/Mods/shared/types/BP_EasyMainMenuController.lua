---@meta

---@class ABP_EasyMainMenuController_C : APawn
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Billboard UBillboardComponent
---@field Scene USceneComponent
---@field PlayerControllerRef APlayerController
---@field MainMenuWidgetRef UWBP_EasyMainMenu_C
---@field TargetCameraBindings TMap<TSoftObjectPtr<AActor>, FS_MainMenuCameraBindings>
---@field TargetCameras TArray<AActor>
---@field CameraBindingsValues TArray<FS_MainMenuCameraBindings>
local ABP_EasyMainMenuController_C = {}

---@param ButtonIndex int32
function ABP_EasyMainMenuController_C:AnyButtonFocused(ButtonIndex) end
---@param RequestedCamera int32
---@param BlendTime float
function ABP_EasyMainMenuController_C:SetViewpointToCamera(RequestedCamera, BlendTime) end
function ABP_EasyMainMenuController_C:ReceiveBeginPlay() end
---@param EntryPoint int32
function ABP_EasyMainMenuController_C:ExecuteUbergraph_BP_EasyMainMenuController(EntryPoint) end


