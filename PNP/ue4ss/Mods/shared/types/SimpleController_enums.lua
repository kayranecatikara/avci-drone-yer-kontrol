---@enum ESimpleControllerAxisCorrection
local ESimpleControllerAxisCorrection = {
    Negative = 0,
    Positive = 1,
    ESimpleControllerAxisCorrection_MAX = 2,
}

---@enum ESimpleControllerButtonStatus
local ESimpleControllerButtonStatus = {
    Pressed = 0,
    Released = 1,
    ESimpleControllerButtonStatus_MAX = 2,
}

---@enum ESimpleControllerButtons
local ESimpleControllerButtons = {
    Button_0 = 0,
    Button_1 = 1,
    Button_2 = 2,
    Button_3 = 3,
    Button_4 = 4,
    Button_5 = 5,
    Button_6 = 6,
    Button_7 = 7,
    Button_8 = 8,
    Button_9 = 9,
    Button_10 = 10,
    Button_11 = 11,
    Button_12 = 12,
    Button_13 = 13,
    Button_14 = 14,
    Button_15 = 15,
    Button_16 = 16,
    Button_17 = 17,
    Button_18 = 18,
    Button_19 = 19,
    Button_20 = 20,
    Button_MAX = 21,
}

---@enum ESimpleControllerDirectionalPad
local ESimpleControllerDirectionalPad = {
    CENTERED = 0,
    UP = 1,
    RIGHT = 2,
    DOWN = 3,
    LEFT = 4,
    RIGHTUP = 5,
    RIGHTDOWN = 6,
    LEFTUP = 7,
    LEFTDOWN = 8,
    ESimpleControllerDirectionalPad_MAX = 9,
}

---@enum ESimpleControllerEventType
local ESimpleControllerEventType = {
    OnChange = 0,
    OnTick = 1,
    Persistent30 = 2,
    Persistent60 = 3,
    Persistent120 = 4,
    ESimpleControllerEventType_MAX = 5,
}

---@enum ESimpleControllerForceFeedbackDirectionType
local ESimpleControllerForceFeedbackDirectionType = {
    CARTESIAN = 0,
    POLAR = 1,
    SPHERICAL = 2,
    ESimpleControllerForceFeedbackDirectionType_MAX = 3,
}

---@enum ESimpleControllerForceFeedbackEffectConditionType
local ESimpleControllerForceFeedbackEffectConditionType = {
    SPRING = 0,
    DAMPER = 1,
    INERTIA = 2,
    FRICTION = 3,
    ESimpleControllerForceFeedbackEffectConditionType_MAX = 4,
}

---@enum ESimpleControllerForceFeedbackEffectPeriodicType
local ESimpleControllerForceFeedbackEffectPeriodicType = {
    SINE = 0,
    TRIANGLE = 1,
    SAWTOOTHUP = 2,
    SAWTOOTHDOWN = 3,
    ESimpleControllerForceFeedbackEffectPeriodicType_MAX = 4,
}

---@enum ESimpleControllerForceFeedbackEffectType
local ESimpleControllerForceFeedbackEffectType = {
    CONSTANT = 0,
    LEFTRIGHT = 1,
    ESimpleControllerForceFeedbackEffectType_MAX = 2,
}

---@enum ESimpleControllerKeyboardTriggerType
local ESimpleControllerKeyboardTriggerType = {
    Down = 0,
    Up = 1,
    ESimpleControllerKeyboardTriggerType_MAX = 2,
}

---@enum ESimpleControllerMapActionType
local ESimpleControllerMapActionType = {
    Button = 0,
    Axis = 1,
    ESimpleControllerMapActionType_MAX = 2,
}

---@enum ESimpleControllerMapButtonReactType
local ESimpleControllerMapButtonReactType = {
    Down = 0,
    Up = 1,
    ESimpleControllerMapButtonReactType_MAX = 2,
}

---@enum ESimpleControllerMapDoubleAction
local ESimpleControllerMapDoubleAction = {
    IgnoreInput = 0,
    DeleteOtherMapping = 1,
    ESimpleControllerMapDoubleAction_MAX = 2,
}

---@enum ESimpleControllerMouseTriggerButton
local ESimpleControllerMouseTriggerButton = {
    LeftMouseButton = 0,
    RightMouseButton = 1,
    MiddleMouseButton = 2,
    ThumbMouseButton = 3,
    ThumbMouseButton2 = 4,
    ESimpleControllerMouseTriggerButton_MAX = 5,
}

---@enum ESimpleControllerMouseTriggerType
local ESimpleControllerMouseTriggerType = {
    Down = 0,
    Up = 1,
    DoubleClick = 2,
    ESimpleControllerMouseTriggerType_MAX = 3,
}

---@enum ESimpleControllerPowerLevel
local ESimpleControllerPowerLevel = {
    UNKNOWN = 0,
    EMPTY = 1,
    LOW = 2,
    MEDIUM = 3,
    FULL = 4,
    WIRED = 5,
    MAX = 6,
}

---@enum ESimpleControllerSensorType
local ESimpleControllerSensorType = {
    ACCELATOR = 0,
    GYRO = 1,
    ESimpleControllerSensorType_MAX = 2,
}

---@enum ESimpleControllerSystemType
local ESimpleControllerSystemType = {
    Android = 0,
    IOS = 1,
    Windows = 2,
    Linux = 3,
    Mac = 4,
    ESimpleControllerSystemType_MAX = 5,
}

---@enum ESimpleControllerType
local ESimpleControllerType = {
    UNKNOWN = 0,
    GAMECONTROLLER = 1,
    WHEEL = 2,
    ARCADE_STICK = 3,
    FLIGHT_STICK = 4,
    DANCE_PAD = 5,
    GUITAR = 6,
    DRUM_KIT = 7,
    ARCADE_PAD = 8,
    THROTTLE = 9,
    KEYBOARD = 10,
    MOUSE = 11,
    MOBILECONTROLLER = 12,
    ESimpleControllerType_MAX = 13,
}

---@enum ESimpleControllerUIDirection
local ESimpleControllerUIDirection = {
    NONE = 0,
    RIGHT = 1,
    LEFT = 2,
    TOP = 3,
    BOTTOM = 4,
    ESimpleControllerUIDirection_MAX = 5,
}

---@enum ESimpleControllerWheelFFDirection
local ESimpleControllerWheelFFDirection = {
    Left = 0,
    Right = 1,
    ESimpleControllerWheelFFDirection_MAX = 2,
}

---@enum SCDualSenseTriggerEffectEndPosition
local SCDualSenseTriggerEffectEndPosition = {
    Value_3 = 0,
    Value_4 = 1,
    Value_5 = 2,
    Value_6 = 3,
    Value_7 = 4,
    Value_8 = 5,
    Value_MAX = 6,
}

---@enum SCDualSenseTriggerEffectStartPosition
local SCDualSenseTriggerEffectStartPosition = {
    Value_2 = 0,
    Value_3 = 1,
    Value_4 = 2,
    Value_5 = 3,
    Value_6 = 4,
    Value_7 = 5,
    Value_MAX = 6,
}

---@enum SCDualSenseTriggerEffectStartZone
local SCDualSenseTriggerEffectStartZone = {
    Value_0 = 0,
    Value_1 = 1,
    Value_2 = 2,
    Value_3 = 3,
    Value_4 = 4,
    Value_5 = 5,
    Value_6 = 6,
    Value_7 = 7,
    Value_8 = 8,
    Value_9 = 9,
    Value_MAX = 10,
}

---@enum SCDualSenseTriggerEffectStrength
local SCDualSenseTriggerEffectStrength = {
    Value_1 = 0,
    Value_2 = 1,
    Value_3 = 2,
    Value_4 = 3,
    Value_5 = 4,
    Value_6 = 5,
    Value_7 = 6,
    Value_8 = 7,
    Value_MAX = 8,
}

---@enum SCDualSenseTriggerEffectStrengthMulti
local SCDualSenseTriggerEffectStrengthMulti = {
    Value_0 = 0,
    Value_1 = 1,
    Value_2 = 2,
    Value_3 = 3,
    Value_4 = 4,
    Value_5 = 5,
    Value_6 = 6,
    Value_7 = 7,
    Value_8 = 8,
    Value_MAX = 9,
}

