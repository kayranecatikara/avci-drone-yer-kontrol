#ifndef UE4SS_SDK_S_CreditsSectionDefinition_HPP
#define UE4SS_SDK_S_CreditsSectionDefinition_HPP

struct FS_CreditsSectionDefinition
{
    FText SectionTitle_3_A542BADA494DC9E1C329C8A17BC31200;                            // 0x0000 (size: 0x10)
    bool OverrideTitleStyle?_43_0315EE5142ACCCA1115A5B8DE411E052;                     // 0x0010 (size: 0x1)
    FS_CreditsTextStyling SectionTitleStyleOverride_46_DF71D8514E80E6388FFA8C87B9EAA58F; // 0x0018 (size: 0x38)
    TEnumAsByte<E_CreditsSectionType::Type> SectionType_7_18F2539A46D27A74B624A2962CE63D81; // 0x0050 (size: 0x1)
    FS_CreditsSectionParameters SectionGlobalParameters_41_352512794A444E5E6E280880607972D5; // 0x0058 (size: 0x20)
    TEnumAsByte<E_CreditsSectionContentType::Type> SectionContentOrder_25_1AE362574DC106CBA207B9AE3CD2E5D6; // 0x0078 (size: 0x1)
    TArray<FS_CreditsTextSectionDefinition> SectionTextContent_18_9C77E793467E4B332F3617B8350775E4; // 0x0080 (size: 0x10)
    FS_CreditsImageSectionDefinition SectionImageContent_27_E6FB86F5458C242480A2A493A2A6BF4B; // 0x0090 (size: 0xC0)

}; // Size: 0x150

#endif
