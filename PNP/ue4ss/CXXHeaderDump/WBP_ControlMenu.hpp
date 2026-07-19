#ifndef UE4SS_SDK_WBP_ControlMenu_HPP
#define UE4SS_SDK_WBP_ControlMenu_HPP

class UWBP_ControlMenu_C : public UUserWidget
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x02D0 (size: 0x8)
    class UWidgetAnimation* SavedCalibration;                                         // 0x02D8 (size: 0x8)
    class UWidgetAnimation* NotAssigned;                                              // 0x02E0 (size: 0x8)
    class UWidgetAnimation* Assigned;                                                 // 0x02E8 (size: 0x8)
    class UWidgetAnimation* Gate;                                                     // 0x02F0 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_Calibration;                                  // 0x02F8 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Btn_Reset;                                        // 0x0300 (size: 0x8)
    class UWBP_EGUI_CommonButton_C* Button_SkipCalibration;                           // 0x0308 (size: 0x8)
    class UCheckBox* CheckBox_Reverse_Pitch;                                          // 0x0310 (size: 0x8)
    class UCheckBox* CheckBox_Reverse_Roll;                                           // 0x0318 (size: 0x8)
    class UCheckBox* CheckBox_Reverse_Throttle;                                       // 0x0320 (size: 0x8)
    class UCheckBox* CheckBox_Reverse_Yaw;                                            // 0x0328 (size: 0x8)
    class UComboBoxString* ComboBox_Controllers;                                      // 0x0330 (size: 0x8)
    class UImage* Image;                                                              // 0x0338 (size: 0x8)
    class UImage* Image_1;                                                            // 0x0340 (size: 0x8)
    class UImage* Image_2;                                                            // 0x0348 (size: 0x8)
    class UImage* Image_3;                                                            // 0x0350 (size: 0x8)
    class UImage* Image_4;                                                            // 0x0358 (size: 0x8)
    class UImage* Image_5;                                                            // 0x0360 (size: 0x8)
    class UImage* Image_6;                                                            // 0x0368 (size: 0x8)
    class UImage* Image_7;                                                            // 0x0370 (size: 0x8)
    class UImage* Image_8;                                                            // 0x0378 (size: 0x8)
    class UImage* Image_9;                                                            // 0x0380 (size: 0x8)
    class UImage* Image_10;                                                           // 0x0388 (size: 0x8)
    class UImage* Image_11;                                                           // 0x0390 (size: 0x8)
    class UImage* Image_12;                                                           // 0x0398 (size: 0x8)
    class UImage* Image_13;                                                           // 0x03A0 (size: 0x8)
    class UImage* Image_136;                                                          // 0x03A8 (size: 0x8)
    class UImage* Image_BlackScreen1;                                                 // 0x03B0 (size: 0x8)
    class UImage* Image_ControllerPreview;                                            // 0x03B8 (size: 0x8)
    class UImage* Image_DronePreview;                                                 // 0x03C0 (size: 0x8)
    class UCircularThrobber* Loader;                                                  // 0x03C8 (size: 0x8)
    class UProgressBar* ProgressBar_Calibration;                                      // 0x03D0 (size: 0x8)
    class UTextBlock* Text_CalibrationAssigned;                                       // 0x03D8 (size: 0x8)
    class UTextBlock* Text_CalibrationInfo;                                           // 0x03E0 (size: 0x8)
    class UTextBlock* Text_CalibrationNotAssigned;                                    // 0x03E8 (size: 0x8)
    class UTextBlock* Text_CalibrationSaved;                                          // 0x03F0 (size: 0x8)
    class UTextBlock* Text_CalibrationTimer;                                          // 0x03F8 (size: 0x8)
    class UWBP_EGUI_CommonHeader_C* WBP_EGUI_CommonHeader;                            // 0x0400 (size: 0x8)
    class UWidgetSwitcher* WidgetSwitcher_Previews;                                   // 0x0408 (size: 0x8)
    class AHUD_MainMenu_C* HUD Main Menu;                                             // 0x0410 (size: 0x8)
    class APC_MainDroneBase_C* PC Main Drone Base;                                    // 0x0418 (size: 0x8)
    class UBP_SettingsSaveGame_C* BP Settings Save Game;                              // 0x0420 (size: 0x8)
    class UBP_GameInstance_C* BP Game Instance;                                       // 0x0428 (size: 0x8)
    class USaveGame* Save Game;                                                       // 0x0430 (size: 0x8)
    double Reverse Roll Axis;                                                         // 0x0438 (size: 0x8)
    double Reverse Pitch Axis;                                                        // 0x0440 (size: 0x8)
    double Reverse Throttle Axis;                                                     // 0x0448 (size: 0x8)
    double Reverse Yaw Axis;                                                          // 0x0450 (size: 0x8)
    class ABPP_MenuCam_C* BPP Menu Cam;                                               // 0x0458 (size: 0x8)
    TMap<FString, int32> ComboBoxSelection;                                           // 0x0460 (size: 0x50)
    TMap<int32, UEditableTextBox*> buttons;                                           // 0x04B0 (size: 0x50)
    TMap<int32, UProgressBar*> AxisL;                                                 // 0x0500 (size: 0x50)
    TMap<int32, UProgressBar*> AxisR;                                                 // 0x0550 (size: 0x50)
    bool MoveMouseCursor;                                                             // 0x05A0 (size: 0x1)
    double wheelPosition;                                                             // 0x05A8 (size: 0x8)
    FWBP_ControlMenu_CLoadedData LoadedData;                                          // 0x05B0 (size: 0x10)
    void LoadedData();
    FString ProfileText;                                                              // 0x05C0 (size: 0x10)
    FString InputKeyList;                                                             // 0x05D0 (size: 0x10)
    FString deviceName;                                                               // 0x05E0 (size: 0x10)
    FEditableTextBoxStyle ButtonAxisActiveColor;                                      // 0x05F0 (size: 0xC80)
    FEditableTextBoxStyle ButtonAxisDeactiveColor;                                    // 0x1270 (size: 0xC80)
    FString CustomProfileName;                                                        // 0x1EF0 (size: 0x10)
    TEnumAsByte<E_CalibrationPhases::Type> ECalibrationPhase;                         // 0x1F00 (size: 0x1)
    double Counter;                                                                   // 0x1F08 (size: 0x8)
    bool isCountingCalibration;                                                       // 0x1F10 (size: 0x1)
    FString ActionName;                                                               // 0x1F18 (size: 0x10)
    FString LastActionName;                                                           // 0x1F28 (size: 0x10)
    class UDataTable* DT Calibration;                                                 // 0x1F38 (size: 0x8)

    void GetSelectedDevice(FSimpleControllerDevice& device, bool& found);
    void MoveAxis(class UProgressBar* AxisL, class UProgressBar* AxisR, double Value);
    void AddControllerToComboBox(FSimpleControllerDevice device);
    void fLoad Controller(FString SlotName);
    void fSave Controller(FString SlotName);
    void onAction_AF166120485BF22031DF02986A7DD5C0(const float AxisValue);
    void failed_C7D18E6A4DFB828EA999F885FDF2C56D();
    void successful_C7D18E6A4DFB828EA999F885FDF2C56D();
    void failed_5E103DFA46040F1A1CF277885B39F498();
    void successful_5E103DFA46040F1A1CF277885B39F498();
    void failed_5675D173453D8263B7ECEBA9ADFFCA8B();
    void successful_5675D173453D8263B7ECEBA9ADFFCA8B();
    void onAction_DCD1AE7341723F707CEFE3AA0256B9C1(const float AxisValue);
    void timer_6BF1F7CD4D8456E985A1FEA97FD45756(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    void timeOut_6BF1F7CD4D8456E985A1FEA97FD45756(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    void isMapped_6BF1F7CD4D8456E985A1FEA97FD45756(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    void error_6BF1F7CD4D8456E985A1FEA97FD45756(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    void successful_6BF1F7CD4D8456E985A1FEA97FD45756(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    void onAction_857356D94B4EBF0639BC49BF1E41A6CF(const int32 axisID, const float AxisValue, const int32 connectionIndex, const FSimpleControllerDevice device);
    void timer_C9D397EF411A20825530959E8D11A453(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    void timeOut_C9D397EF411A20825530959E8D11A453(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    void isMapped_C9D397EF411A20825530959E8D11A453(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    void error_C9D397EF411A20825530959E8D11A453(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    void successful_C9D397EF411A20825530959E8D11A453(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    void actionReleased_013A6CD942AF4E1F6738149A58A3B709();
    void actionPressed_013A6CD942AF4E1F6738149A58A3B709();
    void OnInitialized();
    void Construct();
    void ShowLoader(double HideAfter);
    void BindAttach();
    void BindDetach();
    void BindButtonDown();
    void BindButtonUp();
    void BindAxis();
    void ondeviceAttachedEventDelegate_Event_0(FSimpleControllerDevice device, int32 connectionIndex);
    void ondeviceDetachedEventDelegate_Event_0(FSimpleControllerDevice device, int32 connectionIndex);
    void onButtonDownEventDelegate_Event_0(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void onButtonUpEventDelegate_Event_0(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void LoadMappingProfile();
    void ResetProfile();
    void SaveProfile();
    void LoadAllMappings();
    void UpdateCalibrationInfoText(FText Information, FText Calibrate Button);
    void ProgressBar();
    void StartTimer();
    void Tick(FGeometry MyGeometry, float InDeltaTime);
    void ShowAssignInfo(bool isAssigned);
    void RestartCalibration(bool bInIsEnabledSkip);
    void BndEvt__WBP_ControlMenu_CheckBox_Reverse_K2Node_ComponentBoundEvent_1_OnCheckBoxComponentStateChanged__DelegateSignature(bool bIsChecked);
    void BndEvt__WBP_ControlMenu_CheckBox_Reverse_1_K2Node_ComponentBoundEvent_3_OnCheckBoxComponentStateChanged__DelegateSignature(bool bIsChecked);
    void BndEvt__WBP_ControlMenu_CheckBox_Reverse_2_K2Node_ComponentBoundEvent_4_OnCheckBoxComponentStateChanged__DelegateSignature(bool bIsChecked);
    void InitializeCheckbox();
    void BndEvt__WBP_ControlMenu_CheckBox_Reverse_3_K2Node_ComponentBoundEvent_5_OnCheckBoxComponentStateChanged__DelegateSignature(bool bIsChecked);
    void BndEvt__WBP_ControlMenu_ContinueBtn_1_K2Node_ComponentBoundEvent_10_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_ControlMenu_Btn_Calibration_K2Node_ComponentBoundEvent_12_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_ControlMenu_Btn_Skip_K2Node_ComponentBoundEvent_14_ButtonClicked__DelegateSignature(int32 SelfIndex);
    void BndEvt__WBP_ControlMenu_WBP_EGUI_CommonHeader_K2Node_ComponentBoundEvent_0_NewTabSelected__DelegateSignature(int32 TabIndex, FText TabName, FString TabCultureInvariantName);
    void ConfirmControls();
    void ExecuteUbergraph_WBP_ControlMenu(int32 EntryPoint);
    void LoadedData__DelegateSignature();
}; // Size: 0x1F40

#endif
