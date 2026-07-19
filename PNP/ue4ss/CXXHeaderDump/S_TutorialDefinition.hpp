#ifndef UE4SS_SDK_S_TutorialDefinition_HPP
#define UE4SS_SDK_S_TutorialDefinition_HPP

struct FS_TutorialDefinition
{
    bool PauseGameDuringTutorial?_3_83811CCE4485D54CB50282A30906C301;                 // 0x0000 (size: 0x1)
    bool BlockPlayerInputsDuringTutorial?_4_E6CB72E445FD41BB489E81AE0015D6EC;         // 0x0001 (size: 0x1)
    bool RequireManualInputToDismiss?_21_6BC4D68649A5D0760E50D2B4495911AD;            // 0x0002 (size: 0x1)
    bool RemoveModuleOnAllTutorialsCompleted?_22_7299122346462BADF259368CC738F028;    // 0x0003 (size: 0x1)
    double TutorialDuration_23_6FED41094220EE7C2D7771ABA30328AE;                      // 0x0008 (size: 0x8)
    FText TutorialTitle_24_AF09D7C84B2A2F35E2A72783206C512E;                          // 0x0010 (size: 0x10)
    FS_CommonTextInfo TutorialTitleTextStyling_57_27EF6E6A462BADE293DB53A9B9A3AE75;   // 0x0020 (size: 0x18)
    FSlateBrush TutorialIllustrationImage_26_4513153C4652B83DA2DD0B9951358978;        // 0x0040 (size: 0xB0)
    FText TutorialRichText_29_38037F3C4609F461D8A6BEAD117FCA5E;                       // 0x00F0 (size: 0x10)
    FS_CommonTextInfo TutorialContentTextStyling_56_7927B1804766327B43F25C93F96C1451; // 0x0100 (size: 0x18)
    bool UseTextSizeForInputs?_63_3A1581704613152E2E0FDAA650F33903;                   // 0x0118 (size: 0x1)
    int32 ManualInputsSize_65_4A15C5B74A66F8FA9F7D689527777C0B;                       // 0x011C (size: 0x4)
    bool RichTextUseInputAction?_30_ED5A18664087E1B1631F43ADD6A4E11E;                 // 0x0120 (size: 0x1)
    TArray<FS_InputActionDef> InputActionInfos_34_5DC2DE814CF43BF3B388BEB7EDD7DF2B;   // 0x0128 (size: 0x10)
    TArray<FKey> MouseKeyboardKeys_46_21F5B43F4C7106AB8714D8BE633AA030;               // 0x0138 (size: 0x10)
    TArray<FKey> GamepadKeys_45_F3C1D58F4E72B8E22CF89FB47B700FDC;                     // 0x0148 (size: 0x10)
    TEnumAsByte<E_InputPromptDisplayConditions::Type> DisplayConditions_47_B31DA82E4ECAAB116D719FBD986507DC; // 0x0158 (size: 0x1)

}; // Size: 0x159

#endif
