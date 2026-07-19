#ifndef UE4SS_SDK_InvertXAxis_HPP
#define UE4SS_SDK_InvertXAxis_HPP

class UInvertXAxis_C : public UInputModifier
{

    FInputActionValue ModifyRaw(const class UEnhancedPlayerInput* PlayerInput, FInputActionValue CurrentValue, float DeltaTime);
}; // Size: 0x28

#endif
