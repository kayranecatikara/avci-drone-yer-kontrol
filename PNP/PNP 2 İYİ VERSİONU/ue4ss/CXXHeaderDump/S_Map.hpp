#ifndef UE4SS_SDK_S_Map_HPP
#define UE4SS_SDK_S_Map_HPP

struct FS_Map
{
    TEnumAsByte<E_Levels::Type> LevelName_3_072AB1BA4ADB5B50CAC38898B5B97D59;         // 0x0000 (size: 0x1)
    TEnumAsByte<E_MapMode::Type> Type_48_3DE8743A4A3178F07098118C53011C62;            // 0x0001 (size: 0x1)
    int32 EnemyCount_10_63896E174CE18EB3F8D784BD5003B669;                             // 0x0004 (size: 0x4)
    FName Level_42_34004C5D492BD89A2C998695B53DF146;                                  // 0x0008 (size: 0x8)
    class UTexture2D* CardTexture_47_CF5F936D41DBE1E36AD3979549EF826A;                // 0x0010 (size: 0x8)
    class UTexture2D* LoadingTexture_51_3E45D4384F6BF0226A3325AB448A9BFA;             // 0x0018 (size: 0x8)

}; // Size: 0x20

#endif
