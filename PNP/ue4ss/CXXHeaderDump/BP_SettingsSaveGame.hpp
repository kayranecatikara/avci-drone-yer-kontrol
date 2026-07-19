#ifndef UE4SS_SDK_BP_SettingsSaveGame_HPP
#define UE4SS_SDK_BP_SettingsSaveGame_HPP

class UBP_SettingsSaveGame_C : public USaveGame
{
    FString Graphic Settings;                                                         // 0x0028 (size: 0x10)
    bool FrameRate;                                                                   // 0x0038 (size: 0x1)
    double CameraSensitivity;                                                         // 0x0040 (size: 0x8)
    double MusicVolume;                                                               // 0x0048 (size: 0x8)
    double SFXVolume;                                                                 // 0x0050 (size: 0x8)
    double RC Expo Roll;                                                              // 0x0058 (size: 0x8)
    double Roll Axis Speed;                                                           // 0x0060 (size: 0x8)
    double Pitch Axis Speed;                                                          // 0x0068 (size: 0x8)
    double Yaw Axis Speed;                                                            // 0x0070 (size: 0x8)
    double RC Expo Pitch;                                                             // 0x0078 (size: 0x8)
    double RC Expo Yaw;                                                               // 0x0080 (size: 0x8)
    double Reverse Roll Axis;                                                         // 0x0088 (size: 0x8)
    double Reverse Throttle Axis;                                                     // 0x0090 (size: 0x8)
    double Reverse Pitch Axis;                                                        // 0x0098 (size: 0x8)
    double Reverse Yaw Axis;                                                          // 0x00A0 (size: 0x8)
    double Brightness;                                                                // 0x00A8 (size: 0x8)
    double FieldOfView;                                                               // 0x00B0 (size: 0x8)
    double DeadZone;                                                                  // 0x00B8 (size: 0x8)

}; // Size: 0xC0

#endif
