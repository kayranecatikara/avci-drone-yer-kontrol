---@meta

---@class UWBP_ControlMenu_C : UUserWidget
---@field UberGraphFrame FPointerToUberGraphFrame
---@field SavedCalibration UWidgetAnimation
---@field NotAssigned UWidgetAnimation
---@field Assigned UWidgetAnimation
---@field Gate UWidgetAnimation
---@field Btn_Calibration UWBP_EGUI_CommonButton_C
---@field Btn_RESET UWBP_EGUI_CommonButton_C
---@field Button_SkipCalibration UWBP_EGUI_CommonButton_C
---@field CheckBox_Reverse_Pitch UCheckBox
---@field CheckBox_Reverse_Roll UCheckBox
---@field CheckBox_Reverse_Throttle UCheckBox
---@field CheckBox_Reverse_Yaw UCheckBox
---@field ComboBox_Controllers UComboBoxString
---@field Image UImage
---@field Image_1 UImage
---@field Image_2 UImage
---@field Image_3 UImage
---@field Image_4 UImage
---@field Image_5 UImage
---@field Image_6 UImage
---@field Image_7 UImage
---@field Image_8 UImage
---@field Image_9 UImage
---@field Image_10 UImage
---@field Image_11 UImage
---@field Image_12 UImage
---@field Image_13 UImage
---@field Image_136 UImage
---@field Image_BlackScreen1 UImage
---@field Image_ControllerPreview UImage
---@field Image_DronePreview UImage
---@field Loader UCircularThrobber
---@field ProgressBar_Calibration UProgressBar
---@field Text_CalibrationAssigned UTextBlock
---@field Text_CalibrationInfo UTextBlock
---@field Text_CalibrationNotAssigned UTextBlock
---@field Text_CalibrationSaved UTextBlock
---@field Text_CalibrationTimer UTextBlock
---@field WBP_EGUI_CommonHeader UWBP_EGUI_CommonHeader_C
---@field WidgetSwitcher_Previews UWidgetSwitcher
---@field ['HUD Main Menu'] AHUD_MainMenu_C
---@field ['PC Main Drone Base'] APC_MainDroneBase_C
---@field ['BP Settings Save Game'] UBP_SettingsSaveGame_C
---@field ['BP Game Instance'] UBP_GameInstance_C
---@field ['Save Game'] USaveGame
---@field ['Reverse Roll Axis'] double
---@field ['Reverse Pitch Axis'] double
---@field ['Reverse Throttle Axis'] double
---@field ['Reverse Yaw Axis'] double
---@field ['BPP Menu Cam'] ABPP_MenuCam_C
---@field ComboBoxSelection TMap<FString, int32>
---@field buttons TMap<int32, UEditableTextBox>
---@field AxisL TMap<int32, UProgressBar>
---@field AxisR TMap<int32, UProgressBar>
---@field MoveMouseCursor boolean
---@field wheelPosition double
---@field LoadedData FWBP_ControlMenu_CLoadedData
---@field ProfileText FString
---@field InputKeyList FString
---@field deviceName FString
---@field ButtonAxisActiveColor FEditableTextBoxStyle
---@field ButtonAxisDeactiveColor FEditableTextBoxStyle
---@field CustomProfileName FString
---@field ECalibrationPhase E_CalibrationPhases::Type
---@field Counter double
---@field isCountingCalibration boolean
---@field ActionName FString
---@field LastActionName FString
---@field ['DT Calibration'] UDataTable
local UWBP_ControlMenu_C = {}

---@param device FSimpleControllerDevice
---@param found boolean
function UWBP_ControlMenu_C:GetSelectedDevice(device, found) end
---@param AxisL UProgressBar
---@param AxisR UProgressBar
---@param Value double
function UWBP_ControlMenu_C:MoveAxis(AxisL, AxisR, Value) end
---@param device FSimpleControllerDevice
function UWBP_ControlMenu_C:AddControllerToComboBox(device) end
---@param SlotName FString
UWBP_ControlMenu_C['fLoad Controller'] = function(self, SlotName) end
---@param SlotName FString
UWBP_ControlMenu_C['fSave Controller'] = function(self, SlotName) end
---@param AxisValue float
function UWBP_ControlMenu_C:onAction_AF166120485BF22031DF02986A7DD5C0(AxisValue) end
function UWBP_ControlMenu_C:failed_C7D18E6A4DFB828EA999F885FDF2C56D() end
function UWBP_ControlMenu_C:successful_C7D18E6A4DFB828EA999F885FDF2C56D() end
function UWBP_ControlMenu_C:failed_5E103DFA46040F1A1CF277885B39F498() end
function UWBP_ControlMenu_C:successful_5E103DFA46040F1A1CF277885B39F498() end
function UWBP_ControlMenu_C:failed_5675D173453D8263B7ECEBA9ADFFCA8B() end
function UWBP_ControlMenu_C:successful_5675D173453D8263B7ECEBA9ADFFCA8B() end
---@param AxisValue float
function UWBP_ControlMenu_C:onAction_DCD1AE7341723F707CEFE3AA0256B9C1(AxisValue) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:timer_6BF1F7CD4D8456E985A1FEA97FD45756(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:timeOut_6BF1F7CD4D8456E985A1FEA97FD45756(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:isMapped_6BF1F7CD4D8456E985A1FEA97FD45756(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:error_6BF1F7CD4D8456E985A1FEA97FD45756(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:successful_6BF1F7CD4D8456E985A1FEA97FD45756(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end
---@param axisID int32
---@param AxisValue float
---@param connectionIndex int32
---@param device FSimpleControllerDevice
function UWBP_ControlMenu_C:onAction_857356D94B4EBF0639BC49BF1E41A6CF(axisID, AxisValue, connectionIndex, device) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:timer_C9D397EF411A20825530959E8D11A453(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:timeOut_C9D397EF411A20825530959E8D11A453(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:isMapped_C9D397EF411A20825530959E8D11A453(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:error_C9D397EF411A20825530959E8D11A453(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function UWBP_ControlMenu_C:successful_C9D397EF411A20825530959E8D11A453(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end
function UWBP_ControlMenu_C:actionReleased_013A6CD942AF4E1F6738149A58A3B709() end
function UWBP_ControlMenu_C:actionPressed_013A6CD942AF4E1F6738149A58A3B709() end
function UWBP_ControlMenu_C:OnInitialized() end
function UWBP_ControlMenu_C:Construct() end
---@param HideAfter double
function UWBP_ControlMenu_C:ShowLoader(HideAfter) end
function UWBP_ControlMenu_C:BindAttach() end
function UWBP_ControlMenu_C:BindDetach() end
function UWBP_ControlMenu_C:BindButtonDown() end
function UWBP_ControlMenu_C:BindButtonUp() end
function UWBP_ControlMenu_C:BindAxis() end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ControlMenu_C:ondeviceAttachedEventDelegate_Event_0(device, connectionIndex) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ControlMenu_C:ondeviceDetachedEventDelegate_Event_0(device, connectionIndex) end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ControlMenu_C:onButtonDownEventDelegate_Event_0(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function UWBP_ControlMenu_C:onButtonUpEventDelegate_Event_0(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
function UWBP_ControlMenu_C:LoadMappingProfile() end
function UWBP_ControlMenu_C:ResetProfile() end
function UWBP_ControlMenu_C:SaveProfile() end
function UWBP_ControlMenu_C:LoadAllMappings() end
---@param Information FText
---@param Calibrate_Button FText
function UWBP_ControlMenu_C:UpdateCalibrationInfoText(Information, Calibrate_Button) end
function UWBP_ControlMenu_C:ProgressBar() end
function UWBP_ControlMenu_C:StartTimer() end
---@param MyGeometry FGeometry
---@param InDeltaTime float
function UWBP_ControlMenu_C:Tick(MyGeometry, InDeltaTime) end
---@param isAssigned boolean
function UWBP_ControlMenu_C:ShowAssignInfo(isAssigned) end
---@param bInIsEnabledSkip boolean
function UWBP_ControlMenu_C:RestartCalibration(bInIsEnabledSkip) end
---@param bIsChecked boolean
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_CheckBox_Reverse_K2Node_ComponentBoundEvent_1_OnCheckBoxComponentStateChanged__DelegateSignature(bIsChecked) end
---@param bIsChecked boolean
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_CheckBox_Reverse_1_K2Node_ComponentBoundEvent_3_OnCheckBoxComponentStateChanged__DelegateSignature(bIsChecked) end
---@param bIsChecked boolean
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_CheckBox_Reverse_2_K2Node_ComponentBoundEvent_4_OnCheckBoxComponentStateChanged__DelegateSignature(bIsChecked) end
function UWBP_ControlMenu_C:InitializeCheckbox() end
---@param bIsChecked boolean
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_CheckBox_Reverse_3_K2Node_ComponentBoundEvent_5_OnCheckBoxComponentStateChanged__DelegateSignature(bIsChecked) end
---@param SelfIndex int32
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_ContinueBtn_1_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_Btn_Calibration_K2Node_ComponentBoundEvent_12_ButtonClicked__DelegateSignature(SelfIndex) end
---@param SelfIndex int32
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_Btn_Skip_K2Node_ComponentBoundEvent_14_ButtonClicked__DelegateSignature(SelfIndex) end
---@param TabIndex int32
---@param TabName FText
---@param TabCultureInvariantName FString
function UWBP_ControlMenu_C:BndEvt__WBP_ControlMenu_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_0_NewTabSelected__DelegateSignature(TabIndex, TabName, TabCultureInvariantName) end
function UWBP_ControlMenu_C:ConfirmControls() end
---@param EntryPoint int32
function UWBP_ControlMenu_C:ExecuteUbergraph_WBP_ControlMenu(EntryPoint) end
function UWBP_ControlMenu_C:LoadedData__DelegateSignature() end


