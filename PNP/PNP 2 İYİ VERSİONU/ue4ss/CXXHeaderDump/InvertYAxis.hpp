#ifndef UE4SS_SDK_InvertYAxis_HPP
#define UE4SS_SDK_InvertYAxis_HPP

class UInvertYAxis_C : public UInputModifier
{

    FInputActionValue ModifyRaw(const class UEnhancedPlayerInput* PlayerInput, FInputActionValue CurrentValue, float DeltaTime);
}; // Size: 0x28

#endif
