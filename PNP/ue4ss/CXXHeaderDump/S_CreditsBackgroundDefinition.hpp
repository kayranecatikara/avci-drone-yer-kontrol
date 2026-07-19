#ifndef UE4SS_SDK_S_CreditsBackgroundDefinition_HPP
#define UE4SS_SDK_S_CreditsBackgroundDefinition_HPP

struct FS_CreditsBackgroundDefinition
{
    TEnumAsByte<E_CreditsBackgroundType::Type> BackgroundType_2_4C4791404D1CB38D00A99EBF6FCEA21D; // 0x0000 (size: 0x1)
    FLinearColor SolidColor_5_43B620254191FC306F3141AF02C006AD;                       // 0x0004 (size: 0x10)
    TArray<TSoftObjectPtr<UTexture2D>> Images_15_B168228A4D66C8B42025BEB07C0BBE78;    // 0x0018 (size: 0x10)
    double FadingImagesDuration_13_F114F2E44C9206D38A09DF94CEFD49FE;                  // 0x0028 (size: 0x8)
    double BackgroundCrossFadeDuration_20_02EBA4BF4F839AC5C0FAB4B81357447F;           // 0x0030 (size: 0x8)

}; // Size: 0x38

#endif
