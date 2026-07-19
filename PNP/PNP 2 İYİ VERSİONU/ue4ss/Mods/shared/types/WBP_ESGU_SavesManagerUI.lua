---@meta

---@class UWBP_ESGU_SavesManagerUI_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field Background UWBP_EGUI_CommonBackgroundImage_C
---@field DeleteSlotBtn UWBP_EGUI_CommonButton_C
---@field Divider UBorder
---@field NavBackBtn UWBP_EGUI_CommonButton_C
---@field NewSaveButton UWBP_EGUI_CommonButton_C
---@field SaveFileDetailsBackground UWBP_EGUI_CommonBackground_C
---@field SaveFileDisplayName UWBP_EGUI_CommonText_C
---@field SaveFileThumbnail UImage
---@field SaveOrLoadBtn UWBP_EGUI_CommonButton_C
---@field SavesContainer UVerticalBox
---@field SaveFilesCards TArray<UWBP_ESGU_SaveFileCard_C>
---@field FocusedSaveFile UWBP_ESGU_SaveFileCard_C
---@field FocusedWidget UUserWidget
---@field PlayerControllerRef APlayerController
---@field SaveManagerMenuClosed FWBP_ESGU_SavesManagerUI_CSaveManagerMenuClosed
---@field HUD AHUD
---@field ['Operation Type'] E_SaveGameOperationType::Type
---@field OperationsManager ABP_EasySaveGameOperationsManager_C
---@field RequestedSaveGameOperation FS_SaveOperationInfos
local UWBP_ESGU_SavesManagerUI_C = {}

---@param Operation FS_SaveOperationInfos
function UWBP_ESGU_SavesManagerUI_C:SaveGameOperationEnded(Operation) end
---@param Thumbnail UTexture2D
---@param SaveSlotCardRef UWBP_ESGU_SaveFileCard_C
function UWBP_ESGU_SavesManagerUI_C:UpdateSlotTitleAndThumbnail(Thumbnail, SaveSlotCardRef) end
---@param MyGeometry FGeometry
---@param MouseEvent FPointerEvent
---@return FEventReply
function UWBP_ESGU_SavesManagerUI_C:OnMouseMove(MyGeometry, MouseEvent) end
function UWBP_ESGU_SavesManagerUI_C:SetFocusToFirstWidget() end
---@param SaveFiles TArray<UWBP_ESGU_SaveFileCard_C>
function UWBP_ESGU_SavesManagerUI_C:SortSaveFilesByDate(SaveFiles) end
---@param SelfIndex int32
function UWBP_ESGU_SavesManagerUI_C:BndEvt__WBP_SavesManagerUI_CreateSaveBtn_K2Node_ComponentBoundEvent_2_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_ESGU_SavesManagerUI_C:BndEvt__WBP_SavesManagerUI_DeleteSaveBtn_K2Node_ComponentBoundEvent_3_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_ESGU_SavesManagerUI_C:BndEvt__WBP_SavesManagerUI_NavBackBtn_K2Node_ComponentBoundEvent_4_ButtonClicked__DelegateSignature(SelfIndex) end
---@param ButtonIndex int32
function UWBP_ESGU_SavesManagerUI_C:DeleteSlotAction(ButtonIndex) end
---@param ButtonIndex int32
function UWBP_ESGU_SavesManagerUI_C:OverwriteSlotAction(ButtonIndex) end
---@param OperationType E_SaveGameOperationType::Type
function UWBP_ESGU_SavesManagerUI_C:InitWidget(OperationType) end
---@param SelfIndex int32
function UWBP_ESGU_SavesManagerUI_C:BndEvt__WBP_SaveGamesUI_NewSaveButton_K2Node_ComponentBoundEvent_1_ButtonFocused__DelegateSignature(SelfIndex) end
---@param Key FKey
function UWBP_ESGU_SavesManagerUI_C:AnyKeyPressed(Key) end
---@param InputType E_UI_NavInputList::Type
---@param ActionValue FString
function UWBP_ESGU_SavesManagerUI_C:NewInputActionTriggered(InputType, ActionValue) end
---@param SaveSlotCardRef UWBP_ESGU_SaveFileCard_C
function UWBP_ESGU_SavesManagerUI_C:NewlyFocusedSaveFile(SaveSlotCardRef) end
function UWBP_ESGU_SavesManagerUI_C:RefreshFilesList() end
---@param SelfIndex int32
function UWBP_ESGU_SavesManagerUI_C:BndEvt__WBP_SaveGamesUI_NewSaveButton_K2Node_ComponentBoundEvent_0_ButtonClicked__DelegateSignature(SelfIndex) end
---@param IsDesignTime boolean
function UWBP_ESGU_SavesManagerUI_C:PreConstruct(IsDesignTime) end
function UWBP_ESGU_SavesManagerUI_C:Construct() end
---@param ButtonIndex int32
function UWBP_ESGU_SavesManagerUI_C:LoadSaveAction(ButtonIndex) end
function UWBP_ESGU_SavesManagerUI_C:TriggerSaveOrLoad() end
---@param EntryPoint int32
function UWBP_ESGU_SavesManagerUI_C:ExecuteUbergraph_WBP_ESGU_SavesManagerUI(EntryPoint) end
function UWBP_ESGU_SavesManagerUI_C:SaveManagerMenuClosed__DelegateSignature() end


