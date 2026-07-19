---@meta

---@class FControllerWebserver
local FControllerWebserver = {}


---@class FSimpleControllerDevice
local FSimpleControllerDevice = {}


---@class FSimpleControllerForceFeedbackEffect
local FSimpleControllerForceFeedbackEffect = {}


---@class FSimpleControllerMappingAxisAction
---@field Description FString
---@field Tag FString
---@field InvertAxis boolean
---@field bStructID boolean
local FSimpleControllerMappingAxisAction = {}



---@class FSimpleControllerMappingButtonAction
---@field Description FString
---@field Tag FString
---@field bStructID boolean
local FSimpleControllerMappingButtonAction = {}



---@class FSimpleControllerMappingProfile
---@field structID FGuid
---@field buttonActions TMap<FString, FSimpleControllerMappingButtonAction>
---@field axisActions TMap<FString, FSimpleControllerMappingAxisAction>
local FSimpleControllerMappingProfile = {}



---@class UAutocenterAsyncEvent : UBlueprintAsyncActionBase
---@field Finished FAutocenterAsyncEventFinished
local UAutocenterAsyncEvent = {}

---@param device FSimpleControllerDevice
---@param stopWhenCentered boolean
---@param defaultStrength float
---@param slowdownStrength float
---@param desiredEndPosition float
---@param Tolerance float
---@param showLogs boolean
---@param wheelAxisID int32
---@return UAutocenterAsyncEvent
function UAutocenterAsyncEvent:autocenterWheel(device, stopWhenCentered, defaultStrength, slowdownStrength, desiredEndPosition, Tolerance, showLogs, wheelAxisID) end
function UAutocenterAsyncEvent:AutocenterEvent__DelegateSignature() end


---@class USimpleControllerAxisAsyncEvent : UBlueprintAsyncActionBase
---@field onAction FSimpleControllerAxisAsyncEventOnAction
local USimpleControllerAxisAsyncEvent = {}

---@param axisID int32
---@param AxisValue float
---@param connectionIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerAxisAsyncEvent:ControllerAxisEvent__DelegateSignature(axisID, AxisValue, connectionIndex, device) end
---@param triggerEventIf ESimpleControllerEventType
---@return USimpleControllerAxisAsyncEvent
function USimpleControllerAxisAsyncEvent:controllerAxisAsyncEvent(triggerEventIf) end


---@class USimpleControllerBPLibrary : UBlueprintFunctionLibrary
---@field onButtonDownEventDelegate FSimpleControllerBPLibraryOnButtonDownEventDelegate
---@field onButtonUpEventDelegate FSimpleControllerBPLibraryOnButtonUpEventDelegate
---@field onDirectionalPadEventDelegate FSimpleControllerBPLibraryOnDirectionalPadEventDelegate
---@field onBallMovedEventDelegate FSimpleControllerBPLibraryOnBallMovedEventDelegate
---@field onaxisMovedEventDelegate FSimpleControllerBPLibraryOnaxisMovedEventDelegate
---@field ondeviceAttachedEventDelegate FSimpleControllerBPLibraryOndeviceAttachedEventDelegate
---@field ondeviceDetachedEventDelegate FSimpleControllerBPLibraryOndeviceDetachedEventDelegate
---@field onaccelerationSensorEventDelegate FSimpleControllerBPLibraryOnaccelerationSensorEventDelegate
---@field ongyroSensorEventDelegate FSimpleControllerBPLibraryOngyroSensorEventDelegate
---@field ontouchpadMotionEventDelegate FSimpleControllerBPLibraryOntouchpadMotionEventDelegate
---@field ontouchpadDownEventDelegate FSimpleControllerBPLibraryOntouchpadDownEventDelegate
---@field ontouchpadUpEventDelegate FSimpleControllerBPLibraryOntouchpadUpEventDelegate
---@field SimpleControllerWheel USimpleControllerWheel
local USimpleControllerBPLibrary = {}

---@param successful boolean
---@param errorMessage FString
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@return FSimpleControllerForceFeedbackEffect
function USimpleControllerBPLibrary:uploadForceFeedbackEffect(successful, errorMessage, ForceFeedbackEffect) end
---@param successful boolean
---@param errorMessage FString
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param iterations int32
---@return FSimpleControllerForceFeedbackEffect
function USimpleControllerBPLibrary:uploadAndRunForceFeedbackEffect(successful, errorMessage, ForceFeedbackEffect, iterations) end
---@param successful boolean
---@param errorMessage FString
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param directionX int32
---@param directionY int32
---@param directionZ int32
---@param Length int32
---@param Delay int32
---@param Level float
---@param attackLength int32
---@param attackLevel float
---@param fadeLength int32
---@param fadeLevel float
function USimpleControllerBPLibrary:updateConstantForceFeedbackEffect(successful, errorMessage, ForceFeedbackEffect, directionX, directionY, directionZ, Length, Delay, Level, attackLength, attackLevel, fadeLength, fadeLevel) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadUpEventDelegate__DelegateSignature(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadUpEventDelegate(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadMotionEventDelegate__DelegateSignature(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadMotionEventDelegate(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadDownEventDelegate__DelegateSignature(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
---@param DeviceID FString
---@param touchpadIndex int32
---@param finger int32
---@param X float
---@param Y float
---@param Pressure float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:touchpadDownEventDelegate(DeviceID, touchpadIndex, finger, X, Y, Pressure, deviceIndex, device) end
function USimpleControllerBPLibrary:stopRumbleWheel() end
---@param successful boolean
---@param errorMessage FString
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@return FSimpleControllerForceFeedbackEffect
function USimpleControllerBPLibrary:stopForceFeedbackEffect(successful, errorMessage, ForceFeedbackEffect) end
---@param WorldContextObject UObject
---@param keyboardButtons boolean
---@param mousedButtons boolean
function USimpleControllerBPLibrary:setUnrealKeyboardAndMouseEvents(WorldContextObject, keyboardButtons, mousedButtons) end
---@param device FSimpleControllerDevice
---@param Type ESimpleControllerSensorType
---@param Enable boolean
function USimpleControllerBPLibrary:setSensor(device, Type, Enable) end
---@param X int32
---@param Y int32
function USimpleControllerBPLibrary:SetMousePosition(X, Y) end
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param Color FColor
function USimpleControllerBPLibrary:setLEDColor(successful, errorMessage, device, Color) end
---@param device FSimpleControllerDevice
---@param gain int32
function USimpleControllerBPLibrary:setGainForceFeedback(device, gain) end
---@param device FSimpleControllerDevice
---@param axisID int32
---@param deadZoneMaxPositive float
---@param deadZoneMaxNegative float
---@param deadZoneMinPositive float
---@param deadZoneMinNegative float
---@return FSimpleControllerDevice
function USimpleControllerBPLibrary:setDeadZone(device, axisID, deadZoneMaxPositive, deadZoneMaxNegative, deadZoneMinPositive, deadZoneMinNegative) end
---@param device FSimpleControllerDevice
---@param autocenter int32
function USimpleControllerBPLibrary:setAutocenterForceFeedbackSDL(device, autocenter) end
---@param StatusEvents boolean
---@param ButtonEvents boolean
---@param AxisEvents boolean
---@param GamepadSticksEvents boolean
---@param GamepadTriggerEvents boolean
---@param GamepadFaceButtonsEvents boolean
---@param GamepadControlEvents boolean
---@param GamepadStickButtonsEvents boolean
---@param GamepadShoulderButtonsEvents boolean
---@param GamepadDpadEvents boolean
---@param GamepadSpecialButtonsEvents boolean
function USimpleControllerBPLibrary:setAsyncNodesReadyToDestroy(StatusEvents, ButtonEvents, AxisEvents, GamepadSticksEvents, GamepadTriggerEvents, GamepadFaceButtonsEvents, GamepadControlEvents, GamepadStickButtonsEvents, GamepadShoulderButtonsEvents, GamepadDpadEvents, GamepadSpecialButtonsEvents) end
---@param successful boolean
---@param errorMessage FString
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param iterations int32
---@return FSimpleControllerForceFeedbackEffect
function USimpleControllerBPLibrary:runForceFeedbackEffect(successful, errorMessage, ForceFeedbackEffect, iterations) end
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param strengthLeftMotor float
---@param strengthRightMotor float
---@param lengthInMilliseconds int32
---@param timeBetweenDirectionChangeInMilliseconds int32
function USimpleControllerBPLibrary:rumbleWheel(successful, errorMessage, device, strengthLeftMotor, strengthRightMotor, lengthInMilliseconds, timeBetweenDirectionChangeInMilliseconds) end
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param strengthLeft float
---@param strengthRight float
---@param lengthInMilliseconds int32
function USimpleControllerBPLibrary:rumbleTrigger(successful, errorMessage, device, strengthLeft, strengthRight, lengthInMilliseconds) end
---@param successful boolean
---@param errorMessage FString
---@param connectionIndex int32
---@param strengthSmallMotor float
---@param strengthLargeMotor float
---@param lengthInMilliseconds int32
function USimpleControllerBPLibrary:rumbleByConnectionIndex(successful, errorMessage, connectionIndex, strengthSmallMotor, strengthLargeMotor, lengthInMilliseconds) end
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param strengthSmallMotor float
---@param strengthLargeMotor float
---@param lengthInMilliseconds int32
function USimpleControllerBPLibrary:rumble(successful, errorMessage, device, strengthSmallMotor, strengthLargeMotor, lengthInMilliseconds) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
function USimpleControllerBPLibrary:removeButtonMapping(mappingProfile, ActionName) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
function USimpleControllerBPLibrary:RemoveAxisMapping(mappingProfile, ActionName) end
---@param device FSimpleControllerDevice
---@param axisID int32
---@param Type ESimpleControllerAxisCorrection
function USimpleControllerBPLibrary:removeAxisCorrection(device, axisID, Type) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param device FSimpleControllerDevice
---@param buttonID int32
---@return boolean
function USimpleControllerBPLibrary:mapButton(mappingProfile, ActionName, device, buttonID) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param device FSimpleControllerDevice
---@param axisID int32
---@return boolean
function USimpleControllerBPLibrary:mapAxis(mappingProfile, ActionName, device, axisID) end
---@param connectionIndex int32
---@return boolean
function USimpleControllerBPLibrary:isXinputCompatible(connectionIndex) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@return boolean
function USimpleControllerBPLibrary:isButtonMapped(mappingProfile, ActionName) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@return boolean
function USimpleControllerBPLibrary:isAxisMapped(mappingProfile, ActionName) end
---@param WorldContextObject UObject
function USimpleControllerBPLibrary:initIOSPart(WorldContextObject) end
---@param DeviceID FString
---@param valueA float
---@param valueB float
---@param valueC float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:gyroSensorEventDelegate__DelegateSignature(DeviceID, valueA, valueB, valueC, deviceIndex, device) end
---@param DeviceID FString
---@param valueA float
---@param valueB float
---@param valueC float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:gyroSensorEventDelegate(DeviceID, valueA, valueB, valueC, deviceIndex, device) end
---@param System ESimpleControllerSystemType
---@param dedicatedServer boolean
function USimpleControllerBPLibrary:getSystemType(System, dedicatedServer) end
---@return USimpleControllerBPLibrary
function USimpleControllerBPLibrary:getSimpleControllerTarget() end
---@param X int32
---@param Y int32
function USimpleControllerBPLibrary:GetMousePosition(X, Y) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param Tag FString
---@param buttonActions TArray<FSimpleControllerMappingButtonAction>
---@param axisActions TArray<FSimpleControllerMappingAxisAction>
function USimpleControllerBPLibrary:getMappingActionsByTag(mappingProfile, Tag, buttonActions, axisActions) end
---@param isMapped boolean
---@param actionNames TArray<FString>
---@param buttonID int32
---@param connectionIndex int32
function USimpleControllerBPLibrary:getMappedButtonActions(isMapped, actionNames, buttonID, connectionIndex) end
---@param isMapped boolean
---@param actionNames TArray<FString>
---@param axisID int32
---@param connectionIndex int32
function USimpleControllerBPLibrary:getMappedAxisActions(isMapped, actionNames, axisID, connectionIndex) end
---@param device FSimpleControllerDevice
---@param directionalPadIndex int32
---@return int32
function USimpleControllerBPLibrary:getHatValueBySDL(device, directionalPadIndex) end
---@param device FSimpleControllerDevice
---@param powerLevel ESimpleControllerPowerLevel
function USimpleControllerBPLibrary:getCurrentPowerLevel(device, powerLevel) end
---@return TArray<FSimpleControllerDevice>
function USimpleControllerBPLibrary:getConnectedControllers() end
---@param device FSimpleControllerDevice
---@param buttonID int32
---@return ESimpleControllerButtonStatus
function USimpleControllerBPLibrary:getButtonValueBySDL(device, buttonID) end
---@param device FSimpleControllerDevice
---@param buttonID int32
---@return FString
function USimpleControllerBPLibrary:getButtonName(device, buttonID) end
---@param profile FSimpleControllerMappingProfile
---@param buttonActions TMap<FString, FSimpleControllerMappingButtonAction>
function USimpleControllerBPLibrary:getButtonActions(profile, buttonActions) end
---@param device FSimpleControllerDevice
---@param ballIndex int32
---@param xRel int32
---@param yRel int32
function USimpleControllerBPLibrary:getBallValueBySDL(device, ballIndex, xRel, yRel) end
---@param device FSimpleControllerDevice
---@param axisValues TMap<int32, float>
function USimpleControllerBPLibrary:getAxisValues(device, axisValues) end
---@param device FSimpleControllerDevice
---@param axisID int32
---@return float
function USimpleControllerBPLibrary:getAxisValueBySDL(device, axisID) end
---@param profile FSimpleControllerMappingProfile
---@param axisActions TMap<FString, FSimpleControllerMappingAxisAction>
function USimpleControllerBPLibrary:getAxisActions(profile, axisActions) end
---@param startPosition SCDualSenseTriggerEffectStartPosition
---@param endPosition SCDualSenseTriggerEffectEndPosition
---@param Strength SCDualSenseTriggerEffectStrength
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandWeapon(startPosition, endPosition, Strength, Left, Right) end
---@param startingZone SCDualSenseTriggerEffectStartZone
---@param Strength SCDualSenseTriggerEffectStrength
---@param frequency uint8
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandVibration(startingZone, Strength, frequency, Left, Right) end
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandOFF(Left, Right) end
---@param frequency uint8
---@param Strength_0 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_1 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_2 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_3 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_4 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_5 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_6 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_7 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_8 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_9 SCDualSenseTriggerEffectStrengthMulti
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandMultiVibration(frequency, Strength_0, Strength_1, Strength_2, Strength_3, Strength_4, Strength_5, Strength_6, Strength_7, Strength_8, Strength_9, Left, Right) end
---@param Strength_0 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_1 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_2 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_3 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_4 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_5 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_6 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_7 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_8 SCDualSenseTriggerEffectStrengthMulti
---@param Strength_9 SCDualSenseTriggerEffectStrengthMulti
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandMultiFeedback(Strength_0, Strength_1, Strength_2, Strength_3, Strength_4, Strength_5, Strength_6, Strength_7, Strength_8, Strength_9, Left, Right) end
---@param startingZone SCDualSenseTriggerEffectStartZone
---@param Strength SCDualSenseTriggerEffectStrength
---@param Left boolean
---@param Right boolean
---@return TArray<uint8>
function USimpleControllerBPLibrary:generateDualSenseTriggerCommandFeedback(startingZone, Strength, Left, Right) end
---@param Button ESimpleControllerMouseTriggerButton
---@param Type ESimpleControllerMouseTriggerType
function USimpleControllerBPLibrary:fireMouseButtonEvent(Button, Type) end
---@param keycode int32
---@param Type ESimpleControllerKeyboardTriggerType
---@param UserIndex int32
function USimpleControllerBPLibrary:fireKeyboardButtonEvent(keycode, Type, UserIndex) end
---@param connectionIndex int32
---@param found boolean
---@param deviceIndex int32
function USimpleControllerBPLibrary:findDeviceIndexByConnectionIndex(connectionIndex, found, deviceIndex) end
---@param deviceIndex int32
---@param found boolean
---@return FSimpleControllerDevice
function USimpleControllerBPLibrary:findControllerByDeviceIndex(deviceIndex, found) end
---@param DeviceID FString
---@param found boolean
---@return FSimpleControllerDevice
function USimpleControllerBPLibrary:findControllerByDeviceID(DeviceID, found) end
---@param connectionIndex int32
---@param found boolean
---@return FSimpleControllerDevice
function USimpleControllerBPLibrary:findControllerByConnectionIndex(connectionIndex, found) end
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param bytes TArray<uint8>
function USimpleControllerBPLibrary:executeCommandOnController(successful, errorMessage, device, bytes) end
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:enableForceFeedbackOnDevice(device) end
---@param device FSimpleControllerDevice
---@param Force int32
---@param wheelAxisID int32
---@return boolean
function USimpleControllerBPLibrary:enableConstantForceOnWheel(device, Force, wheelAxisID) end
function USimpleControllerBPLibrary:disableUIVirtualKeys() end
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:disableForceFeedbackOnDevice(device) end
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:disableConstantForceOnWheel(device) end
---@param DeviceID FString
---@param directionalPadValue int32
---@param directionalPadIndex int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:directionalPadEventDelegate__DelegateSignature(DeviceID, directionalPadValue, directionalPadIndex, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param directionalPadValue int32
---@param directionalPadIndex int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:directionalPadEventDelegate(DeviceID, directionalPadValue, directionalPadIndex, deviceIndex, device, connectionIndex) end
---@param directionalPadValue int32
---@param Direction ESimpleControllerDirectionalPad
function USimpleControllerBPLibrary:directinalPadValueToDirection(directionalPadValue, Direction) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:deviceDetachedEventDelegate__DelegateSignature(device, connectionIndex) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:deviceDetachedEventDelegate(device, connectionIndex) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:deviceAttachedEventDelegate__DelegateSignature(device, connectionIndex) end
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:deviceAttachedEventDelegate(device, connectionIndex) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
function USimpleControllerBPLibrary:destroyForceFeedbackEffect(ForceFeedbackEffect) end
---@param ProfileName FString
---@return boolean
function USimpleControllerBPLibrary:deleteMappingFile(ProfileName) end
---@param ProfileName FString
---@param fileData FString
---@param overwriteExistingFile boolean
---@return boolean
function USimpleControllerBPLibrary:createMappingFile(ProfileName, fileData, overwriteExistingFile) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param directionType ESimpleControllerForceFeedbackDirectionType
---@param directionX int32
---@param directionY int32
---@param directionZ int32
---@param Length int32
---@param Delay int32
---@param startLevel float
---@param endLevel float
---@param attackLength int32
---@param attackLevel float
---@param fadeLength int32
---@param fadeLevel float
function USimpleControllerBPLibrary:createForceFeedbackEffectRamp(ForceFeedbackEffect, successful, errorMessage, device, directionType, directionX, directionY, directionZ, Length, Delay, startLevel, endLevel, attackLength, attackLevel, fadeLength, fadeLevel) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param PeriodicType ESimpleControllerForceFeedbackEffectPeriodicType
---@param directionType ESimpleControllerForceFeedbackDirectionType
---@param directionX int32
---@param directionY int32
---@param directionZ int32
---@param Length int32
---@param Delay int32
---@param Period int32
---@param Magnitude float
---@param Offset float
---@param phase int32
---@param attackLength int32
---@param attackLevel float
---@param fadeLength int32
---@param fadeLevel float
function USimpleControllerBPLibrary:createForceFeedbackEffectPeriodic(ForceFeedbackEffect, successful, errorMessage, device, PeriodicType, directionType, directionX, directionY, directionZ, Length, Delay, Period, Magnitude, Offset, phase, attackLength, attackLevel, fadeLength, fadeLevel) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param directionType ESimpleControllerForceFeedbackDirectionType
---@param directionX int32
---@param directionY int32
---@param directionZ int32
---@param Length int32
---@param Delay int32
---@param Level float
---@param attackLength int32
---@param attackLevel float
---@param fadeLength int32
---@param fadeLevel float
function USimpleControllerBPLibrary:createForceFeedbackEffectConstant(ForceFeedbackEffect, successful, errorMessage, device, directionType, directionX, directionY, directionZ, Length, Delay, Level, attackLength, attackLevel, fadeLength, fadeLevel) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param successful boolean
---@param errorMessage FString
---@param device FSimpleControllerDevice
---@param directionType ESimpleControllerForceFeedbackDirectionType
---@param ConditionType ESimpleControllerForceFeedbackEffectConditionType
---@param useDirectionX boolean
---@param useDirectionY boolean
---@param useDirectionZ boolean
---@param Length int32
---@param Delay int32
---@param rightLevel float
---@param leftLevel float
---@param rightCoefficient float
---@param leftCoefficient float
---@param deadband float
---@param Center float
function USimpleControllerBPLibrary:createForceFeedbackEffectCondition(ForceFeedbackEffect, successful, errorMessage, device, directionType, ConditionType, useDirectionX, useDirectionY, useDirectionZ, Length, Delay, rightLevel, leftLevel, rightCoefficient, leftCoefficient, deadband, Center) end
---@param device FSimpleControllerDevice
---@param movedByForce boolean
function USimpleControllerBPLibrary:changeForceFeedbackWheelDirectionType(device, movedByForce) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param InvertAxis boolean
function USimpleControllerBPLibrary:changeAxisActionSettings(mappingProfile, ActionName, InvertAxis) end
function USimpleControllerBPLibrary:cancelMapping() end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:buttonUpEventDelegate__DelegateSignature(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:buttonUpEventDelegate(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
---@param buttonID int32
---@param buttons ESimpleControllerButtons
function USimpleControllerBPLibrary:buttonIDToButton(buttonID, buttons) end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:buttonDownEventDelegate__DelegateSignature(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param buttonID int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:buttonDownEventDelegate(DeviceID, buttonID, deviceIndex, device, connectionIndex) end
---@param profile FSimpleControllerMappingProfile
---@param buttonActions TMap<FString, FSimpleControllerMappingButtonAction>
---@param axisActions TMap<FString, FSimpleControllerMappingAxisAction>
function USimpleControllerBPLibrary:breakMappingProfile(profile, buttonActions, axisActions) end
---@param ForceFeedbackEffect FSimpleControllerForceFeedbackEffect
---@param effectID int32
---@param successful boolean
function USimpleControllerBPLibrary:breakForceFeedbackEffect(ForceFeedbackEffect, effectID, successful) end
---@param device FSimpleControllerDevice
---@param deviceIndex int32
---@param connectionIndex int32
---@param DeviceID FString
---@param deviceName FString
---@param controllerName FString
---@param vendorID int32
---@param productID int32
---@param numAxes int32
---@param numButtons int32
---@param numDirectionalPadAxes int32
---@param numBalls int32
---@param hasHaptic boolean
---@param hasRumble boolean
---@param hasRumbleTriggers boolean
---@param hasAccelerationSensor boolean
---@param hasGyroSensor boolean
---@param hasLED boolean
---@param gamepadAPI_Support boolean
---@param isXinputCompatible boolean
---@param Type ESimpleControllerType
---@param wheelMovedByForce boolean
function USimpleControllerBPLibrary:breakDeviceInfo(device, deviceIndex, connectionIndex, DeviceID, deviceName, controllerName, vendorID, productID, numAxes, numButtons, numDirectionalPadAxes, numBalls, hasHaptic, hasRumble, hasRumbleTriggers, hasAccelerationSensor, hasGyroSensor, hasLED, gamepadAPI_Support, isXinputCompatible, Type, wheelMovedByForce) end
---@param device FSimpleControllerDevice
---@param forceFeedback_CONSTANT boolean
---@param forceFeedback_SINE boolean
---@param forceFeedback_LEFTRIGHT boolean
---@param forceFeedback_TRIANGLE boolean
---@param forceFeedback_SAWTOOTHUP boolean
---@param forceFeedback_SAWTOOTHDOWN boolean
---@param forceFeedback_RAMP boolean
---@param forceFeedback_SPRING boolean
---@param forceFeedback_DAMPER boolean
---@param forceFeedback_INERTIA boolean
---@param forceFeedback_FRICTION boolean
---@param forceFeedback_CUSTOM boolean
---@param forceFeedback_GAIN boolean
---@param forceFeedback_AUTOCENTER boolean
---@param forceFeedback_STATUS boolean
---@param forceFeedback_PAUSE boolean
---@param forceFeedback_POLAR boolean
---@param forceFeedback_CARTESIAN boolean
---@param forceFeedback_SPHERICAL boolean
---@param forceFeedback_INFINITY boolean
---@param maxSimultaneouslyEffects int32
function USimpleControllerBPLibrary:breakDeviceForceFeedbackInfo(device, forceFeedback_CONSTANT, forceFeedback_SINE, forceFeedback_LEFTRIGHT, forceFeedback_TRIANGLE, forceFeedback_SAWTOOTHUP, forceFeedback_SAWTOOTHDOWN, forceFeedback_RAMP, forceFeedback_SPRING, forceFeedback_DAMPER, forceFeedback_INERTIA, forceFeedback_FRICTION, forceFeedback_CUSTOM, forceFeedback_GAIN, forceFeedback_AUTOCENTER, forceFeedback_STATUS, forceFeedback_PAUSE, forceFeedback_POLAR, forceFeedback_CARTESIAN, forceFeedback_SPHERICAL, forceFeedback_INFINITY, maxSimultaneouslyEffects) end
---@param action FSimpleControllerMappingButtonAction
---@param ActionName FString
---@param Description FString
---@param Tag FString
---@param connectionIndex int32
---@param buttonID int32
---@param buttonName FString
---@param deviceName FString
---@param controllerName FString
---@param vendorID int32
---@param productID int32
function USimpleControllerBPLibrary:breakButtonAction(action, ActionName, Description, Tag, connectionIndex, buttonID, buttonName, deviceName, controllerName, vendorID, productID) end
---@param action FSimpleControllerMappingAxisAction
---@param ActionName FString
---@param Description FString
---@param Tag FString
---@param connectionIndex int32
---@param axisID int32
---@param InvertAxis boolean
---@param deviceName FString
---@param controllerName FString
---@param vendorID int32
---@param productID int32
function USimpleControllerBPLibrary:breakAxisAction(action, ActionName, Description, Tag, connectionIndex, axisID, InvertAxis, deviceName, controllerName, vendorID, productID) end
---@param DeviceID FString
---@param ballID int32
---@param xRel float
---@param yRel int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:ballMovedEventDelegate__DelegateSignature(DeviceID, ballID, xRel, yRel, device) end
---@param DeviceID FString
---@param ballID int32
---@param xRel int32
---@param yRel int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:ballMovedEventDelegate(DeviceID, ballID, xRel, yRel, device) end
---@param DeviceID FString
---@param axisID int32
---@param AxisValue float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:axisMovedEventDelegate__DelegateSignature(DeviceID, axisID, AxisValue, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param axisID int32
---@param AxisValue float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerBPLibrary:axisMovedEventDelegate(DeviceID, axisID, AxisValue, deviceIndex, device, connectionIndex) end
---@param X int32
---@param Y int32
function USimpleControllerBPLibrary:addMousePosition(X, Y) end
---@param device FSimpleControllerDevice
---@param axisID int32
---@param Type ESimpleControllerAxisCorrection
function USimpleControllerBPLibrary:addAxisCorrection(device, axisID, Type) end
---@param DeviceID FString
---@param valueA float
---@param valueB float
---@param valueC float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:accelerationSensorEventDelegate__DelegateSignature(DeviceID, valueA, valueB, valueC, deviceIndex, device) end
---@param DeviceID FString
---@param valueA float
---@param valueB float
---@param valueC float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerBPLibrary:accelerationSensorEventDelegate(DeviceID, valueA, valueB, valueC, deviceIndex, device) end


---@class USimpleControllerButtonAsyncEvent : UBlueprintAsyncActionBase
---@field buttonDown FSimpleControllerButtonAsyncEventButtonDown
---@field buttonUp FSimpleControllerButtonAsyncEventButtonUp
local USimpleControllerButtonAsyncEvent = {}

---@param buttonID int32
---@param connectionIndex int32
---@param device FSimpleControllerDevice
function USimpleControllerButtonAsyncEvent:ControllerButtonEvent__DelegateSignature(buttonID, connectionIndex, device) end
---@return USimpleControllerButtonAsyncEvent
function USimpleControllerButtonAsyncEvent:controllerButtonAsyncEvent() end


---@class USimpleControllerGamepadControlButtonEvents : UBlueprintAsyncActionBase
---@field backPressed FSimpleControllerGamepadControlButtonEventsBackPressed
---@field backReleased FSimpleControllerGamepadControlButtonEventsBackReleased
---@field startPressed FSimpleControllerGamepadControlButtonEventsStartPressed
---@field startReleased FSimpleControllerGamepadControlButtonEventsStartReleased
---@field guidePressed FSimpleControllerGamepadControlButtonEventsGuidePressed
---@field guideReleased FSimpleControllerGamepadControlButtonEventsGuideReleased
local USimpleControllerGamepadControlButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadControlButtonEvents
function USimpleControllerGamepadControlButtonEvents:gamepadEventControlButtons(connectionIndex) end
function USimpleControllerGamepadControlButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadDpadButtonEvents : UBlueprintAsyncActionBase
---@field bottomDpadPressed FSimpleControllerGamepadDpadButtonEventsBottomDpadPressed
---@field bottomDpadReleased FSimpleControllerGamepadDpadButtonEventsBottomDpadReleased
---@field topDpadPressed FSimpleControllerGamepadDpadButtonEventsTopDpadPressed
---@field topDpadReleased FSimpleControllerGamepadDpadButtonEventsTopDpadReleased
---@field rightDpadPressed FSimpleControllerGamepadDpadButtonEventsRightDpadPressed
---@field rightDpadReleased FSimpleControllerGamepadDpadButtonEventsRightDpadReleased
---@field leftDpadPressed FSimpleControllerGamepadDpadButtonEventsLeftDpadPressed
---@field leftDpadReleased FSimpleControllerGamepadDpadButtonEventsLeftDpadReleased
local USimpleControllerGamepadDpadButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadDpadButtonEvents
function USimpleControllerGamepadDpadButtonEvents:gamepadEventDpadButtons(connectionIndex) end
function USimpleControllerGamepadDpadButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadFaceButtonEvents : UBlueprintAsyncActionBase
---@field bottomPressed FSimpleControllerGamepadFaceButtonEventsBottomPressed
---@field bottomReleased FSimpleControllerGamepadFaceButtonEventsBottomReleased
---@field topPressed FSimpleControllerGamepadFaceButtonEventsTopPressed
---@field topReleased FSimpleControllerGamepadFaceButtonEventsTopReleased
---@field rightPressed FSimpleControllerGamepadFaceButtonEventsRightPressed
---@field rightReleased FSimpleControllerGamepadFaceButtonEventsRightReleased
---@field leftPressed FSimpleControllerGamepadFaceButtonEventsLeftPressed
---@field leftReleased FSimpleControllerGamepadFaceButtonEventsLeftReleased
local USimpleControllerGamepadFaceButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadFaceButtonEvents
function USimpleControllerGamepadFaceButtonEvents:gamepadEventFaceButtons(connectionIndex) end
function USimpleControllerGamepadFaceButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadShoulderButtonEvents : UBlueprintAsyncActionBase
---@field leftShoulderPressed FSimpleControllerGamepadShoulderButtonEventsLeftShoulderPressed
---@field leftShoulderReleased FSimpleControllerGamepadShoulderButtonEventsLeftShoulderReleased
---@field rightShoulderPressed FSimpleControllerGamepadShoulderButtonEventsRightShoulderPressed
---@field rightShoulderReleased FSimpleControllerGamepadShoulderButtonEventsRightShoulderReleased
local USimpleControllerGamepadShoulderButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadShoulderButtonEvents
function USimpleControllerGamepadShoulderButtonEvents:gamepadEventShoulderButtons(connectionIndex) end
function USimpleControllerGamepadShoulderButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadSpecialButtonEvents : UBlueprintAsyncActionBase
---@field Misc1Pressed FSimpleControllerGamepadSpecialButtonEventsMisc1Pressed
---@field Misc1Released FSimpleControllerGamepadSpecialButtonEventsMisc1Released
---@field XboxElitePaddleP1Pressed FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP1Pressed
---@field XboxElitePaddleP1Released FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP1Released
---@field XboxElitePaddleP2Pressed FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP2Pressed
---@field XboxElitePaddleP2Released FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP2Released
---@field XboxElitePaddleP3Pressed FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP3Pressed
---@field XboxElitePaddleP3Released FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP3Released
---@field XboxElitePaddleP4Pressed FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP4Pressed
---@field XboxElitePaddleP4Released FSimpleControllerGamepadSpecialButtonEventsXboxElitePaddleP4Released
---@field PSTouchpadPressed FSimpleControllerGamepadSpecialButtonEventsPSTouchpadPressed
---@field PSTouchpadReleased FSimpleControllerGamepadSpecialButtonEventsPSTouchpadReleased
local USimpleControllerGamepadSpecialButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadSpecialButtonEvents
function USimpleControllerGamepadSpecialButtonEvents:gamepadEventSpecialButtons(connectionIndex) end
function USimpleControllerGamepadSpecialButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadStickAxisEvents : UBlueprintAsyncActionBase
---@field leftStickX FSimpleControllerGamepadStickAxisEventsLeftStickX
---@field leftStickY FSimpleControllerGamepadStickAxisEventsLeftStickY
---@field rightStickX FSimpleControllerGamepadStickAxisEventsRightStickX
---@field rightStickY FSimpleControllerGamepadStickAxisEventsRightStickY
local USimpleControllerGamepadStickAxisEvents = {}

---@param triggerEventIf ESimpleControllerEventType
---@param connectionIndex int32
---@return USimpleControllerGamepadStickAxisEvents
function USimpleControllerGamepadStickAxisEvents:gamepadEventStickAxis(triggerEventIf, connectionIndex) end
---@param AxisValue float
function USimpleControllerGamepadStickAxisEvents:ControllerAxisEvent__DelegateSignature(AxisValue) end


---@class USimpleControllerGamepadStickButtonEvents : UBlueprintAsyncActionBase
---@field leftStickPressed FSimpleControllerGamepadStickButtonEventsLeftStickPressed
---@field leftStickReleased FSimpleControllerGamepadStickButtonEventsLeftStickReleased
---@field rightStickPressed FSimpleControllerGamepadStickButtonEventsRightStickPressed
---@field rightStickReleased FSimpleControllerGamepadStickButtonEventsRightStickReleased
local USimpleControllerGamepadStickButtonEvents = {}

---@param connectionIndex int32
---@return USimpleControllerGamepadStickButtonEvents
function USimpleControllerGamepadStickButtonEvents:gamepadEventStickButtons(connectionIndex) end
function USimpleControllerGamepadStickButtonEvents:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerGamepadTriggerAxisEvents : UBlueprintAsyncActionBase
---@field leftTrigger FSimpleControllerGamepadTriggerAxisEventsLeftTrigger
---@field rightTrigger FSimpleControllerGamepadTriggerAxisEventsRightTrigger
local USimpleControllerGamepadTriggerAxisEvents = {}

---@param triggerEventIf ESimpleControllerEventType
---@param connectionIndex int32
---@return USimpleControllerGamepadTriggerAxisEvents
function USimpleControllerGamepadTriggerAxisEvents:gamepadEventTriggerAxis(triggerEventIf, connectionIndex) end
---@param AxisValue float
function USimpleControllerGamepadTriggerAxisEvents:ControllerAxisEvent__DelegateSignature(AxisValue) end


---@class USimpleControllerMappedButtonAsyncEvent : UBlueprintAsyncActionBase
---@field actionPressed FSimpleControllerMappedButtonAsyncEventActionPressed
---@field actionReleased FSimpleControllerMappedButtonAsyncEventActionReleased
local USimpleControllerMappedButtonAsyncEvent = {}

---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@return USimpleControllerMappedButtonAsyncEvent
function USimpleControllerMappedButtonAsyncEvent:controllerEventMappedButton(mappingProfile, ActionName) end
function USimpleControllerMappedButtonAsyncEvent:ControllerButtonEvent__DelegateSignature() end


---@class USimpleControllerMappingAxis : UBlueprintAsyncActionBase
---@field successful FSimpleControllerMappingAxisSuccessful
---@field Error FSimpleControllerMappingAxisError
---@field isMapped FSimpleControllerMappingAxisIsMapped
---@field Timeout FSimpleControllerMappingAxisTimeout
---@field Timer FSimpleControllerMappingAxisTimer
local USimpleControllerMappingAxis = {}

---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param timeInSeconds int32
---@param minAxisValueToReact float
---@param allowMultipleMapping boolean
---@return USimpleControllerMappingAxis
function USimpleControllerMappingAxis:startMappingAxis(mappingProfile, ActionName, timeInSeconds, minAxisValueToReact, allowMultipleMapping) end
---@param action FSimpleControllerMappingAxisAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedAxisID int32
---@param usedConnectionIndex int32
function USimpleControllerMappingAxis:ControllerMappingEvent__DelegateSignature(action, Seconds, usedDevice, usedAxisID, usedConnectionIndex) end


---@class USimpleControllerMappingAxisEvents : UBlueprintAsyncActionBase
---@field onAction FSimpleControllerMappingAxisEventsOnAction
local USimpleControllerMappingAxisEvents = {}

---@param triggerEventIf ESimpleControllerEventType
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@return USimpleControllerMappingAxisEvents
function USimpleControllerMappingAxisEvents:controllerEventMappedAxis(triggerEventIf, mappingProfile, ActionName) end
---@param AxisValue float
function USimpleControllerMappingAxisEvents:ControllerAxisEvent__DelegateSignature(AxisValue) end


---@class USimpleControllerMappingButton : UBlueprintAsyncActionBase
---@field successful FSimpleControllerMappingButtonSuccessful
---@field Error FSimpleControllerMappingButtonError
---@field isMapped FSimpleControllerMappingButtonIsMapped
---@field Timeout FSimpleControllerMappingButtonTimeout
---@field Timer FSimpleControllerMappingButtonTimer
local USimpleControllerMappingButton = {}

---@param WorldContextObject UObject
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param whiteList TArray<int32>
---@param blacklist TArray<int32>
---@param timeInSeconds int32
---@param allowMultipleMapping boolean
---@param keyboardButtons boolean
---@param mousedButtons boolean
---@param reactType ESimpleControllerMapButtonReactType
---@return USimpleControllerMappingButton
function USimpleControllerMappingButton:startMappingButton(WorldContextObject, mappingProfile, ActionName, whiteList, blacklist, timeInSeconds, allowMultipleMapping, keyboardButtons, mousedButtons, reactType) end
---@param action FSimpleControllerMappingButtonAction
---@param Seconds int32
---@param usedDevice FSimpleControllerDevice
---@param usedButtonID int32
---@param usedConnectionIndex int32
function USimpleControllerMappingButton:ControllerMappingEvent__DelegateSignature(action, Seconds, usedDevice, usedButtonID, usedConnectionIndex) end


---@class USimpleControllerMappingCalibrateAxis : UBlueprintAsyncActionBase
---@field finishedMax FSimpleControllerMappingCalibrateAxisFinishedMax
---@field finishedMin FSimpleControllerMappingCalibrateAxisFinishedMin
---@field Error FSimpleControllerMappingCalibrateAxisError
---@field Timer FSimpleControllerMappingCalibrateAxisTimer
---@field axisValueChange FSimpleControllerMappingCalibrateAxisAxisValueChange
local USimpleControllerMappingCalibrateAxis = {}

---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
function USimpleControllerMappingCalibrateAxis:removeCalibrationFromMappedAxis(mappingProfile, ActionName) end
---@param AxisValue float
---@param Seconds int32
function USimpleControllerMappingCalibrateAxis:ControllerCalibrateEvent__DelegateSignature(AxisValue, Seconds) end
---@param mappingProfile FSimpleControllerMappingProfile
---@param ActionName FString
---@param timeInSecondsPerStep int32
---@return USimpleControllerMappingCalibrateAxis
function USimpleControllerMappingCalibrateAxis:calibrateMappedAxis(mappingProfile, ActionName, timeInSecondsPerStep) end


---@class USimpleControllerMappingLoad : UBlueprintAsyncActionBase
---@field successful FSimpleControllerMappingLoadSuccessful
---@field failed FSimpleControllerMappingLoadFailed
local USimpleControllerMappingLoad = {}

---@param WorldContextObject UObject
---@param ProfileName FString
---@param mappingProfile FSimpleControllerMappingProfile
---@param byDevice boolean
---@return USimpleControllerMappingLoad
function USimpleControllerMappingLoad:loadMappingFromFile(WorldContextObject, ProfileName, mappingProfile, byDevice) end
function USimpleControllerMappingLoad:ControllerMappingEvent__DelegateSignature() end


---@class USimpleControllerMappingSave : UBlueprintAsyncActionBase
---@field successful FSimpleControllerMappingSaveSuccessful
---@field failed FSimpleControllerMappingSaveFailed
local USimpleControllerMappingSave = {}

---@param ProfileName FString
---@param mappingProfile FSimpleControllerMappingProfile
---@return USimpleControllerMappingSave
function USimpleControllerMappingSave:saveMappingToFile(ProfileName, mappingProfile) end
function USimpleControllerMappingSave:ControllerMappingEvent__DelegateSignature() end


---@class USimpleControllerMobile : UObject
local USimpleControllerMobile = {}


---@class USimpleControllerPluginSettings : UDeveloperSettings
---@field SDL_EVENTS_THREAD boolean
---@field CREATE_PLAYER_CONTROLLER boolean
---@field WHEEL_FF_TEST boolean
---@field XINPUT_ENABLED boolean
---@field DIRECTINPUT_ENABLED boolean
---@field JOYSTICK_HIDAPI boolean
---@field JOYSTICK_RAWINPUT boolean
---@field JOYSTICK_WGI boolean
---@field JOYSTICK_HIDAPI_GAMECUBE boolean
---@field JOYSTICK_GAMECUBE_RUMBLE_BRAKE boolean
---@field JOYSTICK_HIDAPI_JOY_CONS boolean
---@field JOYSTICK_HIDAPI_COMBINE_JOY_CONS boolean
---@field JOYSTICK_HIDAPI_VERTICAL_JOY_CONS boolean
---@field JOYSTICK_HIDAPI_LUNA boolean
---@field JOYSTICK_HIDAPI_NINTENDO_CLASSIC boolean
---@field JOYSTICK_HIDAPI_SHIELD boolean
---@field JOYSTICK_HIDAPI_PS3 boolean
---@field JOYSTICK_HIDAPI_PS4 boolean
---@field JOYSTICK_HIDAPI_PS4_PS5_RUMBLE boolean
---@field JOYSTICK_HIDAPI_PS5 boolean
---@field JOYSTICK_HIDAPI_PS5_PLAYER_LED boolean
---@field JOYSTICK_HIDAPI_STADIA boolean
---@field JOYSTICK_HIDAPI_STEAM boolean
---@field JOYSTICK_HIDAPI_SWITCH boolean
---@field JOYSTICK_HIDAPI_SWITCH_HOME_LED boolean
---@field JOYSTICK_HIDAPI_JOYCON_HOME_LED boolean
---@field JOYSTICK_HIDAPI_SWITCH_PLAYER_LED boolean
---@field JOYSTICK_HIDAPI_WII boolean
---@field JOYSTICK_HIDAPI_WII_PLAYER_LED boolean
---@field JOYSTICK_HIDAPI_XBOX boolean
---@field JOYSTICK_HIDAPI_XBOX_360 boolean
---@field JOYSTICK_HIDAPI_XBOX_360_PLAYER_LED boolean
---@field JOYSTICK_HIDAPI_XBOX_360_WIRELESS boolean
---@field JOYSTICK_HIDAPI_XBOX_ONE boolean
---@field JOYSTICK_HIDAPI_XBOX_ONE_HOME_LED boolean
---@field JOYSTICK_RAWINPUT_CORRELATE_XINPUT boolean
---@field JOYSTICK_ROG_CHAKRAM boolean
---@field JOYSTICK_THREAD boolean
---@field LINUX_DIGITAL_HATS boolean
---@field LINUX_HAT_DEADZONES boolean
---@field LINUX_JOYSTICK_CLASSIC boolean
---@field LINUX_JOYSTICK_DEADZONES boolean
---@field JOYSTICK_ALLOW_BACKGROUND_EVENTS boolean
local USimpleControllerPluginSettings = {}



---@class USimpleControllerStatusAsyncEvent : UBlueprintAsyncActionBase
---@field attached FSimpleControllerStatusAsyncEventAttached
---@field detached FSimpleControllerStatusAsyncEventDetached
local USimpleControllerStatusAsyncEvent = {}

---@param device FSimpleControllerDevice
function USimpleControllerStatusAsyncEvent:ControllerStatusEvent__DelegateSignature(device) end
---@return USimpleControllerStatusAsyncEvent
function USimpleControllerStatusAsyncEvent:controllerStatusAsyncEvent() end


---@class USimpleControllerUIEnableSelection : UBlueprintAsyncActionBase
---@field onSelect FSimpleControllerUIEnableSelectionOnSelect
local USimpleControllerUIEnableSelection = {}

---@param DeviceID FString
---@param directionalPadValue int32
---@param directionalPadIndex int32
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerUIEnableSelection:uiDirectionalPadEvent(DeviceID, directionalPadValue, directionalPadIndex, deviceIndex, device, connectionIndex) end
---@param DeviceID FString
---@param axisID int32
---@param AxisValue float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerUIEnableSelection:uiAxisEvent(DeviceID, axisID, AxisValue, deviceIndex, device, connectionIndex) end
---@param Widget UWidget
---@param fakeConnectionIndex int32
function USimpleControllerUIEnableSelection:selectUIElement(Widget, fakeConnectionIndex) end
---@param Direction ESimpleControllerUIDirection
---@param fakeConnectionIndex int32
function USimpleControllerUIEnableSelection:selectNextUIElement(Direction, fakeConnectionIndex) end
---@param mainWidget UWidget
---@param selectedWidget UWidget
---@param connectionIndex int32
---@param hasNewSelection boolean
---@param lastDirection ESimpleControllerUIDirection
function USimpleControllerUIEnableSelection:selectedWidgetEventDelegate__DelegateSignature(mainWidget, selectedWidget, connectionIndex, hasNewSelection, lastDirection) end
function USimpleControllerUIEnableSelection:resumeSimpleControllerUISelection() end
function USimpleControllerUIEnableSelection:pauseSimpleControllerUISelection() end
---@param activeUIElement USimpleControllerUIEnableSelection
---@param mainWidget UWidget
---@param childWidgets TArray<UWidget>
---@param defaultWidgetToSelect UWidget
---@param connectionIndexes TArray<int32>
---@param useDpad boolean
---@param horizontalAxisID int32
---@param verticalAxisID int32
---@return USimpleControllerUIEnableSelection
function USimpleControllerUIEnableSelection:enableSimpleControllerUISelection(activeUIElement, mainWidget, childWidgets, defaultWidgetToSelect, connectionIndexes, useDpad, horizontalAxisID, verticalAxisID) end
function USimpleControllerUIEnableSelection:destroySimpleControllerUISelection() end


---@class USimpleControllerUnrealEvents : UObject
local USimpleControllerUnrealEvents = {}


---@class USimpleControllerUnrealMobileEvents : UObject
local USimpleControllerUnrealMobileEvents = {}


---@class USimpleControllerWheel : UObject
local USimpleControllerWheel = {}

---@param DeviceID FString
---@param axisID int32
---@param AxisValue float
---@param deviceIndex int32
---@param device FSimpleControllerDevice
---@param connectionIndex int32
function USimpleControllerWheel:wheelAxisEvent(DeviceID, axisID, AxisValue, deviceIndex, device, connectionIndex) end
---@param Force int32
function USimpleControllerWheel:updateConstantForceOnWheel(Force) end
---@param device FSimpleControllerDevice
---@param stopWhenCentered boolean
---@param defaultStrength float
---@param slowdownStrength float
---@param autocenterDesiredEndPosition float
function USimpleControllerWheel:updateAutocenterWheel(device, stopWhenCentered, defaultStrength, slowdownStrength, autocenterDesiredEndPosition) end
---@param device FSimpleControllerDevice
function USimpleControllerWheel:stopAutocenter(device) end
---@param device FSimpleControllerDevice
---@param hardStopStrength float
---@param moveWheelToHardStopLength float
function USimpleControllerWheel:moveWheelToHardStop(device, hardStopStrength, moveWheelToHardStopLength) end
---@param device FSimpleControllerDevice
---@param Position float
---@param Strength float
---@param hardStopStrength float
---@param stopLength float
---@param doHardStop boolean
function USimpleControllerWheel:moveWheelTo(device, Position, Strength, hardStopStrength, stopLength, doHardStop) end


---@class UStartControllerWebserverAsyncEvent : UBlueprintAsyncActionBase
---@field onSuccess FStartControllerWebserverAsyncEventOnSuccess
---@field onFail FStartControllerWebserverAsyncEventOnFail
local UStartControllerWebserverAsyncEvent = {}

function UStartControllerWebserverAsyncEvent:stopControllerWebserver() end
---@param webServer FControllerWebserver
function UStartControllerWebserverAsyncEvent:startControllerWebserverEvent__DelegateSignature(webServer) end
---@param QRLibPath FString
---@param controllerWebUIPath FString
---@return UStartControllerWebserverAsyncEvent
function UStartControllerWebserverAsyncEvent:startControllerWebserverAsync(QRLibPath, controllerWebUIPath) end
---@param webServer FControllerWebserver
---@return FString
function UStartControllerWebserverAsyncEvent:getServerUrl(webServer) end
---@param webServer FControllerWebserver
---@return FString
function UStartControllerWebserverAsyncEvent:getQCode(webServer) end


