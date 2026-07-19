#ifndef UE4SS_SDK_GamepadSensitivity_HPP
#define UE4SS_SDK_GamepadSensitivity_HPP

class UGamepadSensitivity_C : public UInputModifier
{
    double Sensitivity;                                                               // 0x0028 (size: 0x8)

    FInputActionValue ModifyRaw(const class UEnhancedPlayerInput* PlayerInput, FInputActionValue CurrentValue, float DeltaTime);
}; // Size: 0x30

#endif
