#ifndef UE4SS_SDK_SimpleController_HPP
#define UE4SS_SDK_SimpleController_HPP

#include "SimpleController_enums.hpp"

struct FControllerWebserver
{
}; // Size: 0x70

struct FSimpleControllerDevice
{
}; // Size: 0x340

struct FSimpleControllerForceFeedbackEffect
{
}; // Size: 0x18

struct FSimpleControllerMappingAxisAction
{
    FString Description;                                                              // 0x0010 (size: 0x10)
    FString Tag;                                                                      // 0x0020 (size: 0x10)
    bool InvertAxis;                                                                  // 0x0030 (size: 0x1)
    bool bStructID;                                                                   // 0x0031 (size: 0x1)

}; // Size: 0x90

struct FSimpleControllerMappingButtonAction
{
    FString Description;                                                              // 0x0010 (size: 0x10)
    FString Tag;                                                                      // 0x0020 (size: 0x10)
    bool bStructID;                                                                   // 0x0030 (size: 0x1)

}; // Size: 0xA0

struct FSimpleControllerMappingProfile
{
    FGuid structID;                                                                   // 0x0000 (size: 0x10)
    TMap<class FString, class FSimpleControllerMappingButtonAction> buttonActions;    // 0x0010 (size: 0x50)
    TMap<class FString, class FSimpleControllerMappingAxisAction> axisActions;        // 0x0060 (size: 0x50)

}; // Size: 0x150

class UAutocenterAsyncEvent : public UBlueprintAsyncActionBase
{
    FAutocenterAsyncEventFinished Finished;                                           // 0x0390 (size: 0x10)
    void AutocenterEvent();

    class UAutocenterAsyncEvent* autocenterWheel(FSimpleControllerDevice device, bool stopWhenCentered, float defaultStrength, float slowdownStrength, float desiredEndPosition, float Tolerance, bool showLogs, int32 wheelAxisID);
    void AutocenterEvent__DelegateSignature();
}; // Size: 0x3A0

class USimpleControllerAxisAsyncEvent : public UBlueprintAsyncActionBase
{
    FSimpleControllerAxisAsyncEventOnAction onAction;                                 // 0x0040 (size: 0x10)
    void ControllerAxisEvent(const int32 axisID, const float AxisValue, const int32 connectionIndex, const FSimpleControllerDevice device);

    void ControllerAxisEvent__DelegateSignature(const int32 axisID, const float AxisValue, const int32 connectionIndex, const FSimpleControllerDevice device);
    class USimpleControllerAxisAsyncEvent* controllerAxisAsyncEvent(ESimpleControllerEventType triggerEventIf);
}; // Size: 0x50

class USimpleControllerBPLibrary : public UBlueprintFunctionLibrary
{
    FSimpleControllerBPLibraryOnButtonDownEventDelegate onButtonDownEventDelegate;    // 0x0030 (size: 0x10)
    void buttonDownEventDelegate(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOnButtonUpEventDelegate onButtonUpEventDelegate;        // 0x0040 (size: 0x10)
    void buttonUpEventDelegate(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOnDirectionalPadEventDelegate onDirectionalPadEventDelegate; // 0x0050 (size: 0x10)
    void directionalPadEventDelegate(FString DeviceID, int32 directionalPadValue, int32 directionalPadIndex, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOnBallMovedEventDelegate onBallMovedEventDelegate;      // 0x0060 (size: 0x10)
    void ballMovedEventDelegate(FString DeviceID, int32 ballID, float xRel, int32 yRel, FSimpleControllerDevice device);
    FSimpleControllerBPLibraryOnaxisMovedEventDelegate onaxisMovedEventDelegate;      // 0x0070 (size: 0x10)
    void axisMovedEventDelegate(FString DeviceID, int32 axisID, float AxisValue, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOndeviceAttachedEventDelegate ondeviceAttachedEventDelegate; // 0x0080 (size: 0x10)
    void deviceAttachedEventDelegate(FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOndeviceDetachedEventDelegate ondeviceDetachedEventDelegate; // 0x0090 (size: 0x10)
    void deviceDetachedEventDelegate(FSimpleControllerDevice device, int32 connectionIndex);
    FSimpleControllerBPLibraryOnaccelerationSensorEventDelegate onaccelerationSensorEventDelegate; // 0x00A0 (size: 0x10)
    void accelerationSensorEventDelegate(FString DeviceID, float valueA, float valueB, float valueC, int32 deviceIndex, FSimpleControllerDevice device);
    FSimpleControllerBPLibraryOngyroSensorEventDelegate ongyroSensorEventDelegate;    // 0x00B0 (size: 0x10)
    void gyroSensorEventDelegate(FString DeviceID, float valueA, float valueB, float valueC, int32 deviceIndex, FSimpleControllerDevice device);
    FSimpleControllerBPLibraryOntouchpadMotionEventDelegate ontouchpadMotionEventDelegate; // 0x00C0 (size: 0x10)
    void touchpadMotionEventDelegate(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    FSimpleControllerBPLibraryOntouchpadDownEventDelegate ontouchpadDownEventDelegate; // 0x00D0 (size: 0x10)
    void touchpadDownEventDelegate(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    FSimpleControllerBPLibraryOntouchpadUpEventDelegate ontouchpadUpEventDelegate;    // 0x00E0 (size: 0x10)
    void touchpadUpEventDelegate(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    class USimpleControllerWheel* SimpleControllerWheel;                              // 0x0108 (size: 0x8)

    FSimpleControllerForceFeedbackEffect uploadForceFeedbackEffect(bool& successful, FString& errorMessage, FSimpleControllerForceFeedbackEffect ForceFeedbackEffect);
    FSimpleControllerForceFeedbackEffect uploadAndRunForceFeedbackEffect(bool& successful, FString& errorMessage, FSimpleControllerForceFeedbackEffect ForceFeedbackEffect, int32 iterations);
    void updateConstantForceFeedbackEffect(bool& successful, FString& errorMessage, FSimpleControllerForceFeedbackEffect ForceFeedbackEffect, int32 directionX, int32 directionY, int32 directionZ, int32 Length, int32 Delay, float Level, int32 attackLength, float attackLevel, int32 fadeLength, float fadeLevel);
    void touchpadUpEventDelegate__DelegateSignature(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    void touchpadUpEventDelegate(const FString DeviceID, const int32 touchpadIndex, const int32 finger, const float X, const float Y, const float Pressure, const int32 deviceIndex, const FSimpleControllerDevice device);
    void touchpadMotionEventDelegate__DelegateSignature(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    void touchpadMotionEventDelegate(const FString DeviceID, const int32 touchpadIndex, const int32 finger, const float X, const float Y, const float Pressure, const int32 deviceIndex, const FSimpleControllerDevice device);
    void touchpadDownEventDelegate__DelegateSignature(FString DeviceID, int32 touchpadIndex, int32 finger, float X, float Y, float Pressure, int32 deviceIndex, FSimpleControllerDevice device);
    void touchpadDownEventDelegate(const FString DeviceID, const int32 touchpadIndex, const int32 finger, const float X, const float Y, const float Pressure, const int32 deviceIndex, const FSimpleControllerDevice device);
    void stopRumbleWheel();
    FSimpleControllerForceFeedbackEffect stopForceFeedbackEffect(bool& successful, FString& errorMessage, FSimpleControllerForceFeedbackEffect ForceFeedbackEffect);
    void setUnrealKeyboardAndMouseEvents(class UObject* WorldContextObject, bool keyboardButtons, bool mousedButtons);
    void setSensor(FSimpleControllerDevice device, ESimpleControllerSensorType Type, bool Enable);
    void SetMousePosition(int32 X, int32 Y);
    void setLEDColor(bool& successful, FString& errorMessage, FSimpleControllerDevice device, FColor Color);
    void setGainForceFeedback(FSimpleControllerDevice device, int32 gain);
    FSimpleControllerDevice setDeadZone(FSimpleControllerDevice device, int32 axisID, float deadZoneMaxPositive, float deadZoneMaxNegative, float deadZoneMinPositive, float deadZoneMinNegative);
    void setAutocenterForceFeedbackSDL(FSimpleControllerDevice device, int32 autocenter);
    void setAsyncNodesReadyToDestroy(bool StatusEvents, bool ButtonEvents, bool AxisEvents, bool GamepadSticksEvents, bool GamepadTriggerEvents, bool GamepadFaceButtonsEvents, bool GamepadControlEvents, bool GamepadStickButtonsEvents, bool GamepadShoulderButtonsEvents, bool GamepadDpadEvents, bool GamepadSpecialButtonsEvents);
    FSimpleControllerForceFeedbackEffect runForceFeedbackEffect(bool& successful, FString& errorMessage, FSimpleControllerForceFeedbackEffect ForceFeedbackEffect, int32 iterations);
    void rumbleWheel(bool& successful, FString& errorMessage, FSimpleControllerDevice device, float strengthLeftMotor, float strengthRightMotor, int32 lengthInMilliseconds, int32 timeBetweenDirectionChangeInMilliseconds);
    void rumbleTrigger(bool& successful, FString& errorMessage, FSimpleControllerDevice device, float strengthLeft, float strengthRight, int32 lengthInMilliseconds);
    void rumbleByConnectionIndex(bool& successful, FString& errorMessage, int32 connectionIndex, float strengthSmallMotor, float strengthLargeMotor, int32 lengthInMilliseconds);
    void rumble(bool& successful, FString& errorMessage, FSimpleControllerDevice device, float strengthSmallMotor, float strengthLargeMotor, int32 lengthInMilliseconds);
    void removeButtonMapping(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void RemoveAxisMapping(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void removeAxisCorrection(FSimpleControllerDevice device, int32 axisID, ESimpleControllerAxisCorrection Type);
    bool mapButton(FSimpleControllerMappingProfile mappingProfile, FString ActionName, FSimpleControllerDevice device, int32 buttonID);
    bool mapAxis(FSimpleControllerMappingProfile mappingProfile, FString ActionName, FSimpleControllerDevice device, int32 axisID);
    bool isXinputCompatible(int32 connectionIndex);
    bool isButtonMapped(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    bool isAxisMapped(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void initIOSPart(class UObject* WorldContextObject);
    void gyroSensorEventDelegate__DelegateSignature(FString DeviceID, float valueA, float valueB, float valueC, int32 deviceIndex, FSimpleControllerDevice device);
    void gyroSensorEventDelegate(const FString DeviceID, const float valueA, const float valueB, const float valueC, const int32 deviceIndex, const FSimpleControllerDevice device);
    void getSystemType(ESimpleControllerSystemType& System, bool& dedicatedServer);
    class USimpleControllerBPLibrary* getSimpleControllerTarget();
    void GetMousePosition(int32& X, int32& Y);
    void getMappingActionsByTag(FSimpleControllerMappingProfile mappingProfile, FString Tag, TArray<FSimpleControllerMappingButtonAction>& buttonActions, TArray<FSimpleControllerMappingAxisAction>& axisActions);
    void getMappedButtonActions(bool& isMapped, TArray<FString>& actionNames, int32 buttonID, int32 connectionIndex);
    void getMappedAxisActions(bool& isMapped, TArray<FString>& actionNames, int32 axisID, int32 connectionIndex);
    int32 getHatValueBySDL(FSimpleControllerDevice device, int32 directionalPadIndex);
    void getCurrentPowerLevel(FSimpleControllerDevice device, ESimpleControllerPowerLevel& powerLevel);
    TArray<FSimpleControllerDevice> getConnectedControllers();
    ESimpleControllerButtonStatus getButtonValueBySDL(FSimpleControllerDevice device, int32 buttonID);
    FString getButtonName(FSimpleControllerDevice device, int32 buttonID);
    void getButtonActions(FSimpleControllerMappingProfile profile, TMap<class FString, class FSimpleControllerMappingButtonAction>& buttonActions);
    void getBallValueBySDL(FSimpleControllerDevice device, int32 ballIndex, int32& xRel, int32& yRel);
    void getAxisValues(FSimpleControllerDevice device, TMap<int32, float>& axisValues);
    float getAxisValueBySDL(FSimpleControllerDevice device, int32 axisID);
    void getAxisActions(FSimpleControllerMappingProfile profile, TMap<class FString, class FSimpleControllerMappingAxisAction>& axisActions);
    TArray<uint8> generateDualSenseTriggerCommandWeapon(SCDualSenseTriggerEffectStartPosition startPosition, SCDualSenseTriggerEffectEndPosition endPosition, SCDualSenseTriggerEffectStrength Strength, bool Left, bool Right);
    TArray<uint8> generateDualSenseTriggerCommandVibration(SCDualSenseTriggerEffectStartZone startingZone, SCDualSenseTriggerEffectStrength Strength, uint8 frequency, bool Left, bool Right);
    TArray<uint8> generateDualSenseTriggerCommandOFF(bool Left, bool Right);
    TArray<uint8> generateDualSenseTriggerCommandMultiVibration(uint8 frequency, SCDualSenseTriggerEffectStrengthMulti Strength_0, SCDualSenseTriggerEffectStrengthMulti Strength_1, SCDualSenseTriggerEffectStrengthMulti Strength_2, SCDualSenseTriggerEffectStrengthMulti Strength_3, SCDualSenseTriggerEffectStrengthMulti Strength_4, SCDualSenseTriggerEffectStrengthMulti Strength_5, SCDualSenseTriggerEffectStrengthMulti Strength_6, SCDualSenseTriggerEffectStrengthMulti Strength_7, SCDualSenseTriggerEffectStrengthMulti Strength_8, SCDualSenseTriggerEffectStrengthMulti Strength_9, bool Left, bool Right);
    TArray<uint8> generateDualSenseTriggerCommandMultiFeedback(SCDualSenseTriggerEffectStrengthMulti Strength_0, SCDualSenseTriggerEffectStrengthMulti Strength_1, SCDualSenseTriggerEffectStrengthMulti Strength_2, SCDualSenseTriggerEffectStrengthMulti Strength_3, SCDualSenseTriggerEffectStrengthMulti Strength_4, SCDualSenseTriggerEffectStrengthMulti Strength_5, SCDualSenseTriggerEffectStrengthMulti Strength_6, SCDualSenseTriggerEffectStrengthMulti Strength_7, SCDualSenseTriggerEffectStrengthMulti Strength_8, SCDualSenseTriggerEffectStrengthMulti Strength_9, bool Left, bool Right);
    TArray<uint8> generateDualSenseTriggerCommandFeedback(SCDualSenseTriggerEffectStartZone startingZone, SCDualSenseTriggerEffectStrength Strength, bool Left, bool Right);
    void fireMouseButtonEvent(ESimpleControllerMouseTriggerButton Button, ESimpleControllerMouseTriggerType Type);
    void fireKeyboardButtonEvent(int32 keycode, ESimpleControllerKeyboardTriggerType Type, int32 UserIndex);
    void findDeviceIndexByConnectionIndex(int32 connectionIndex, bool& found, int32& deviceIndex);
    FSimpleControllerDevice findControllerByDeviceIndex(int32 deviceIndex, bool& found);
    FSimpleControllerDevice findControllerByDeviceID(FString DeviceID, bool& found);
    FSimpleControllerDevice findControllerByConnectionIndex(int32 connectionIndex, bool& found);
    void executeCommandOnController(bool& successful, FString& errorMessage, FSimpleControllerDevice device, TArray<uint8> bytes);
    void enableForceFeedbackOnDevice(FSimpleControllerDevice device);
    bool enableConstantForceOnWheel(FSimpleControllerDevice device, int32 Force, int32 wheelAxisID);
    void disableUIVirtualKeys();
    void disableForceFeedbackOnDevice(FSimpleControllerDevice device);
    void disableConstantForceOnWheel(FSimpleControllerDevice device);
    void directionalPadEventDelegate__DelegateSignature(FString DeviceID, int32 directionalPadValue, int32 directionalPadIndex, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void directionalPadEventDelegate(const FString DeviceID, const int32 directionalPadValue, int32 directionalPadIndex, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void directinalPadValueToDirection(int32 directionalPadValue, ESimpleControllerDirectionalPad& Direction);
    void deviceDetachedEventDelegate__DelegateSignature(FSimpleControllerDevice device, int32 connectionIndex);
    void deviceDetachedEventDelegate(const FSimpleControllerDevice device, const int32 connectionIndex);
    void deviceAttachedEventDelegate__DelegateSignature(FSimpleControllerDevice device, int32 connectionIndex);
    void deviceAttachedEventDelegate(const FSimpleControllerDevice device, const int32 connectionIndex);
    void destroyForceFeedbackEffect(FSimpleControllerForceFeedbackEffect ForceFeedbackEffect);
    bool deleteMappingFile(FString ProfileName);
    bool createMappingFile(FString ProfileName, FString fileData, bool overwriteExistingFile);
    void createForceFeedbackEffectRamp(FSimpleControllerForceFeedbackEffect& ForceFeedbackEffect, bool& successful, FString& errorMessage, FSimpleControllerDevice device, ESimpleControllerForceFeedbackDirectionType directionType, int32 directionX, int32 directionY, int32 directionZ, int32 Length, int32 Delay, float startLevel, float endLevel, int32 attackLength, float attackLevel, int32 fadeLength, float fadeLevel);
    void createForceFeedbackEffectPeriodic(FSimpleControllerForceFeedbackEffect& ForceFeedbackEffect, bool& successful, FString& errorMessage, FSimpleControllerDevice device, ESimpleControllerForceFeedbackEffectPeriodicType PeriodicType, ESimpleControllerForceFeedbackDirectionType directionType, int32 directionX, int32 directionY, int32 directionZ, int32 Length, int32 Delay, int32 Period, float Magnitude, float Offset, int32 phase, int32 attackLength, float attackLevel, int32 fadeLength, float fadeLevel);
    void createForceFeedbackEffectConstant(FSimpleControllerForceFeedbackEffect& ForceFeedbackEffect, bool& successful, FString& errorMessage, FSimpleControllerDevice device, ESimpleControllerForceFeedbackDirectionType directionType, int32 directionX, int32 directionY, int32 directionZ, int32 Length, int32 Delay, float Level, int32 attackLength, float attackLevel, int32 fadeLength, float fadeLevel);
    void createForceFeedbackEffectCondition(FSimpleControllerForceFeedbackEffect& ForceFeedbackEffect, bool& successful, FString& errorMessage, FSimpleControllerDevice device, ESimpleControllerForceFeedbackDirectionType directionType, ESimpleControllerForceFeedbackEffectConditionType ConditionType, bool useDirectionX, bool useDirectionY, bool useDirectionZ, int32 Length, int32 Delay, float rightLevel, float leftLevel, float rightCoefficient, float leftCoefficient, float deadband, float Center);
    void changeForceFeedbackWheelDirectionType(FSimpleControllerDevice device, bool movedByForce);
    void changeAxisActionSettings(FSimpleControllerMappingProfile mappingProfile, FString ActionName, bool InvertAxis);
    void cancelMapping();
    void buttonUpEventDelegate__DelegateSignature(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void buttonUpEventDelegate(const FString DeviceID, const int32 buttonID, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void buttonIDToButton(int32 buttonID, ESimpleControllerButtons& buttons);
    void buttonDownEventDelegate__DelegateSignature(FString DeviceID, int32 buttonID, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void buttonDownEventDelegate(const FString DeviceID, const int32 buttonID, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void breakMappingProfile(FSimpleControllerMappingProfile profile, TMap<class FString, class FSimpleControllerMappingButtonAction>& buttonActions, TMap<class FString, class FSimpleControllerMappingAxisAction>& axisActions);
    void breakForceFeedbackEffect(FSimpleControllerForceFeedbackEffect ForceFeedbackEffect, int32& effectID, bool& successful);
    void breakDeviceInfo(FSimpleControllerDevice device, int32& deviceIndex, int32& connectionIndex, FString& DeviceID, FString& deviceName, FString& controllerName, int32& vendorID, int32& productID, int32& numAxes, int32& numButtons, int32& numDirectionalPadAxes, int32& numBalls, bool& hasHaptic, bool& hasRumble, bool& hasRumbleTriggers, bool& hasAccelerationSensor, bool& hasGyroSensor, bool& hasLED, bool& gamepadAPI_Support, bool& isXinputCompatible, ESimpleControllerType& Type, bool& wheelMovedByForce);
    void breakDeviceForceFeedbackInfo(FSimpleControllerDevice device, bool& forceFeedback_CONSTANT, bool& forceFeedback_SINE, bool& forceFeedback_LEFTRIGHT, bool& forceFeedback_TRIANGLE, bool& forceFeedback_SAWTOOTHUP, bool& forceFeedback_SAWTOOTHDOWN, bool& forceFeedback_RAMP, bool& forceFeedback_SPRING, bool& forceFeedback_DAMPER, bool& forceFeedback_INERTIA, bool& forceFeedback_FRICTION, bool& forceFeedback_CUSTOM, bool& forceFeedback_GAIN, bool& forceFeedback_AUTOCENTER, bool& forceFeedback_STATUS, bool& forceFeedback_PAUSE, bool& forceFeedback_POLAR, bool& forceFeedback_CARTESIAN, bool& forceFeedback_SPHERICAL, bool& forceFeedback_INFINITY, int32& maxSimultaneouslyEffects);
    void breakButtonAction(FSimpleControllerMappingButtonAction action, FString& ActionName, FString& Description, FString& Tag, int32& connectionIndex, int32& buttonID, FString& buttonName, FString& deviceName, FString& controllerName, int32& vendorID, int32& productID);
    void breakAxisAction(FSimpleControllerMappingAxisAction action, FString& ActionName, FString& Description, FString& Tag, int32& connectionIndex, int32& axisID, bool& InvertAxis, FString& deviceName, FString& controllerName, int32& vendorID, int32& productID);
    void ballMovedEventDelegate__DelegateSignature(FString DeviceID, int32 ballID, float xRel, int32 yRel, FSimpleControllerDevice device);
    void ballMovedEventDelegate(const FString DeviceID, const int32 ballID, const int32 xRel, const int32 yRel, const FSimpleControllerDevice device);
    void axisMovedEventDelegate__DelegateSignature(FString DeviceID, int32 axisID, float AxisValue, int32 deviceIndex, FSimpleControllerDevice device, int32 connectionIndex);
    void axisMovedEventDelegate(const FString DeviceID, const int32 axisID, const float AxisValue, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void addMousePosition(int32 X, int32 Y);
    void addAxisCorrection(FSimpleControllerDevice device, int32 axisID, ESimpleControllerAxisCorrection Type);
    void accelerationSensorEventDelegate__DelegateSignature(FString DeviceID, float valueA, float valueB, float valueC, int32 deviceIndex, FSimpleControllerDevice device);
    void accelerationSensorEventDelegate(const FString DeviceID, const float valueA, const float valueB, const float valueC, const int32 deviceIndex, const FSimpleControllerDevice device);
}; // Size: 0x698

class USimpleControllerButtonAsyncEvent : public UBlueprintAsyncActionBase
{
    FSimpleControllerButtonAsyncEventButtonDown buttonDown;                           // 0x0030 (size: 0x10)
    void ControllerButtonEvent(const int32 buttonID, const int32 connectionIndex, const FSimpleControllerDevice device);
    FSimpleControllerButtonAsyncEventButtonUp buttonUp;                               // 0x0040 (size: 0x10)
    void ControllerButtonEvent(const int32 buttonID, const int32 connectionIndex, const FSimpleControllerDevice device);

    void ControllerButtonEvent__DelegateSignature(const int32 buttonID, const int32 connectionIndex, const FSimpleControllerDevice device);
    class USimpleControllerButtonAsyncEvent* controllerButtonAsyncEvent();
}; // Size: 0x50

class USimpleControllerGamepadControlButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadControlButtonEventsBackPressed backPressed;               // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadControlButtonEventsBackReleased backReleased;             // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadControlButtonEventsStartPressed startPressed;             // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadControlButtonEventsStartReleased startReleased;           // 0x0068 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadControlButtonEventsGuidePressed guidePressed;             // 0x0078 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadControlButtonEventsGuideReleased guideReleased;           // 0x0088 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadControlButtonEvents* gamepadEventControlButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0x98

class USimpleControllerGamepadDpadButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadDpadButtonEventsBottomDpadPressed bottomDpadPressed;      // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsBottomDpadReleased bottomDpadReleased;    // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsTopDpadPressed topDpadPressed;            // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsTopDpadReleased topDpadReleased;          // 0x0068 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsRightDpadPressed rightDpadPressed;        // 0x0078 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsRightDpadReleased rightDpadReleased;      // 0x0088 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsLeftDpadPressed leftDpadPressed;          // 0x0098 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadDpadButtonEventsLeftDpadReleased leftDpadReleased;        // 0x00A8 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadDpadButtonEvents* gamepadEventDpadButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0xB8

class USimpleControllerGamepadFaceButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadFaceButtonEventsBottomPressed bottomPressed;              // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsBottomReleased bottomReleased;            // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsTopPressed topPressed;                    // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsTopReleased topReleased;                  // 0x0068 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsRightPressed rightPressed;                // 0x0078 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsRightReleased rightReleased;              // 0x0088 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsLeftPressed leftPressed;                  // 0x0098 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadFaceButtonEventsLeftReleased leftReleased;                // 0x00A8 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadFaceButtonEvents* gamepadEventFaceButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0xB8

class USimpleControllerGamepadShoulderButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadShoulderButtonEventsLeftShoulderPressed leftShoulderPressed; // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadShoulderButtonEventsLeftShoulderReleased leftShoulderReleased; // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadShoulderButtonEventsRightShoulderPressed rightShoulderPressed; // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadShoulderButtonEventsRightShoulderReleased rightShoulderReleased; // 0x0068 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadShoulderButtonEvents* gamepadEventShoulderButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0x78

class USimpleControllerGamepadSpecialButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadSpecialButtonEventsMisc1Pressed Misc1Pressed;             // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsMisc1Released Misc1Released;           // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP1Pressed XboxElitePaddleP1Pressed; // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP1Released XboxElitePaddleP1Released; // 0x0068 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP2Pressed XboxElitePaddleP2Pressed; // 0x0078 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP2Released XboxElitePaddleP2Released; // 0x0088 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP3Pressed XboxElitePaddleP3Pressed; // 0x0098 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP3Released XboxElitePaddleP3Released; // 0x00A8 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP4Pressed XboxElitePaddleP4Pressed; // 0x00B8 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP4Released XboxElitePaddleP4Released; // 0x00C8 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsPSTouchpadPressed PSTouchpadPressed;   // 0x00D8 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadSpecialButtonEventsPSTouchpadReleased PSTouchpadReleased; // 0x00E8 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadSpecialButtonEvents* gamepadEventSpecialButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0xF8

class USimpleControllerGamepadStickAxisEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadStickAxisEventsLeftStickX leftStickX;                     // 0x0048 (size: 0x10)
    void ControllerAxisEvent(const float AxisValue);
    FSimpleControllerGamepadStickAxisEventsLeftStickY leftStickY;                     // 0x0058 (size: 0x10)
    void ControllerAxisEvent(const float AxisValue);
    FSimpleControllerGamepadStickAxisEventsRightStickX rightStickX;                   // 0x0068 (size: 0x10)
    void ControllerAxisEvent(const float AxisValue);
    FSimpleControllerGamepadStickAxisEventsRightStickY rightStickY;                   // 0x0078 (size: 0x10)
    void ControllerAxisEvent(const float AxisValue);

    class USimpleControllerGamepadStickAxisEvents* gamepadEventStickAxis(ESimpleControllerEventType triggerEventIf, int32 connectionIndex);
    void ControllerAxisEvent__DelegateSignature(const float AxisValue);
}; // Size: 0x88

class USimpleControllerGamepadStickButtonEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadStickButtonEventsLeftStickPressed leftStickPressed;       // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadStickButtonEventsLeftStickReleased leftStickReleased;     // 0x0048 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadStickButtonEventsRightStickPressed rightStickPressed;     // 0x0058 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerGamepadStickButtonEventsRightStickReleased rightStickReleased;   // 0x0068 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerGamepadStickButtonEvents* gamepadEventStickButtons(int32 connectionIndex);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0x78

class USimpleControllerGamepadTriggerAxisEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerGamepadTriggerAxisEventsLeftTrigger leftTrigger;                 // 0x0040 (size: 0x10)
    void ControllerAxisEvent(float AxisValue);
    FSimpleControllerGamepadTriggerAxisEventsRightTrigger rightTrigger;               // 0x0050 (size: 0x10)
    void ControllerAxisEvent(float AxisValue);

    class USimpleControllerGamepadTriggerAxisEvents* gamepadEventTriggerAxis(ESimpleControllerEventType triggerEventIf, int32 connectionIndex);
    void ControllerAxisEvent__DelegateSignature(float AxisValue);
}; // Size: 0x60

class USimpleControllerMappedButtonAsyncEvent : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappedButtonAsyncEventActionPressed actionPressed;               // 0x0038 (size: 0x10)
    void ControllerButtonEvent();
    FSimpleControllerMappedButtonAsyncEventActionReleased actionReleased;             // 0x0048 (size: 0x10)
    void ControllerButtonEvent();

    class USimpleControllerMappedButtonAsyncEvent* controllerEventMappedButton(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void ControllerButtonEvent__DelegateSignature();
}; // Size: 0x58

class USimpleControllerMappingAxis : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingAxisSuccessful successful;                                // 0x0398 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    FSimpleControllerMappingAxisError Error;                                          // 0x03A8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    FSimpleControllerMappingAxisIsMapped isMapped;                                    // 0x03B8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    FSimpleControllerMappingAxisTimeout Timeout;                                      // 0x03C8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
    FSimpleControllerMappingAxisTimer Timer;                                          // 0x03D8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);

    class USimpleControllerMappingAxis* startMappingAxis(FSimpleControllerMappingProfile mappingProfile, FString ActionName, int32 timeInSeconds, float minAxisValueToReact, bool allowMultipleMapping);
    void ControllerMappingEvent__DelegateSignature(const FSimpleControllerMappingAxisAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedAxisID, const int32 usedConnectionIndex);
}; // Size: 0x3E8

class USimpleControllerMappingAxisEvents : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingAxisEventsOnAction onAction;                              // 0x0038 (size: 0x10)
    void ControllerAxisEvent(const float AxisValue);

    class USimpleControllerMappingAxisEvents* controllerEventMappedAxis(ESimpleControllerEventType triggerEventIf, FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void ControllerAxisEvent__DelegateSignature(const float AxisValue);
}; // Size: 0x48

class USimpleControllerMappingButton : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingButtonSuccessful successful;                              // 0x03C8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    FSimpleControllerMappingButtonError Error;                                        // 0x03D8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    FSimpleControllerMappingButtonIsMapped isMapped;                                  // 0x03E8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    FSimpleControllerMappingButtonTimeout Timeout;                                    // 0x03F8 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
    FSimpleControllerMappingButtonTimer Timer;                                        // 0x0408 (size: 0x10)
    void ControllerMappingEvent(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);

    class USimpleControllerMappingButton* startMappingButton(class UObject* WorldContextObject, FSimpleControllerMappingProfile mappingProfile, FString ActionName, TArray<int32> whiteList, TArray<int32> blacklist, int32 timeInSeconds, bool allowMultipleMapping, bool keyboardButtons, bool mousedButtons, ESimpleControllerMapButtonReactType reactType);
    void ControllerMappingEvent__DelegateSignature(const FSimpleControllerMappingButtonAction action, const int32 Seconds, const FSimpleControllerDevice usedDevice, const int32 usedButtonID, const int32 usedConnectionIndex);
}; // Size: 0x418

class USimpleControllerMappingCalibrateAxis : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingCalibrateAxisFinishedMax finishedMax;                     // 0x0390 (size: 0x10)
    void ControllerCalibrateEvent(const float AxisValue, const int32 Seconds);
    FSimpleControllerMappingCalibrateAxisFinishedMin finishedMin;                     // 0x03A0 (size: 0x10)
    void ControllerCalibrateEvent(const float AxisValue, const int32 Seconds);
    FSimpleControllerMappingCalibrateAxisError Error;                                 // 0x03B0 (size: 0x10)
    void ControllerCalibrateEvent(const float AxisValue, const int32 Seconds);
    FSimpleControllerMappingCalibrateAxisTimer Timer;                                 // 0x03C0 (size: 0x10)
    void ControllerCalibrateEvent(const float AxisValue, const int32 Seconds);
    FSimpleControllerMappingCalibrateAxisAxisValueChange axisValueChange;             // 0x03D0 (size: 0x10)
    void ControllerCalibrateEvent(const float AxisValue, const int32 Seconds);

    void removeCalibrationFromMappedAxis(FSimpleControllerMappingProfile mappingProfile, FString ActionName);
    void ControllerCalibrateEvent__DelegateSignature(const float AxisValue, const int32 Seconds);
    class USimpleControllerMappingCalibrateAxis* calibrateMappedAxis(FSimpleControllerMappingProfile mappingProfile, FString ActionName, int32 timeInSecondsPerStep);
}; // Size: 0x3E0

class USimpleControllerMappingLoad : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingLoadSuccessful successful;                                // 0x0060 (size: 0x10)
    void ControllerMappingEvent();
    FSimpleControllerMappingLoadFailed failed;                                        // 0x0070 (size: 0x10)
    void ControllerMappingEvent();

    class USimpleControllerMappingLoad* loadMappingFromFile(class UObject* WorldContextObject, FString ProfileName, FSimpleControllerMappingProfile mappingProfile, bool byDevice);
    void ControllerMappingEvent__DelegateSignature();
}; // Size: 0x80

class USimpleControllerMappingSave : public UBlueprintAsyncActionBase
{
    FSimpleControllerMappingSaveSuccessful successful;                                // 0x0050 (size: 0x10)
    void ControllerMappingEvent();
    FSimpleControllerMappingSaveFailed failed;                                        // 0x0060 (size: 0x10)
    void ControllerMappingEvent();

    class USimpleControllerMappingSave* saveMappingToFile(FString ProfileName, FSimpleControllerMappingProfile mappingProfile);
    void ControllerMappingEvent__DelegateSignature();
}; // Size: 0x70

class USimpleControllerMobile : public UObject
{
}; // Size: 0x1D0

class USimpleControllerPluginSettings : public UDeveloperSettings
{
    bool SDL_EVENTS_THREAD;                                                           // 0x0038 (size: 0x1)
    bool CREATE_PLAYER_CONTROLLER;                                                    // 0x0039 (size: 0x1)
    bool WHEEL_FF_TEST;                                                               // 0x003A (size: 0x1)
    bool XINPUT_ENABLED;                                                              // 0x003B (size: 0x1)
    bool DIRECTINPUT_ENABLED;                                                         // 0x003C (size: 0x1)
    bool JOYSTICK_HIDAPI;                                                             // 0x003D (size: 0x1)
    bool JOYSTICK_RAWINPUT;                                                           // 0x003E (size: 0x1)
    bool JOYSTICK_WGI;                                                                // 0x003F (size: 0x1)
    bool JOYSTICK_HIDAPI_GAMECUBE;                                                    // 0x0040 (size: 0x1)
    bool JOYSTICK_GAMECUBE_RUMBLE_BRAKE;                                              // 0x0041 (size: 0x1)
    bool JOYSTICK_HIDAPI_JOY_CONS;                                                    // 0x0042 (size: 0x1)
    bool JOYSTICK_HIDAPI_COMBINE_JOY_CONS;                                            // 0x0043 (size: 0x1)
    bool JOYSTICK_HIDAPI_VERTICAL_JOY_CONS;                                           // 0x0044 (size: 0x1)
    bool JOYSTICK_HIDAPI_LUNA;                                                        // 0x0045 (size: 0x1)
    bool JOYSTICK_HIDAPI_NINTENDO_CLASSIC;                                            // 0x0046 (size: 0x1)
    bool JOYSTICK_HIDAPI_SHIELD;                                                      // 0x0047 (size: 0x1)
    bool JOYSTICK_HIDAPI_PS3;                                                         // 0x0048 (size: 0x1)
    bool JOYSTICK_HIDAPI_PS4;                                                         // 0x0049 (size: 0x1)
    bool JOYSTICK_HIDAPI_PS4_PS5_RUMBLE;                                              // 0x004A (size: 0x1)
    bool JOYSTICK_HIDAPI_PS5;                                                         // 0x004B (size: 0x1)
    bool JOYSTICK_HIDAPI_PS5_PLAYER_LED;                                              // 0x004C (size: 0x1)
    bool JOYSTICK_HIDAPI_STADIA;                                                      // 0x004D (size: 0x1)
    bool JOYSTICK_HIDAPI_STEAM;                                                       // 0x004E (size: 0x1)
    bool JOYSTICK_HIDAPI_SWITCH;                                                      // 0x004F (size: 0x1)
    bool JOYSTICK_HIDAPI_SWITCH_HOME_LED;                                             // 0x0050 (size: 0x1)
    bool JOYSTICK_HIDAPI_JOYCON_HOME_LED;                                             // 0x0051 (size: 0x1)
    bool JOYSTICK_HIDAPI_SWITCH_PLAYER_LED;                                           // 0x0052 (size: 0x1)
    bool JOYSTICK_HIDAPI_WII;                                                         // 0x0053 (size: 0x1)
    bool JOYSTICK_HIDAPI_WII_PLAYER_LED;                                              // 0x0054 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX;                                                        // 0x0055 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX_360;                                                    // 0x0056 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX_360_PLAYER_LED;                                         // 0x0057 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX_360_WIRELESS;                                           // 0x0058 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX_ONE;                                                    // 0x0059 (size: 0x1)
    bool JOYSTICK_HIDAPI_XBOX_ONE_HOME_LED;                                           // 0x005A (size: 0x1)
    bool JOYSTICK_RAWINPUT_CORRELATE_XINPUT;                                          // 0x005B (size: 0x1)
    bool JOYSTICK_ROG_CHAKRAM;                                                        // 0x005C (size: 0x1)
    bool JOYSTICK_THREAD;                                                             // 0x005D (size: 0x1)
    bool LINUX_DIGITAL_HATS;                                                          // 0x005E (size: 0x1)
    bool LINUX_HAT_DEADZONES;                                                         // 0x005F (size: 0x1)
    bool LINUX_JOYSTICK_CLASSIC;                                                      // 0x0060 (size: 0x1)
    bool LINUX_JOYSTICK_DEADZONES;                                                    // 0x0061 (size: 0x1)
    bool JOYSTICK_ALLOW_BACKGROUND_EVENTS;                                            // 0x0062 (size: 0x1)

}; // Size: 0x68

class USimpleControllerStatusAsyncEvent : public UBlueprintAsyncActionBase
{
    FSimpleControllerStatusAsyncEventAttached attached;                               // 0x0030 (size: 0x10)
    void ControllerStatusEvent(const FSimpleControllerDevice device);
    FSimpleControllerStatusAsyncEventDetached detached;                               // 0x0040 (size: 0x10)
    void ControllerStatusEvent(const FSimpleControllerDevice device);

    void ControllerStatusEvent__DelegateSignature(const FSimpleControllerDevice device);
    class USimpleControllerStatusAsyncEvent* controllerStatusAsyncEvent();
}; // Size: 0x50

class USimpleControllerUIEnableSelection : public UBlueprintAsyncActionBase
{
    FSimpleControllerUIEnableSelectionOnSelect onSelect;                              // 0x0030 (size: 0x10)
    void selectedWidgetEventDelegate(class UWidget* mainWidget, class UWidget* selectedWidget, int32 connectionIndex, bool hasNewSelection, ESimpleControllerUIDirection lastDirection);

    void uiDirectionalPadEvent(const FString DeviceID, const int32 directionalPadValue, int32 directionalPadIndex, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void uiAxisEvent(const FString DeviceID, const int32 axisID, const float AxisValue, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void selectUIElement(class UWidget* Widget, int32 fakeConnectionIndex);
    void selectNextUIElement(ESimpleControllerUIDirection Direction, int32 fakeConnectionIndex);
    void selectedWidgetEventDelegate__DelegateSignature(class UWidget* mainWidget, class UWidget* selectedWidget, int32 connectionIndex, bool hasNewSelection, ESimpleControllerUIDirection lastDirection);
    void resumeSimpleControllerUISelection();
    void pauseSimpleControllerUISelection();
    class USimpleControllerUIEnableSelection* enableSimpleControllerUISelection(class USimpleControllerUIEnableSelection*& activeUIElement, class UWidget* mainWidget, TArray<class UWidget*> childWidgets, class UWidget* defaultWidgetToSelect, TArray<int32> connectionIndexes, bool useDpad, int32 horizontalAxisID, int32 verticalAxisID);
    void destroySimpleControllerUISelection();
}; // Size: 0xE8

class USimpleControllerUnrealEvents : public UObject
{
}; // Size: 0x40

class USimpleControllerUnrealMobileEvents : public UObject
{
}; // Size: 0xB0

class USimpleControllerWheel : public UObject
{

    void wheelAxisEvent(const FString DeviceID, const int32 axisID, const float AxisValue, const int32 deviceIndex, const FSimpleControllerDevice device, const int32 connectionIndex);
    void updateConstantForceOnWheel(int32 Force);
    void updateAutocenterWheel(FSimpleControllerDevice device, bool stopWhenCentered, float defaultStrength, float slowdownStrength, float autocenterDesiredEndPosition);
    void stopAutocenter(FSimpleControllerDevice device);
    void moveWheelToHardStop(FSimpleControllerDevice device, float hardStopStrength, float moveWheelToHardStopLength);
    void moveWheelTo(FSimpleControllerDevice device, float Position, float Strength, float hardStopStrength, float stopLength, bool doHardStop);
}; // Size: 0x4D0

class UStartControllerWebserverAsyncEvent : public UBlueprintAsyncActionBase
{
    FStartControllerWebserverAsyncEventOnSuccess onSuccess;                           // 0x00C0 (size: 0x10)
    void startControllerWebserverEvent(const FControllerWebserver webServer);
    FStartControllerWebserverAsyncEventOnFail onFail;                                 // 0x00D0 (size: 0x10)
    void startControllerWebserverEvent(const FControllerWebserver webServer);

    void stopControllerWebserver();
    void startControllerWebserverEvent__DelegateSignature(const FControllerWebserver webServer);
    class UStartControllerWebserverAsyncEvent* startControllerWebserverAsync(FString QRLibPath, FString controllerWebUIPath);
    FString getServerUrl(FControllerWebserver webServer);
    FString getQCode(FControllerWebserver webServer);
}; // Size: 0xE0

#endif
