#ifndef UE4SS_SDK_BPI_EGUI_WidgetsCommunicationInterface_HPP
#define UE4SS_SDK_BPI_EGUI_WidgetsCommunicationInterface_HPP

class IBPI_EGUI_WidgetsCommunicationInterface_C : public IInterface
{

    void OptionsMenuClosedEvent(int32 LastActiveTab);
    void SelectInitialOptionsMenuTab(int32 TabIndex);
}; // Size: 0x28

#endif
