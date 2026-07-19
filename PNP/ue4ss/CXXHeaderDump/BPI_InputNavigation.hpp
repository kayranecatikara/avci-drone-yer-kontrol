#ifndef UE4SS_SDK_BPI_InputNavigation_HPP
#define UE4SS_SDK_BPI_InputNavigation_HPP

class IBPI_InputNavigation_C : public IInterface
{

    void AnyKeyPressed(FKey Key);
    void NewInputActionTriggered(TEnumAsByte<E_UI_NavInputList::Type> InputType, FString ActionValue);
}; // Size: 0x28

#endif
